from pathlib import Path

import pandas as pd
import yaml

from core.data.validate_public_dataset_modality_schemas import (
    build_arg_parser,
    validate_public_dataset_modality_schemas,
)


def write_request(path, inventory, summary, output_dir):
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump({
            "request_id": "test_schema",
            "atlas_name": "test_public",
            "inputs": {"real_file_intake_inventory": str(inventory), "real_file_intake_summary": str(summary)},
            "expected_outputs": {"modality_schema_validation_dir": str(output_dir)},
            "schema_policy": {"minimum_rows": 1, "minimum_columns": 2, "numeric_fraction_threshold": 0.5, "allowed_extensions": [".tsv", ".csv", ".txt"], "modality_id_hints": {"transcriptomics": ["sample", "gene", "id"]}},
        }, handle, sort_keys=False)


def test_validate_public_dataset_modality_schemas_awaiting_file(tmp_path: Path):
    inventory = tmp_path / "inventory.tsv"
    summary = tmp_path / "summary.yaml"
    request = tmp_path / "request.yaml"
    output_dir = tmp_path / "schema"
    pd.DataFrame([{
        "dataset_id": "dataset_a", "source_id": "gdc_tcga", "accession_or_project_id": "TCGA-TEST", "atlas_hint": "brca", "modality": "transcriptomics", "expected_file_type": "matrix", "target_local_path": str(tmp_path / "missing.tsv"), "intake_status": "awaiting_file", "candidate_file_count": 0, "candidate_files": "",
    }]).to_csv(inventory, sep="\t", index=False)
    with summary.open("w", encoding="utf-8") as handle:
        yaml.safe_dump({"request_id": "upstream_intake", "output_dir": str(tmp_path)}, handle, sort_keys=False)
    write_request(request, inventory, summary, output_dir)
    out_summary, validation_df, modality_df, source_df, paths = validate_public_dataset_modality_schemas(request_path=request)
    assert paths["schema_validation_table"].exists()
    assert paths["modality_summary"].exists()
    assert paths["schema_validation_summary"].exists()
    assert out_summary["dataset_count"] == 1
    assert out_summary["awaiting_file_count"] == 1
    assert validation_df.loc[0, "schema_validation_status"] == "skipped_awaiting_file"
    assert not modality_df.empty


def test_validate_public_dataset_modality_schemas_valid_file(tmp_path: Path):
    real_file = tmp_path / "real.tsv"
    real_file.write_text("sample_id\tGENE1\nS1\t10\n", encoding="utf-8")
    inventory = tmp_path / "inventory.tsv"
    summary = tmp_path / "summary.yaml"
    request = tmp_path / "request.yaml"
    output_dir = tmp_path / "schema"
    pd.DataFrame([{
        "dataset_id": "dataset_a", "source_id": "gdc_tcga", "accession_or_project_id": "TCGA-TEST", "atlas_hint": "brca", "modality": "transcriptomics", "expected_file_type": "matrix", "target_local_path": str(real_file), "intake_status": "target_file_present", "candidate_file_count": 0, "candidate_files": "",
    }]).to_csv(inventory, sep="\t", index=False)
    with summary.open("w", encoding="utf-8") as handle:
        yaml.safe_dump({"request_id": "upstream_intake", "output_dir": str(tmp_path)}, handle, sort_keys=False)
    write_request(request, inventory, summary, output_dir)
    out_summary, validation_df, modality_df, source_df, paths = validate_public_dataset_modality_schemas(request_path=request)
    assert out_summary["validated_schema_count"] == 1
    assert validation_df.loc[0, "schema_validation_status"] == "validated_modality_schema"


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--request", "request.yaml", "--output-dir", "out"])
    assert str(args.request).endswith("request.yaml")
    assert str(args.output_dir).endswith("out")

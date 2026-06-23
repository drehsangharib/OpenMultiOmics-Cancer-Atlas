from pathlib import Path

import pandas as pd
import yaml

from core.data.validate_public_dataset_replacement_readiness import (
    build_arg_parser,
    validate_public_dataset_replacement_readiness,
)


def write_request(path, replacement_plan, replacement_manifest_inventory, replacement_summary, output_dir):
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "request_id": "test_readiness",
                "atlas_name": "test_public",
                "inputs": {
                    "replacement_plan": str(replacement_plan),
                    "replacement_manifest_inventory": str(replacement_manifest_inventory),
                    "replacement_summary": str(replacement_summary),
                },
                "expected_outputs": {"readiness_dir": str(output_dir)},
            },
            handle,
            sort_keys=False,
        )


def write_summary(path, tmp_path):
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump({"request_id": "upstream_replacement", "atlas_name": "test_public", "output_dir": str(tmp_path / "replacement_workflow")}, handle, sort_keys=False)


def test_validate_public_dataset_replacement_readiness_missing_real_file(tmp_path: Path):
    replacement_plan = tmp_path / "replacement_plan.tsv"
    replacement_manifest_inventory = tmp_path / "replacement_manifest_inventory.tsv"
    replacement_summary = tmp_path / "replacement_summary.yaml"
    request_path = tmp_path / "readiness_request.yaml"
    output_dir = tmp_path / "readiness"
    replacement_manifest_stub = tmp_path / "brca_transcriptomics_real_public_data_manifest.yaml"
    replacement_manifest_stub.write_text("manifest_id: brca_transcriptomics_real_public_data_manifest\n", encoding="utf-8")
    pd.DataFrame([{
        "dataset_id": "dataset_a", "display_name": "Dataset A", "source_id": "source_a", "accession_or_project_id": "ACC-A",
        "atlas_hint": "brca", "modality": "transcriptomics", "expected_file_type": "matrix", "replacement_priority": 1,
        "local_file_path": str(tmp_path / "placeholder.tsv"), "placeholder_exists": 1,
        "local_replacement_path": str(tmp_path / "missing_real.tsv"), "replacement_file_exists": 0,
        "materialized_manifest_stub": str(tmp_path / "source_manifest.yaml"), "replacement_status": "awaiting_real_public_file",
        "recommended_action": "download real file", "notes": "test",
    }]).to_csv(replacement_plan, sep="\t", index=False)
    pd.DataFrame([{
        "dataset_id": "dataset_a", "atlas_hint": "brca", "modality": "transcriptomics",
        "source_manifest": str(tmp_path / "source_manifest.yaml"), "replacement_manifest_stub": str(replacement_manifest_stub),
        "source_manifest_exists": 1, "replacement_manifest_stub_exists": 1,
    }]).to_csv(replacement_manifest_inventory, sep="\t", index=False)
    write_summary(replacement_summary, tmp_path)
    write_request(request_path, replacement_plan, replacement_manifest_inventory, replacement_summary, output_dir)
    summary, readiness_df, source_df, paths = validate_public_dataset_replacement_readiness(request_path=request_path)
    assert paths["readiness_table"].exists()
    assert paths["source_artifact_index"].exists()
    assert paths["readiness_summary"].exists()
    assert paths["readiness_report"].exists()
    assert summary["replacement_candidate_count"] == 1
    assert summary["ready_for_replacement_validation_count"] == 0
    assert summary["not_ready_missing_real_file_count"] == 1
    assert readiness_df.loc[0, "readiness_status"] == "not_ready_missing_real_file"
    assert not source_df.empty


def test_validate_public_dataset_replacement_readiness_ready_file(tmp_path: Path):
    replacement_plan = tmp_path / "replacement_plan.tsv"
    replacement_manifest_inventory = tmp_path / "replacement_manifest_inventory.tsv"
    replacement_summary = tmp_path / "replacement_summary.yaml"
    request_path = tmp_path / "readiness_request.yaml"
    output_dir = tmp_path / "readiness"
    replacement_manifest_stub = tmp_path / "gbm_epigenome_real_public_data_manifest.yaml"
    real_file = tmp_path / "real.tsv"
    replacement_manifest_stub.write_text("manifest_id: gbm_epigenome_real_public_data_manifest\n", encoding="utf-8")
    real_file.write_text("sample_id\tFEATURE1\nS1\t1\n", encoding="utf-8")
    pd.DataFrame([{
        "dataset_id": "dataset_b", "display_name": "Dataset B", "source_id": "source_b", "accession_or_project_id": "ACC-B",
        "atlas_hint": "gbm", "modality": "epigenome", "expected_file_type": "matrix", "replacement_priority": 1,
        "local_file_path": str(tmp_path / "placeholder.tsv"), "placeholder_exists": 1,
        "local_replacement_path": str(real_file), "replacement_file_exists": 1,
        "materialized_manifest_stub": str(tmp_path / "source_manifest.yaml"), "replacement_status": "ready_with_real_file",
        "recommended_action": "validate real file", "notes": "test",
    }]).to_csv(replacement_plan, sep="\t", index=False)
    pd.DataFrame([{
        "dataset_id": "dataset_b", "atlas_hint": "gbm", "modality": "epigenome",
        "source_manifest": str(tmp_path / "source_manifest.yaml"), "replacement_manifest_stub": str(replacement_manifest_stub),
        "source_manifest_exists": 1, "replacement_manifest_stub_exists": 1,
    }]).to_csv(replacement_manifest_inventory, sep="\t", index=False)
    write_summary(replacement_summary, tmp_path)
    write_request(request_path, replacement_plan, replacement_manifest_inventory, replacement_summary, output_dir)
    summary, readiness_df, source_df, paths = validate_public_dataset_replacement_readiness(request_path=request_path)
    assert summary["replacement_candidate_count"] == 1
    assert summary["ready_for_replacement_validation_count"] == 1
    assert summary["not_ready_missing_real_file_count"] == 0
    assert readiness_df.loc[0, "readiness_status"] == "ready_for_replacement_validation"


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--request", "request.yaml", "--output-dir", "out"])
    assert str(args.request).endswith("request.yaml")
    assert str(args.output_dir).endswith("out")

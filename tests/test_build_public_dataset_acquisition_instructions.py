from pathlib import Path

import pandas as pd
import yaml

from core.data.build_public_dataset_acquisition_instructions import (
    build_arg_parser,
    build_public_dataset_acquisition_instructions,
)


def test_build_public_dataset_acquisition_instructions(tmp_path: Path):
    registry_path = tmp_path / "registry.yaml"
    replacement_plan = tmp_path / "replacement_plan.tsv"
    readiness_table = tmp_path / "readiness.tsv"
    execution_jobs = tmp_path / "execution.tsv"
    file_validation_table = tmp_path / "file_validation.tsv"
    request_path = tmp_path / "request.yaml"
    output_dir = tmp_path / "instructions"

    with registry_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "datasets": {
                    "dataset_a": {
                        "display_name": "Dataset A",
                        "source_id": "gdc_tcga",
                        "accession_or_project_id": "TCGA-TEST",
                        "atlas_hint": "brca",
                        "modality": "transcriptomics",
                        "expected_file_type": "matrix",
                        "replacement_priority": 1,
                        "local_replacement_path": str(tmp_path / "real.tsv"),
                        "notes": "test",
                    }
                }
            },
            handle,
            sort_keys=False,
        )

    pd.DataFrame(
        [
            {
                "dataset_id": "dataset_a",
                "display_name": "Dataset A",
                "source_id": "gdc_tcga",
                "accession_or_project_id": "TCGA-TEST",
                "atlas_hint": "brca",
                "modality": "transcriptomics",
                "expected_file_type": "matrix",
                "replacement_priority": 1,
                "local_replacement_path": str(tmp_path / "real.tsv"),
                "replacement_file_exists": 0,
                "replacement_status": "awaiting_real_public_file",
                "recommended_action": "download/export",
                "notes": "test",
            }
        ]
    ).to_csv(replacement_plan, sep="\t", index=False)

    pd.DataFrame([{"dataset_id": "dataset_a", "readiness_status": "not_ready_missing_real_file", "readiness_message": "missing"}]).to_csv(readiness_table, sep="\t", index=False)
    pd.DataFrame([{"dataset_id": "dataset_a", "execution_status": "skipped_not_ready", "skip_reason": "missing"}]).to_csv(execution_jobs, sep="\t", index=False)
    pd.DataFrame([{"dataset_id": "dataset_a", "file_validation_status": "skipped_not_ready", "file_validation_message": "missing"}]).to_csv(file_validation_table, sep="\t", index=False)

    with request_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "request_id": "test_acquisition_instructions",
                "atlas_name": "test_public",
                "inputs": {
                    "dataset_accession_registry": str(registry_path),
                    "replacement_plan": str(replacement_plan),
                    "readiness_table": str(readiness_table),
                    "execution_jobs": str(execution_jobs),
                    "file_validation_table": str(file_validation_table),
                },
                "expected_outputs": {"acquisition_instructions_dir": str(output_dir)},
                "instruction_policy": {
                    "include_only_not_ready_or_unvalidated": False,
                    "include_validation_commands": True,
                    "include_replacement_paths": True,
                    "include_source_specific_guidance": True,
                },
            },
            handle,
            sort_keys=False,
        )

    summary, instructions_df, source_df, paths = build_public_dataset_acquisition_instructions(request_path=request_path)

    assert paths["acquisition_instructions"].exists()
    assert paths["source_artifact_index"].exists()
    assert paths["acquisition_summary"].exists()
    assert paths["acquisition_report"].exists()
    assert summary["instruction_count"] == 1
    assert summary["acquisition_needed_count"] == 1
    assert not instructions_df.empty
    assert instructions_df.loc[0, "dataset_id"] == "dataset_a"
    assert instructions_df.loc[0, "acquisition_needed"] == 1
    assert "GDC" in instructions_df.loc[0, "acquisition_instruction"]
    assert not source_df.empty


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--request", "request.yaml", "--output-dir", "out"])
    assert str(args.request).endswith("request.yaml")
    assert str(args.output_dir).endswith("out")

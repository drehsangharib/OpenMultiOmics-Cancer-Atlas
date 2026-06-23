from pathlib import Path

import pandas as pd
import yaml

from core.data.validate_public_dataset_replacement_files import (
    build_arg_parser,
    validate_public_dataset_replacement_files,
)


def write_request(path, execution_jobs, execution_summary, output_dir):
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "request_id": "test_file_validation",
                "atlas_name": "test_public",
                "inputs": {
                    "execution_jobs": str(execution_jobs),
                    "execution_summary": str(execution_summary),
                    "execution_source_artifact_index": str(path.parent / "execution_source.tsv"),
                },
                "expected_outputs": {"file_validation_dir": str(output_dir)},
                "validation_policy": {
                    "require_ready_execution_job": True,
                    "require_real_replacement_file": True,
                    "require_readable_table": True,
                    "minimum_rows": 1,
                    "minimum_columns": 2,
                    "allowed_extensions": [".tsv", ".csv", ".txt"],
                },
            },
            handle,
            sort_keys=False,
        )


def write_execution_summary(path, tmp_path):
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "request_id": "upstream_execution",
                "atlas_name": "test_public",
                "output_dir": str(tmp_path / "execution"),
            },
            handle,
            sort_keys=False,
        )


def base_job(tmp_path, execution_status="skipped_not_ready", local_replacement_path=None):
    if local_replacement_path is None:
        local_replacement_path = tmp_path / "missing.tsv"
    return {
        "execution_job_id": "execute_dataset_a_brca_transcriptomics",
        "dataset_id": "dataset_a",
        "display_name": "Dataset A",
        "source_id": "source_a",
        "accession_or_project_id": "ACC-A",
        "atlas_hint": "brca",
        "modality": "transcriptomics",
        "expected_file_type": "matrix",
        "replacement_priority": 1,
        "readiness_status": "not_ready_missing_real_file",
        "execution_status": execution_status,
        "skip_reason": "not ready",
        "local_replacement_path": str(local_replacement_path),
        "replacement_manifest_stub": str(tmp_path / "manifest.yaml"),
        "materialized_manifest_stub": str(tmp_path / "source_manifest.yaml"),
        "recommended_action": "download real file",
        "notes": "test",
    }


def test_validate_public_dataset_replacement_files_skipped_not_ready(tmp_path: Path):
    execution_jobs = tmp_path / "execution_jobs.tsv"
    execution_summary = tmp_path / "execution_summary.yaml"
    request_path = tmp_path / "file_validation_request.yaml"
    output_dir = tmp_path / "file_validation"

    pd.DataFrame([base_job(tmp_path)]).to_csv(execution_jobs, sep="\t", index=False)
    write_execution_summary(execution_summary, tmp_path)
    write_request(request_path, execution_jobs, execution_summary, output_dir)

    summary, validation_df, source_df, paths = validate_public_dataset_replacement_files(request_path=request_path)

    assert paths["file_validation_table"].exists()
    assert paths["source_artifact_index"].exists()
    assert paths["file_validation_summary"].exists()
    assert paths["file_validation_report"].exists()
    assert summary["replacement_candidate_count"] == 1
    assert summary["ready_execution_job_count"] == 0
    assert summary["validated_real_file_count"] == 0
    assert summary["skipped_not_ready_count"] == 1
    assert validation_df.loc[0, "file_validation_status"] == "skipped_not_ready"
    assert not source_df.empty


def test_validate_public_dataset_replacement_files_valid_ready_file(tmp_path: Path):
    execution_jobs = tmp_path / "execution_jobs.tsv"
    execution_summary = tmp_path / "execution_summary.yaml"
    request_path = tmp_path / "file_validation_request.yaml"
    output_dir = tmp_path / "file_validation"
    real_file = tmp_path / "real.tsv"
    real_file.write_text("sample_id\tGENE1\nS1\t1\n", encoding="utf-8")

    job = base_job(tmp_path, execution_status="ready_execution_job", local_replacement_path=real_file)
    job["skip_reason"] = ""
    job["readiness_status"] = "ready_for_replacement_validation"
    pd.DataFrame([job]).to_csv(execution_jobs, sep="\t", index=False)
    write_execution_summary(execution_summary, tmp_path)
    write_request(request_path, execution_jobs, execution_summary, output_dir)

    summary, validation_df, source_df, paths = validate_public_dataset_replacement_files(request_path=request_path)

    assert summary["replacement_candidate_count"] == 1
    assert summary["ready_execution_job_count"] == 1
    assert summary["validated_real_file_count"] == 1
    assert summary["skipped_not_ready_count"] == 0
    assert validation_df.loc[0, "file_validation_status"] == "validated_real_file"
    assert validation_df.loc[0, "real_file_row_count"] == 1
    assert validation_df.loc[0, "real_file_column_count"] == 2


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--request", "request.yaml", "--output-dir", "out"])
    assert str(args.request).endswith("request.yaml")
    assert str(args.output_dir).endswith("out")

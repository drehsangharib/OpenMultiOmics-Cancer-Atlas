from pathlib import Path

import pandas as pd
import yaml

from core.data.build_public_dataset_replacement_execution_scaffold import (
    build_arg_parser,
    build_public_dataset_replacement_execution_scaffold,
)


def write_request(path, readiness_table, readiness_summary, output_dir):
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "request_id": "test_execution_scaffold",
                "atlas_name": "test_public",
                "inputs": {
                    "readiness_table": str(readiness_table),
                    "readiness_summary": str(readiness_summary),
                    "readiness_source_artifact_index": str(path.parent / "source_artifact_index.tsv"),
                },
                "expected_outputs": {"execution_scaffold_dir": str(output_dir)},
            },
            handle,
            sort_keys=False,
        )


def write_readiness_summary(path, tmp_path):
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "request_id": "upstream_readiness",
                "atlas_name": "test_public",
                "output_dir": str(tmp_path / "readiness"),
            },
            handle,
            sort_keys=False,
        )


def base_row(tmp_path, dataset_id="dataset_a", atlas_hint="brca", modality="transcriptomics"):
    return {
        "dataset_id": dataset_id,
        "display_name": "Dataset A",
        "source_id": "source_a",
        "accession_or_project_id": "ACC-A",
        "atlas_hint": atlas_hint,
        "modality": modality,
        "expected_file_type": "matrix",
        "replacement_priority": 1,
        "local_file_path": str(tmp_path / "placeholder.tsv"),
        "placeholder_exists": 1,
        "placeholder_exists_current": 1,
        "local_replacement_path": str(tmp_path / "real.tsv"),
        "replacement_file_exists": 0,
        "replacement_file_exists_current": 0,
        "materialized_manifest_stub": str(tmp_path / "source_manifest.yaml"),
        "replacement_manifest_stub": str(tmp_path / "replacement_manifest.yaml"),
        "replacement_manifest_stub_exists": 1,
        "replacement_manifest_stub_exists_current": 1,
        "replacement_status": "awaiting_real_public_file",
        "readiness_status": "not_ready_missing_real_file",
        "readiness_message": "Real replacement file is missing.",
        "recommended_action": "download real file",
        "notes": "test",
    }


def test_build_public_dataset_replacement_execution_scaffold_skipped_candidate(tmp_path: Path):
    readiness_table = tmp_path / "readiness_table.tsv"
    readiness_summary = tmp_path / "readiness_summary.yaml"
    request_path = tmp_path / "execution_request.yaml"
    output_dir = tmp_path / "execution_scaffold"

    pd.DataFrame([base_row(tmp_path)]).to_csv(readiness_table, sep="\t", index=False)
    write_readiness_summary(readiness_summary, tmp_path)
    write_request(request_path, readiness_table, readiness_summary, output_dir)

    summary, jobs_df, manifest_df, source_df, paths = build_public_dataset_replacement_execution_scaffold(request_path=request_path)

    assert paths["execution_jobs"].exists()
    assert paths["execution_manifest_inventory"].exists()
    assert paths["source_artifact_index"].exists()
    assert paths["execution_summary"].exists()
    assert paths["execution_report"].exists()
    assert summary["replacement_candidate_count"] == 1
    assert summary["ready_execution_job_count"] == 0
    assert summary["skipped_not_ready_count"] == 1
    assert summary["execution_job_manifest_count"] == 0
    assert jobs_df.loc[0, "execution_status"] == "skipped_not_ready"
    assert manifest_df.empty
    assert not source_df.empty


def test_build_public_dataset_replacement_execution_scaffold_ready_candidate(tmp_path: Path):
    readiness_table = tmp_path / "readiness_table.tsv"
    readiness_summary = tmp_path / "readiness_summary.yaml"
    request_path = tmp_path / "execution_request.yaml"
    output_dir = tmp_path / "execution_scaffold"
    real_file = tmp_path / "real.tsv"
    manifest_stub = tmp_path / "replacement_manifest.yaml"
    real_file.write_text("sample_id\tFEATURE1\nS1\t1\n", encoding="utf-8")
    manifest_stub.write_text("manifest_id: replacement_manifest\n", encoding="utf-8")

    row = base_row(tmp_path, dataset_id="dataset_b", atlas_hint="gbm", modality="epigenome")
    row["local_replacement_path"] = str(real_file)
    row["replacement_file_exists"] = 1
    row["replacement_file_exists_current"] = 1
    row["replacement_manifest_stub"] = str(manifest_stub)
    row["readiness_status"] = "ready_for_replacement_validation"
    row["readiness_message"] = "ready"
    row["replacement_status"] = "ready_with_real_file"

    pd.DataFrame([row]).to_csv(readiness_table, sep="\t", index=False)
    write_readiness_summary(readiness_summary, tmp_path)
    write_request(request_path, readiness_table, readiness_summary, output_dir)

    summary, jobs_df, manifest_df, source_df, paths = build_public_dataset_replacement_execution_scaffold(request_path=request_path)

    assert summary["replacement_candidate_count"] == 1
    assert summary["ready_execution_job_count"] == 1
    assert summary["skipped_not_ready_count"] == 0
    assert summary["execution_job_manifest_count"] == 1
    assert jobs_df.loc[0, "execution_status"] == "ready_execution_job"
    assert not manifest_df.empty
    assert Path(manifest_df.loc[0, "execution_job_manifest"]).exists()


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--request", "request.yaml", "--output-dir", "out"])
    assert str(args.request).endswith("request.yaml")
    assert str(args.output_dir).endswith("out")

from pathlib import Path

import pandas as pd
import yaml

from core.data.run_public_data_execution_smoke import (
    build_arg_parser,
    inspect_feature_store,
    run_public_data_execution_smoke,
)


def test_inspect_feature_store(tmp_path: Path):
    for name in ["normalized_matrix.tsv", "sample_metadata.tsv", "feature_metadata.tsv", "qc_summary.tsv", "feature_store_manifest.yaml"]:
        (tmp_path / name).write_text("x", encoding="utf-8")
    count, expected = inspect_feature_store(tmp_path)
    assert count == 5
    assert "normalized_matrix" in expected


def test_run_public_data_execution_smoke_with_mocked_processor(tmp_path: Path, monkeypatch):
    materialization_dir = tmp_path / "materialization"
    materialization_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir = materialization_dir / "materialized_manifest_stubs"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    feature_store_dir = tmp_path / "feature_store"
    feature_store_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = manifest_dir / "brca_transcriptomics_materialized_public_data_manifest.yaml"
    with manifest_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "manifest_id": "test_manifest",
                "atlas_name": "brca",
                "modality": "transcriptomics",
                "expected_outputs": {"feature_store_dir": str(feature_store_dir)},
                "input_files": [{"path": "matrix.tsv"}],
            },
            handle,
            sort_keys=False,
        )

    for name in ["normalized_matrix.tsv", "sample_metadata.tsv", "feature_metadata.tsv", "qc_summary.tsv", "feature_store_manifest.yaml"]:
        (feature_store_dir / name).write_text("x", encoding="utf-8")

    inventory_path = materialization_dir / "materialized_manifest_inventory.tsv"
    pd.DataFrame(
        [
            {
                "atlas_hint": "brca",
                "modality": "transcriptomics",
                "materialized_manifest_stub": str(manifest_path),
                "local_file_path": "matrix.tsv",
            }
        ]
    ).to_csv(inventory_path, sep="\t", index=False)

    summary_path = materialization_dir / "local_file_materialization_summary.yaml"
    with summary_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump({"materialized_manifest_stub_count": 1}, handle, sort_keys=False)

    request_path = tmp_path / "smoke_request.yaml"
    output_dir = tmp_path / "smoke"
    with request_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "request_id": "test_smoke",
                "atlas_name": "test_public",
                "materialization_summary": str(summary_path),
                "materialized_manifest_inventory": str(inventory_path),
                "expected_outputs": {"smoke_run_dir": str(output_dir)},
            },
            handle,
            sort_keys=False,
        )

    def fake_run_processor(manifest_path, python_executable=None):
        return {
            "returncode": 0,
            "stdout": "ok",
            "stderr": "",
            "processor_module": "fake.module",
            "feature_store_dir": str(feature_store_dir),
        }

    monkeypatch.setattr("core.data.run_public_data_execution_smoke.run_processor_for_manifest", fake_run_processor)
    summary, smoke_df, paths = run_public_data_execution_smoke(request_path=request_path)

    assert paths["execution_smoke_results"].exists()
    assert paths["execution_smoke_summary"].exists()
    assert paths["execution_smoke_report"].exists()
    assert summary["smoke_run_count"] == 1
    assert summary["smoke_pass_count"] == 1
    assert int(smoke_df.loc[0, "passed"]) == 1


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--request", "request.yaml"])
    assert str(args.request).endswith("request.yaml")

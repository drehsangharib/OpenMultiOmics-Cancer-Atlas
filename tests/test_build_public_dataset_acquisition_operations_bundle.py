from pathlib import Path

import pandas as pd
import yaml

from core.data.build_public_dataset_acquisition_operations_bundle import (
    build_arg_parser,
    build_public_dataset_acquisition_operations_bundle,
)


def test_build_public_dataset_acquisition_operations_bundle(tmp_path: Path):
    status_dashboard = tmp_path / "status.tsv"
    status_summary = tmp_path / "summary.yaml"
    request_path = tmp_path / "request.yaml"
    output_dir = tmp_path / "operations"

    pd.DataFrame([
        {
            "dataset_id": "dataset_a",
            "display_name": "Dataset A",
            "source_id": "gdc_tcga",
            "accession_or_project_id": "TCGA-TEST",
            "atlas_hint": "brca",
            "modality": "transcriptomics",
            "expected_file_type": "matrix",
            "acquisition_needed": 1,
            "acquisition_status": "pending_acquisition_workspace_ready",
            "target_local_path": str(tmp_path / "real.tsv"),
            "target_local_path_exists_current": 0,
            "dataset_workspace_dir": str(tmp_path / "workspace"),
            "dataset_readme": str(tmp_path / "workspace" / "README.md"),
            "dataset_readme_exists": 1,
            "dataset_readme_exists_current": 1,
            "next_action": "Acquire file",
            "operator_action": "Acquire/export public file and place at target_local_path",
        }
    ]).to_csv(status_dashboard, sep="\t", index=False)

    with status_summary.open("w", encoding="utf-8") as handle:
        yaml.safe_dump({"request_id": "upstream_status", "atlas_name": "test_public", "output_dir": str(tmp_path)}, handle, sort_keys=False)

    with request_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "request_id": "test_operations",
                "atlas_name": "test_public",
                "inputs": {
                    "acquisition_status_dashboard": str(status_dashboard),
                    "acquisition_status_summary": str(status_summary),
                },
                "expected_outputs": {"acquisition_operations_dir": str(output_dir)},
            },
            handle,
            sort_keys=False,
        )

    summary, task_board_df, source_templates_df, progress_rollup_df, paths = build_public_dataset_acquisition_operations_bundle(request_path=request_path)

    assert paths["task_board"].exists()
    assert paths["checklist"].exists()
    assert paths["source_templates"].exists()
    assert paths["progress_rollup"].exists()
    assert paths["operations_summary"].exists()
    assert paths["operations_report"].exists()
    assert summary["dataset_count"] == 1
    assert summary["tasks_open"] == 1
    assert summary["tasks_complete"] == 0
    assert summary["source_template_count"] == 1
    assert task_board_df.loc[0, "task_status"] == "open_pending_acquisition"
    assert not source_templates_df.empty
    assert not progress_rollup_df.empty


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--request", "request.yaml", "--output-dir", "out"])
    assert str(args.request).endswith("request.yaml")
    assert str(args.output_dir).endswith("out")

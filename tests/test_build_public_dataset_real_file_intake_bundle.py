from pathlib import Path

import pandas as pd
import yaml

from core.data.build_public_dataset_real_file_intake_bundle import (
    build_arg_parser,
    build_public_dataset_real_file_intake_bundle,
)


def test_build_public_dataset_real_file_intake_bundle(tmp_path: Path):
    task_board = tmp_path / "task_board.tsv"
    operations_summary = tmp_path / "operations_summary.yaml"
    request_path = tmp_path / "request.yaml"
    output_dir = tmp_path / "intake"
    dropzone_root = tmp_path / "dropzone"

    pd.DataFrame([
        {
            "task_id": "acquire_dataset_a",
            "dataset_id": "dataset_a",
            "display_name": "Dataset A",
            "source_id": "gdc_tcga",
            "accession_or_project_id": "TCGA-TEST",
            "atlas_hint": "brca",
            "modality": "transcriptomics",
            "expected_file_type": "matrix",
            "task_status": "open_pending_acquisition",
            "acquisition_status": "pending_acquisition_workspace_ready",
            "target_local_path": str(tmp_path / "real.tsv"),
            "target_local_path_exists_current": 0,
            "dataset_workspace_dir": str(tmp_path / "workspace"),
            "dataset_readme": str(tmp_path / "workspace" / "README.md"),
            "dataset_readme_exists_current": 1,
            "operator_action": "Acquire/export public file and place at target_local_path",
            "source_template": "Use GDC.",
        }
    ]).to_csv(task_board, sep="\t", index=False)

    with operations_summary.open("w", encoding="utf-8") as handle:
        yaml.safe_dump({"request_id": "upstream_operations", "atlas_name": "test_public", "output_dir": str(tmp_path)}, handle, sort_keys=False)

    with request_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "request_id": "test_intake",
                "atlas_name": "test_public",
                "inputs": {"acquisition_task_board": str(task_board), "acquisition_operations_summary": str(operations_summary)},
                "expected_outputs": {"real_file_intake_dir": str(output_dir), "dropzone_root": str(dropzone_root)},
            },
            handle,
            sort_keys=False,
        )

    summary, intake_df, readme_df, source_df, paths = build_public_dataset_real_file_intake_bundle(request_path=request_path)

    assert paths["intake_inventory"].exists()
    assert paths["dropzone_readme_inventory"].exists()
    assert paths["intake_summary"].exists()
    assert paths["intake_report"].exists()
    assert summary["dataset_count"] == 1
    assert summary["dropzone_dir_count"] == 1
    assert summary["dropzone_readme_count"] == 1
    assert summary["candidate_file_count"] == 0
    assert summary["awaiting_file_count"] == 1
    assert Path(intake_df.loc[0, "dropzone_readme"]).exists()
    assert not readme_df.empty
    assert not source_df.empty


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--request", "request.yaml", "--output-dir", "out", "--dropzone-root", "dropzone"])
    assert str(args.request).endswith("request.yaml")
    assert str(args.output_dir).endswith("out")
    assert str(args.dropzone_root).endswith("dropzone")

from pathlib import Path

import pandas as pd
import yaml

from core.data.build_public_dataset_acquisition_status_dashboard import (
    build_arg_parser,
    build_public_dataset_acquisition_status_dashboard,
)


def test_build_public_dataset_acquisition_status_dashboard(tmp_path: Path):
    workspace_index = tmp_path / "workspace_index.tsv"
    workspace_summary = tmp_path / "workspace_summary.yaml"
    source_index = tmp_path / "source.tsv"
    request_path = tmp_path / "request.yaml"
    output_dir = tmp_path / "dashboard"
    readme = tmp_path / "workspace" / "dataset_a" / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text("# Dataset A\n", encoding="utf-8")

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
                "acquisition_needed": 1,
                "target_local_path": str(tmp_path / "real.tsv"),
                "target_local_path_exists_current": 0,
                "dataset_workspace_dir": str(readme.parent),
                "dataset_readme": str(readme),
                "dataset_readme_exists": 1,
                "next_action": "Acquire file",
            }
        ]
    ).to_csv(workspace_index, sep="\t", index=False)

    with workspace_summary.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "request_id": "upstream_workspace",
                "atlas_name": "test_public",
                "output_dir": str(tmp_path / "workspace"),
            },
            handle,
            sort_keys=False,
        )

    pd.DataFrame([{"artifact_label": "workspace", "path": str(workspace_index), "exists": 1}]).to_csv(source_index, sep="\t", index=False)

    with request_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "request_id": "test_status_dashboard",
                "atlas_name": "test_public",
                "inputs": {
                    "acquisition_workspace_index": str(workspace_index),
                    "acquisition_workspace_summary": str(workspace_summary),
                    "acquisition_workspace_source_artifact_index": str(source_index),
                },
                "expected_outputs": {"acquisition_status_dashboard_dir": str(output_dir)},
            },
            handle,
            sort_keys=False,
        )

    summary, status_df, source_summary_df, modality_summary_df, source_df, paths = build_public_dataset_acquisition_status_dashboard(request_path=request_path)

    assert paths["status_dashboard"].exists()
    assert paths["status_by_source"].exists()
    assert paths["status_by_modality"].exists()
    assert paths["source_artifact_index"].exists()
    assert paths["status_summary"].exists()
    assert paths["status_report"].exists()
    assert summary["dataset_count"] == 1
    assert summary["pending_acquisition_count"] == 1
    assert summary["local_file_present_count"] == 0
    assert status_df.loc[0, "acquisition_status"] == "pending_acquisition_workspace_ready"
    assert not source_summary_df.empty
    assert not modality_summary_df.empty
    assert not source_df.empty


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--request", "request.yaml", "--output-dir", "out"])
    assert str(args.request).endswith("request.yaml")
    assert str(args.output_dir).endswith("out")

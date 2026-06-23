from pathlib import Path

import pandas as pd
import yaml

from core.data.build_public_dataset_acquisition_workspace import (
    build_arg_parser,
    build_public_dataset_acquisition_workspace,
)


def test_build_public_dataset_acquisition_workspace(tmp_path: Path):
    instructions = tmp_path / "instructions.tsv"
    acquisition_summary = tmp_path / "summary.yaml"
    source_index = tmp_path / "source.tsv"
    request_path = tmp_path / "request.yaml"
    output_dir = tmp_path / "workspace"

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
                "acquisition_instruction": "Use GDC to export TCGA-TEST.",
                "next_action": "Acquire/export data and save to target path.",
                "post_acquisition_validation_commands": "python -m core.data.validate_public_dataset_replacement_readiness; python -m core.data.validate_public_dataset_replacement_files",
            }
        ]
    ).to_csv(instructions, sep="\t", index=False)

    with acquisition_summary.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "request_id": "upstream_acquisition",
                "atlas_name": "test_public",
                "output_dir": str(tmp_path / "instructions"),
            },
            handle,
            sort_keys=False,
        )

    pd.DataFrame([{"artifact_label": "instructions", "path": str(instructions), "exists": 1}]).to_csv(source_index, sep="\t", index=False)

    with request_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "request_id": "test_workspace",
                "atlas_name": "test_public",
                "inputs": {
                    "acquisition_instructions": str(instructions),
                    "acquisition_summary": str(acquisition_summary),
                    "acquisition_source_artifact_index": str(source_index),
                },
                "expected_outputs": {"acquisition_workspace_dir": str(output_dir)},
                "workspace_policy": {
                    "create_dataset_workspace_dirs": True,
                    "create_per_dataset_readme_files": True,
                    "do_not_create_or_modify_real_replacement_files": True,
                    "include_post_acquisition_validation_commands": True,
                },
            },
            handle,
            sort_keys=False,
        )

    summary, workspace_df, source_df, paths = build_public_dataset_acquisition_workspace(request_path=request_path)

    assert paths["workspace_index"].exists()
    assert paths["source_artifact_index"].exists()
    assert paths["workspace_summary"].exists()
    assert paths["workspace_report"].exists()
    assert summary["workspace_dataset_count"] == 1
    assert summary["acquisition_needed_count"] == 1
    assert summary["dataset_readme_count"] == 1
    assert workspace_df.loc[0, "dataset_id"] == "dataset_a"
    assert Path(workspace_df.loc[0, "dataset_readme"]).exists()
    assert not source_df.empty


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--request", "request.yaml", "--output-dir", "out"])
    assert str(args.request).endswith("request.yaml")
    assert str(args.output_dir).endswith("out")

from pathlib import Path

import pandas as pd
import yaml

from core.data.build_public_dataset_replacement_workflow import (
    build_arg_parser,
    build_public_dataset_replacement_workflow,
)


def test_build_public_dataset_replacement_workflow(tmp_path: Path):
    registry_path = tmp_path / "registry.yaml"
    local_requirements = tmp_path / "local_requirements.tsv"
    manifest_inventory = tmp_path / "manifest_inventory.tsv"
    dashboard_summary = tmp_path / "dashboard.yaml"
    request_path = tmp_path / "request.yaml"
    output_dir = tmp_path / "replacement"
    source_manifest = tmp_path / "source_manifest.yaml"

    with registry_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "datasets": {
                    "dataset_a": {
                        "display_name": "Dataset A",
                        "source_id": "source_a",
                        "accession_or_project_id": "ACC-A",
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

    placeholder = tmp_path / "placeholder.tsv"
    placeholder.write_text("sample_id\tGENE1\nS1\t1\n", encoding="utf-8")
    pd.DataFrame(
        [
            {
                "atlas_hint": "brca",
                "modality": "transcriptomics",
                "local_file_path": str(placeholder),
            }
        ]
    ).to_csv(local_requirements, sep="\t", index=False)

    with source_manifest.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "manifest_id": "brca_transcriptomics_materialized_public_data_manifest",
                "atlas_name": "brca",
                "modality": "transcriptomics",
                "input_files": [{"path": str(placeholder)}],
            },
            handle,
            sort_keys=False,
        )

    pd.DataFrame(
        [
            {
                "atlas_hint": "brca",
                "modality": "transcriptomics",
                "materialized_manifest_stub": str(source_manifest),
            }
        ]
    ).to_csv(manifest_inventory, sep="\t", index=False)

    with dashboard_summary.open("w", encoding="utf-8") as handle:
        yaml.safe_dump({"portfolio_id": "portfolio_test"}, handle, sort_keys=False)

    with request_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "request_id": "test_replacement",
                "atlas_name": "test_public",
                "dataset_accession_registry": str(registry_path),
                "local_file_requirements": str(local_requirements),
                "materialized_manifest_inventory": str(manifest_inventory),
                "portfolio_dashboard_summary": str(dashboard_summary),
                "expected_outputs": {"replacement_workflow_dir": str(output_dir)},
            },
            handle,
            sort_keys=False,
        )

    summary, plan_df, stub_df, source_df, paths = build_public_dataset_replacement_workflow(request_path=request_path)

    assert paths["replacement_plan"].exists()
    assert paths["replacement_manifest_inventory"].exists()
    assert paths["source_artifact_index"].exists()
    assert paths["replacement_summary"].exists()
    assert paths["replacement_report"].exists()
    assert summary["replacement_candidate_count"] == 1
    assert summary["replacement_manifest_stub_count"] == 1
    assert not plan_df.empty
    assert not stub_df.empty
    assert not source_df.empty


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--request", "request.yaml", "--output-dir", "out"])
    assert str(args.request).endswith("request.yaml")
    assert str(args.output_dir).endswith("out")

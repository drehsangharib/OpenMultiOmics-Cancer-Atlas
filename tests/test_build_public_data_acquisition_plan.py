from pathlib import Path

import yaml

from core.data.build_public_data_acquisition_plan import (
    build_arg_parser,
    build_public_data_acquisition_plan,
)


def test_build_public_data_acquisition_plan(tmp_path: Path):
    registry_path = tmp_path / "registry.yaml"
    request_path = tmp_path / "request.yaml"
    output_dir = tmp_path / "plan"

    with registry_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "sources": {
                    "source_a": {
                        "display_name": "Source A",
                        "source_type": "public_repository",
                        "access_mode": "manifest_export",
                        "status": "scaffold",
                        "supported_modalities": ["transcriptomics"],
                        "suggested_atlases": ["brca"],
                        "identifier_examples": ["A1"],
                        "acquisition_notes": "test",
                    }
                }
            },
            handle,
            sort_keys=False,
        )

    with request_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "request_id": "test_request",
                "atlas_name": "test_public_atlas",
                "requested_sources": [
                    {
                        "source_id": "source_a",
                        "atlas_hint": "brca",
                        "modality": "transcriptomics",
                        "dataset_query": "test query",
                        "priority": 1,
                    }
                ],
                "expected_outputs": {"acquisition_plan_dir": str(output_dir)},
            },
            handle,
            sort_keys=False,
        )

    summary, source_inventory_df, acquisition_plan_df, template_inventory_df, paths = build_public_data_acquisition_plan(
        request_path=request_path,
        source_registry_path=registry_path,
    )

    assert paths["source_inventory"].exists()
    assert paths["acquisition_plan"].exists()
    assert paths["manifest_template_inventory"].exists()
    assert paths["acquisition_summary"].exists()
    assert paths["acquisition_report"].exists()
    assert summary["registered_source_count"] == 1
    assert summary["requested_dataset_count"] == 1
    assert summary["manifest_template_count"] == 1
    assert not source_inventory_df.empty
    assert not acquisition_plan_df.empty
    assert not template_inventory_df.empty


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--request", "request.yaml", "--source-registry", "registry.yaml"])
    assert str(args.request).endswith("request.yaml")
    assert str(args.source_registry).endswith("registry.yaml")

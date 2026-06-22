from pathlib import Path

import pandas as pd
import yaml

from core.data.materialize_public_data_files import (
    build_arg_parser,
    materialize_public_data_files,
)


def test_materialize_public_data_files(tmp_path: Path):
    acquisition_dir = tmp_path / "acquisition"
    templates_dir = acquisition_dir / "manifest_templates"
    materialization_dir = tmp_path / "materialized"
    templates_dir.mkdir(parents=True, exist_ok=True)

    acquisition_summary = acquisition_dir / "public_data_acquisition_summary.yaml"
    template_inventory = acquisition_dir / "manifest_template_inventory.tsv"
    request_path = tmp_path / "materialization_request.yaml"

    with acquisition_summary.open("w", encoding="utf-8") as handle:
        yaml.safe_dump({"requested_dataset_count": 1, "atlas_name": "test_public"}, handle, sort_keys=False)

    template_path = templates_dir / "brca_transcriptomics_public_data_manifest.yaml"
    with template_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "manifest_id": "brca_transcriptomics_public_data_manifest",
                "atlas_name": "brca",
                "modality": "transcriptomics",
                "data_type": "public_transcriptomics_matrix_or_manifest",
                "source_name": "source_a",
                "input_files": [
                    {
                        "file_id": "matrix",
                        "path": "placeholder.tsv",
                        "file_format": "tsv",
                        "matrix_orientation": "samples_by_features",
                        "sample_id_column": "sample_id",
                        "feature_id_type": "placeholder",
                    }
                ],
                "processing_plan": {"max_missing_fraction": 0.5},
            },
            handle,
            sort_keys=False,
        )

    pd.DataFrame(
        [
            {
                "source_id": "source_a",
                "modality": "transcriptomics",
                "atlas_hint": "brca",
                "manifest_template": str(template_path),
            }
        ]
    ).to_csv(template_inventory, sep="\t", index=False)

    with request_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "request_id": "test_materialize",
                "atlas_name": "test_public",
                "acquisition_summary": str(acquisition_summary),
                "manifest_template_inventory": str(template_inventory),
                "local_data_root": str(tmp_path / "data"),
                "materialization_policy": {"create_placeholder_files": True, "overwrite_existing_placeholders": True},
                "expected_outputs": {"materialization_dir": str(materialization_dir)},
            },
            handle,
            sort_keys=False,
        )

    summary, file_requirements_df, manifest_inventory_df, paths = materialize_public_data_files(request_path=request_path)

    assert paths["local_file_requirements"].exists()
    assert paths["materialized_manifest_inventory"].exists()
    assert paths["materialization_summary"].exists()
    assert paths["materialization_report"].exists()
    assert summary["local_file_requirement_count"] == 1
    assert summary["materialized_manifest_stub_count"] == 1
    assert summary["placeholder_file_count"] == 1
    assert Path(file_requirements_df.loc[0, "local_file_path"]).exists()
    assert Path(manifest_inventory_df.loc[0, "materialized_manifest_stub"]).exists()


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--request", "request.yaml"])
    assert str(args.request).endswith("request.yaml")

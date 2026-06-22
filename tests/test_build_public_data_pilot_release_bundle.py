from pathlib import Path

import pandas as pd
import yaml

from core.data.build_public_data_pilot_release_bundle import (
    build_arg_parser,
    build_public_data_pilot_release_bundle,
)


def test_build_public_data_pilot_release_bundle(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir(parents=True, exist_ok=True)
    release_dir = tmp_path / "release"

    integration_summary = source / "summary.yaml"
    artifact_inventory = source / "inventory.tsv"
    integration_report = source / "report.html"
    pilot_bundle_manifest = source / "bundle.yaml"
    request_path = tmp_path / "request.yaml"

    with integration_summary.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "atlas_name": "test_public",
                "input_feature_store_count": 4,
                "integrated_samples": 3,
                "integrated_features": 12,
                "external_evidence_rows": 12,
            },
            handle,
            sort_keys=False,
        )
    pd.DataFrame([{"artifact_label": "x", "path": "x", "exists": 1, "size_bytes": 1}]).to_csv(artifact_inventory, sep="\t", index=False)
    integration_report.write_text("<html>report</html>", encoding="utf-8")
    with pilot_bundle_manifest.open("w", encoding="utf-8") as handle:
        yaml.safe_dump({"bundle": "test"}, handle, sort_keys=False)

    with request_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "request_id": "test_release",
                "release_id": "test-a20",
                "release_name": "Test release",
                "atlas_name": "test_public",
                "source_integration_summary": str(integration_summary),
                "source_integration_artifact_inventory": str(artifact_inventory),
                "source_integration_report": str(integration_report),
                "source_pilot_bundle_manifest": str(pilot_bundle_manifest),
                "expected_outputs": {"release_dir": str(release_dir)},
            },
            handle,
            sort_keys=False,
        )

    summary, copied_df, inventory_df, paths = build_public_data_pilot_release_bundle(request_path=request_path)

    assert paths["release_manifest"].exists()
    assert paths["release_inventory"].exists()
    assert paths["release_report"].exists()
    assert paths["release_readme"].exists()
    assert paths["release_archive"].exists()
    assert summary["release_id"] == "test-a20"
    assert summary["integrated_features"] == 12
    assert not copied_df.empty
    assert not inventory_df.empty


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--request", "request.yaml", "--output-dir", "out"])
    assert str(args.request).endswith("request.yaml")
    assert str(args.output_dir).endswith("out")

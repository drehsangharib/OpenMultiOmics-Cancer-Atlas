from pathlib import Path

import pandas as pd
import yaml

from core.releases.build_end_to_end_release_bundle import (
    build_arg_parser,
    build_end_to_end_release_bundle,
)


def test_build_end_to_end_release_bundle(tmp_path: Path):
    reports = tmp_path / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    release_dir = tmp_path / "release"
    config_path = tmp_path / "release_config.yaml"

    summary_path = reports / "end_to_end_demo_summary.yaml"
    inventory_path = reports / "end_to_end_artifact_inventory.tsv"
    capability_path = reports / "platform_capability_map.tsv"
    report_path = reports / "end_to_end_demo_report.html"

    with summary_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "demo_run_id": "test_demo",
                "atlas_name": "test_atlas",
                "final_stage": "external_annotation_connector_scaffold",
                "integrated_samples": 3,
                "integrated_features": 12,
                "external_evidence_rows": 12,
            },
            handle,
            sort_keys=False,
        )

    source_artifact = reports / "artifact.txt"
    source_artifact.write_text("artifact", encoding="utf-8")
    pd.DataFrame(
        [
            {
                "artifact_label": "artifact",
                "path": str(source_artifact),
                "exists": 1,
                "size_bytes": source_artifact.stat().st_size,
            }
        ]
    ).to_csv(inventory_path, sep="\t", index=False)

    pd.DataFrame([{"layer": "A13", "capability": "demo", "status": "current"}]).to_csv(capability_path, sep="\t", index=False)
    report_path.write_text("<html>demo</html>", encoding="utf-8")

    with config_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "release_id": "test-release",
                "release_name": "Test release",
                "atlas_name": "test_atlas",
                "source_reports": {
                    "end_to_end_demo_summary": str(summary_path),
                    "end_to_end_artifact_inventory": str(inventory_path),
                    "platform_capability_map": str(capability_path),
                    "end_to_end_demo_report": str(report_path),
                },
                "expected_outputs": {"release_dir": str(release_dir)},
            },
            handle,
            sort_keys=False,
        )

    release_manifest, artifact_inventory_df, capability_df, paths = build_end_to_end_release_bundle(config_path=config_path)

    assert paths["release_manifest"].exists()
    assert paths["release_artifact_inventory"].exists()
    assert paths["release_capability_map"].exists()
    assert paths["release_summary_report"].exists()
    assert paths["release_readme"].exists()
    assert paths["release_archive"].exists()
    assert release_manifest["release_id"] == "test-release"
    assert release_manifest["artifact_count"] >= 1
    assert not artifact_inventory_df.empty
    assert not capability_df.empty


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--config", "release.yaml", "--release-dir", "release"])
    assert str(args.config).endswith("release.yaml")
    assert str(args.release_dir).endswith("release")

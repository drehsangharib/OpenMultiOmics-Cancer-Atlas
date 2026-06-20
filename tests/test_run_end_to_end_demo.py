from pathlib import Path

import pandas as pd
import yaml

from core.pipelines.run_end_to_end_demo import (
    build_arg_parser,
    build_capability_map,
    collect_artifact_inventory,
    resolve_demo_config,
)


def test_resolve_demo_config(tmp_path: Path):
    config_path = tmp_path / "demo.yaml"
    with config_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "demo_run_id": "test_demo",
                "atlas_name": "test_atlas",
                "feature_store_manifests": ["a.yaml", "b.yaml"],
                "expected_outputs": {"final_report_dir": "reports"},
            },
            handle,
            sort_keys=False,
        )

    cfg = resolve_demo_config(config_path=config_path)
    assert cfg["demo_run_id"] == "test_demo"
    assert cfg["atlas_name"] == "test_atlas"
    assert len(cfg["feature_store_manifests"]) == 2


def test_collect_artifact_inventory(tmp_path: Path):
    existing = tmp_path / "exists.txt"
    existing.write_text("hello", encoding="utf-8")
    missing = tmp_path / "missing.txt"

    df = collect_artifact_inventory({"existing": existing, "missing": missing})
    assert df.shape[0] == 2
    assert int(df.loc[df["artifact_label"] == "existing", "exists"].iloc[0]) == 1
    assert int(df.loc[df["artifact_label"] == "missing", "exists"].iloc[0]) == 0


def test_build_capability_map():
    df = build_capability_map()
    assert not df.empty
    assert "A13" in set(df["layer"])


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--atlas", "demo", "--manifest-paths", "a.yaml", "b.yaml"])
    assert args.atlas == "demo"
    assert args.manifest_paths == ["a.yaml", "b.yaml"]

from pathlib import Path

import pandas as pd
import yaml

from core.data.run_public_data_pilot_integration import (
    build_arg_parser,
    collect_feature_store_manifests,
    collect_integration_artifact_inventory,
)


def test_collect_feature_store_manifests(tmp_path: Path):
    manifest = tmp_path / "feature_store_manifest.yaml"
    manifest.write_text("x", encoding="utf-8")
    df = pd.DataFrame([{"feature_store_manifest": str(manifest)}])
    paths = collect_feature_store_manifests(df)
    assert paths == [manifest]


def test_collect_integration_artifact_inventory(tmp_path: Path):
    existing = tmp_path / "exists.txt"
    existing.write_text("hello", encoding="utf-8")
    missing = tmp_path / "missing.txt"
    df = collect_integration_artifact_inventory({"existing": existing, "missing": missing})
    assert df.shape[0] == 2
    assert int(df.loc[df["artifact_label"] == "existing", "exists"].iloc[0]) == 1
    assert int(df.loc[df["artifact_label"] == "missing", "exists"].iloc[0]) == 0


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--request", "request.yaml", "--output-dir", "out"])
    assert str(args.request).endswith("request.yaml")
    assert str(args.output_dir).endswith("out")

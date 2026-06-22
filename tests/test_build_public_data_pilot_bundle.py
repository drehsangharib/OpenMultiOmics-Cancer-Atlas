from pathlib import Path

import pandas as pd
import yaml

from core.data.build_public_data_pilot_bundle import (
    build_arg_parser,
    build_public_data_pilot_bundle,
)


def test_build_public_data_pilot_bundle(tmp_path: Path):
    feature_store = tmp_path / "features" / "transcriptomics" / "brca"
    feature_store.mkdir(parents=True, exist_ok=True)
    for name in ["normalized_matrix.tsv", "sample_metadata.tsv", "feature_metadata.tsv", "qc_summary.tsv", "feature_store_manifest.yaml"]:
        (feature_store / name).write_text("x", encoding="utf-8")

    smoke_dir = tmp_path / "smoke"
    smoke_dir.mkdir(parents=True, exist_ok=True)
    smoke_summary = smoke_dir / "execution_smoke_summary.yaml"
    smoke_results = smoke_dir / "execution_smoke_results.tsv"
    bundle_dir = tmp_path / "bundle"
    request_path = tmp_path / "bundle_request.yaml"

    with smoke_summary.open("w", encoding="utf-8") as handle:
        yaml.safe_dump({"smoke_run_count": 1, "smoke_pass_count": 1}, handle, sort_keys=False)

    pd.DataFrame(
        [
            {
                "atlas_hint": "brca",
                "modality": "transcriptomics",
                "processor_module": "fake.module",
                "passed": 1,
                "feature_store_dir": str(feature_store),
            }
        ]
    ).to_csv(smoke_results, sep="\t", index=False)

    with request_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "request_id": "test_bundle",
                "atlas_name": "test_public",
                "execution_smoke_summary": str(smoke_summary),
                "execution_smoke_results": str(smoke_results),
                "expected_outputs": {"pilot_bundle_dir": str(bundle_dir)},
                "bundle_policy": {"require_all_smoke_passed": True},
            },
            handle,
            sort_keys=False,
        )

    summary, bundle_inventory_df, copied_artifacts_df, modality_summary_df, paths = build_public_data_pilot_bundle(request_path=request_path)

    assert paths["bundle_inventory"].exists()
    assert paths["copied_artifact_inventory"].exists()
    assert paths["modality_summary"].exists()
    assert paths["bundle_manifest"].exists()
    assert paths["bundle_report"].exists()
    assert paths["bundle_archive"].exists()
    assert summary["feature_store_count"] == 1
    assert summary["copied_artifact_count"] == 5
    assert not bundle_inventory_df.empty
    assert not copied_artifacts_df.empty
    assert not modality_summary_df.empty


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--request", "request.yaml"])
    assert str(args.request).endswith("request.yaml")

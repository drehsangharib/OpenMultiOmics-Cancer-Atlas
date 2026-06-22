from pathlib import Path

import yaml

from core.data.build_public_data_portfolio_dashboard import (
    build_arg_parser,
    build_public_data_portfolio_dashboard,
)


def write_yaml_file(path: Path, payload):
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)


def test_build_public_data_portfolio_dashboard(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir(parents=True, exist_ok=True)
    output_dir = tmp_path / "dashboard"
    request_path = tmp_path / "dashboard_request.yaml"

    artifacts = {
        "acquisition_summary": source / "acquisition.yaml",
        "materialization_summary": source / "materialization.yaml",
        "execution_smoke_summary": source / "smoke.yaml",
        "pilot_bundle_manifest": source / "bundle.yaml",
        "pilot_integration_summary": source / "integration.yaml",
        "pilot_release_manifest": source / "release.yaml",
    }

    write_yaml_file(artifacts["acquisition_summary"], {"registered_source_count": 3, "requested_dataset_count": 4})
    write_yaml_file(artifacts["materialization_summary"], {"materialized_manifest_stub_count": 4, "placeholder_file_count": 4})
    write_yaml_file(artifacts["execution_smoke_summary"], {"smoke_run_count": 4, "smoke_pass_count": 4, "smoke_fail_count": 0})
    write_yaml_file(artifacts["pilot_bundle_manifest"], {"feature_store_count": 4, "copied_artifact_count": 20})
    write_yaml_file(artifacts["pilot_integration_summary"], {"integrated_samples": 3, "integrated_features": 12, "external_evidence_rows": 12})
    write_yaml_file(artifacts["pilot_release_manifest"], {"copied_source_artifact_count": 4})

    write_yaml_file(
        request_path,
        {
            "request_id": "test_dashboard",
            "portfolio_id": "test_portfolio",
            "portfolio_name": "Test portfolio",
            "atlas_name": "test_public",
            "source_artifacts": {key: str(value) for key, value in artifacts.items()},
            "expected_outputs": {"dashboard_dir": str(output_dir)},
            "portfolio_policy": {"require_all_source_artifacts": True},
        },
    )

    summary, stage_df, metrics_df, artifact_df, paths = build_public_data_portfolio_dashboard(request_path=request_path)

    assert paths["dashboard_summary"].exists()
    assert paths["workflow_stage_summary"].exists()
    assert paths["portfolio_metrics"].exists()
    assert paths["source_artifact_index"].exists()
    assert paths["html_dashboard"].exists()
    assert paths["markdown_dashboard"].exists()
    assert summary["workflow_stage_count"] == 6
    assert int(metrics_df.loc[metrics_df["metric"] == "smoke_pass_count", "value"].iloc[0]) == 4
    assert not stage_df.empty
    assert artifact_df.shape[0] == 6


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--request", "request.yaml", "--output-dir", "out"])
    assert str(args.request).endswith("request.yaml")
    assert str(args.output_dir).endswith("out")

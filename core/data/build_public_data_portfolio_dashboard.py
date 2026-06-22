#!/usr/bin/env python3

import argparse
import html
import sys
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_DASHBOARD_REQUEST = Path("configs/public_data_sources/public_data_portfolio_dashboard_request.yaml")
DEFAULT_OUTPUT_ROOT = Path("outputs/public_data_acquisition")


def load_yaml_mapping(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"YAML file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain a mapping: {path}")
    return data


def write_yaml(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)


def ensure_dir(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def escape_html(value):
    if value is None:
        return ""
    return html.escape(str(value))


def dataframe_to_html_table(df, max_rows=150):
    if df.empty:
        return "<p>No records available.</p>"
    out = df.head(max_rows).copy()
    lines = ["<table border='1' cellspacing='0' cellpadding='5'>", "<thead><tr>"]
    for column in out.columns:
        lines.append(f"<th>{escape_html(column)}</th>")
    lines.append("</tr></thead><tbody>")
    for _, row in out.iterrows():
        lines.append("<tr>")
        for column in out.columns:
            lines.append(f"<td>{escape_html(row[column])}</td>")
        lines.append("</tr>")
    lines.append("</tbody></table>")
    return "\n".join(lines)


def scalar(summary, key, default=0):
    value = summary.get(key, default)
    try:
        return int(value)
    except Exception:
        return default


def load_source_artifacts(request, require_all=True):
    source_artifacts = request.get("source_artifacts", {}) or {}
    if not source_artifacts:
        raise ValueError("Dashboard request must contain source_artifacts")
    loaded = {}
    rows = []
    for label, path in source_artifacts.items():
        path = Path(path)
        exists = path.exists()
        if require_all and not exists:
            raise FileNotFoundError(f"Missing source artifact for dashboard: {label} -> {path}")
        data = load_yaml_mapping(path) if exists and path.suffix.lower() in {".yaml", ".yml"} else {}
        loaded[label] = data
        rows.append(
            {
                "artifact_label": str(label),
                "path": str(path),
                "exists": int(exists),
                "size_bytes": int(path.stat().st_size) if exists else 0,
            }
        )
    return loaded, pd.DataFrame(rows)


def build_workflow_stage_summary(loaded):
    acquisition = loaded.get("acquisition_summary", {})
    materialization = loaded.get("materialization_summary", {})
    smoke = loaded.get("execution_smoke_summary", {})
    bundle = loaded.get("pilot_bundle_manifest", {})
    integration = loaded.get("pilot_integration_summary", {})
    release = loaded.get("pilot_release_manifest", {})

    rows = [
        {
            "stage_order": 1,
            "stage_id": "public_data_acquisition",
            "stage_name": "Public-data acquisition planning",
            "primary_count_label": "requested_datasets",
            "primary_count": scalar(acquisition, "requested_dataset_count"),
            "status": "available" if acquisition else "missing",
        },
        {
            "stage_order": 2,
            "stage_id": "local_file_materialization",
            "stage_name": "Local file materialization",
            "primary_count_label": "manifest_stubs",
            "primary_count": scalar(materialization, "materialized_manifest_stub_count"),
            "status": "available" if materialization else "missing",
        },
        {
            "stage_order": 3,
            "stage_id": "execution_smoke",
            "stage_name": "Public-data execution smoke test",
            "primary_count_label": "smoke_pass_count",
            "primary_count": scalar(smoke, "smoke_pass_count"),
            "status": "pass" if scalar(smoke, "smoke_fail_count") == 0 and smoke else "review",
        },
        {
            "stage_order": 4,
            "stage_id": "pilot_feature_store_bundle",
            "stage_name": "Pilot feature-store bundle",
            "primary_count_label": "feature_stores",
            "primary_count": scalar(bundle, "feature_store_count"),
            "status": "available" if bundle else "missing",
        },
        {
            "stage_order": 5,
            "stage_id": "pilot_integration",
            "stage_name": "Public-data pilot integration",
            "primary_count_label": "integrated_features",
            "primary_count": scalar(integration, "integrated_features"),
            "status": "available" if integration else "missing",
        },
        {
            "stage_order": 6,
            "stage_id": "pilot_release_bundle",
            "stage_name": "Public-data pilot release bundle",
            "primary_count_label": "copied_source_artifacts",
            "primary_count": scalar(release, "copied_source_artifact_count"),
            "status": "available" if release else "missing",
        },
    ]
    return pd.DataFrame(rows)


def build_portfolio_metrics(loaded):
    acquisition = loaded.get("acquisition_summary", {})
    materialization = loaded.get("materialization_summary", {})
    smoke = loaded.get("execution_smoke_summary", {})
    bundle = loaded.get("pilot_bundle_manifest", {})
    integration = loaded.get("pilot_integration_summary", {})
    release = loaded.get("pilot_release_manifest", {})

    metrics = {
        "registered_source_count": scalar(acquisition, "registered_source_count"),
        "requested_dataset_count": scalar(acquisition, "requested_dataset_count"),
        "materialized_manifest_stub_count": scalar(materialization, "materialized_manifest_stub_count"),
        "placeholder_file_count": scalar(materialization, "placeholder_file_count"),
        "smoke_run_count": scalar(smoke, "smoke_run_count"),
        "smoke_pass_count": scalar(smoke, "smoke_pass_count"),
        "smoke_fail_count": scalar(smoke, "smoke_fail_count"),
        "feature_store_count": scalar(bundle, "feature_store_count"),
        "copied_feature_store_artifacts": scalar(bundle, "copied_artifact_count"),
        "input_feature_store_count": scalar(integration, "input_feature_store_count"),
        "integrated_samples": scalar(integration, "integrated_samples"),
        "integrated_features": scalar(integration, "integrated_features"),
        "external_evidence_rows": scalar(integration, "external_evidence_rows"),
        "release_copied_source_artifacts": scalar(release, "copied_source_artifact_count"),
    }
    return pd.DataFrame([{"metric": key, "value": value} for key, value in metrics.items()])


def build_html_dashboard(request, dashboard_summary, stage_df, metrics_df, artifact_df):
    title = "Public-Data Pilot Portfolio Dashboard"
    parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        f"<title>{escape_html(title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This dashboard indexes the public-data pilot workflow from acquisition planning to release packaging.</p>",
        f"<p><strong>Portfolio:</strong> {escape_html(dashboard_summary.get('portfolio_id', ''))}</p>",
        f"<p><strong>Atlas:</strong> {escape_html(dashboard_summary.get('atlas_name', ''))}</p>",
        f"<p><strong>Workflow stages:</strong> {dashboard_summary.get('workflow_stage_count', 0)}</p>",
        "<h2>Portfolio metrics</h2>",
        dataframe_to_html_table(metrics_df),
        "<h2>Workflow stage summary</h2>",
        dataframe_to_html_table(stage_df),
        "<h2>Indexed source artifacts</h2>",
        dataframe_to_html_table(artifact_df),
        "<h2>Recommended next steps</h2>",
        "<ul>",
        "<li>Replace placeholder matrices with real exported public repository files.</li>",
        "<li>Rerun acquisition, materialization, smoke, pilot bundle, integration, and release steps.</li>",
        "<li>Add real public-data dataset accession tracking and biological validation evidence.</li>",
        "</ul>",
        "</body>",
        "</html>",
    ]
    return "\n".join(parts)


def build_markdown_dashboard(dashboard_summary, stage_df, metrics_df):
    lines = [
        f"# {dashboard_summary.get('portfolio_name', 'Public-data pilot portfolio')}",
        "",
        "## Summary",
        "",
        f"- Portfolio ID: `{dashboard_summary.get('portfolio_id', '')}`",
        f"- Atlas: `{dashboard_summary.get('atlas_name', '')}`",
        f"- Workflow stages: `{dashboard_summary.get('workflow_stage_count', 0)}`",
        f"- Indexed source artifacts: `{dashboard_summary.get('indexed_source_artifact_count', 0)}`",
        "",
        "## Key metrics",
        "",
    ]
    for _, row in metrics_df.iterrows():
        lines.append(f"- `{row['metric']}`: `{row['value']}`")
    lines.extend(["", "## Workflow stages", ""])
    for _, row in stage_df.sort_values("stage_order").iterrows():
        lines.append(f"- **{row['stage_name']}** — {row['primary_count_label']}: `{row['primary_count']}`, status: `{row['status']}`")
    lines.extend([
        "",
        "## Interpretation status",
        "",
        "This dashboard indexes scaffold and pilot outputs. Placeholder matrices should be replaced with real public-data files before biological conclusions are made.",
    ])
    return "\n".join(lines) + "\n"


def build_public_data_portfolio_dashboard(request_path=DEFAULT_DASHBOARD_REQUEST, output_dir=None):
    request = load_yaml_mapping(request_path)
    require_all = bool((request.get("portfolio_policy", {}) or {}).get("require_all_source_artifacts", True))
    loaded, artifact_df = load_source_artifacts(request, require_all=require_all)

    expected_outputs = request.get("expected_outputs", {}) or {}
    dashboard_dir = ensure_dir(output_dir or expected_outputs.get("dashboard_dir", DEFAULT_OUTPUT_ROOT / request.get("atlas_name", "public_data_pilot") / "portfolio_dashboard"))

    stage_df = build_workflow_stage_summary(loaded)
    metrics_df = build_portfolio_metrics(loaded)

    paths = {
        "dashboard_summary": Path(dashboard_dir) / "public_data_portfolio_dashboard_summary.yaml",
        "workflow_stage_summary": Path(dashboard_dir) / "public_data_workflow_stage_summary.tsv",
        "portfolio_metrics": Path(dashboard_dir) / "public_data_portfolio_metrics.tsv",
        "source_artifact_index": Path(dashboard_dir) / "public_data_source_artifact_index.tsv",
        "html_dashboard": Path(dashboard_dir) / "index.html",
        "markdown_dashboard": Path(dashboard_dir) / "README.md",
    }

    stage_df.to_csv(paths["workflow_stage_summary"], sep="\t", index=False)
    metrics_df.to_csv(paths["portfolio_metrics"], sep="\t", index=False)
    artifact_df.to_csv(paths["source_artifact_index"], sep="\t", index=False)

    dashboard_summary = {
        "request_id": str(request.get("request_id", "")),
        "portfolio_id": str(request.get("portfolio_id", "")),
        "portfolio_name": str(request.get("portfolio_name", "")),
        "atlas_name": str(request.get("atlas_name", "")),
        "workflow_stage_count": int(stage_df.shape[0]),
        "indexed_source_artifact_count": int(artifact_df.shape[0]),
        "dashboard_dir": str(dashboard_dir),
        "outputs": {label: str(path) for label, path in paths.items()},
        "agent_role": {
            "stage": "public_data_portfolio_dashboard",
            "purpose": "summarize and index the public-data pilot workflow outputs for review and planning",
        },
    }

    write_yaml(paths["dashboard_summary"], dashboard_summary)
    paths["html_dashboard"].write_text(build_html_dashboard(request, dashboard_summary, stage_df, metrics_df, artifact_df), encoding="utf-8")
    paths["markdown_dashboard"].write_text(build_markdown_dashboard(dashboard_summary, stage_df, metrics_df), encoding="utf-8")

    return dashboard_summary, stage_df, metrics_df, artifact_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Build a public-data pilot dashboard index and portfolio report.")
    parser.add_argument("--request", type=Path, default=DEFAULT_DASHBOARD_REQUEST)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        dashboard_summary, stage_df, metrics_df, artifact_df, paths = build_public_data_portfolio_dashboard(
            request_path=args.request,
            output_dir=args.output_dir,
        )
    except Exception as exc:
        print(f"ERROR: Public-data portfolio dashboard build failed: {exc}", file=sys.stderr)
        return 1

    print("Public-data portfolio dashboard complete.")
    print(f"Portfolio: {dashboard_summary['portfolio_id']}")
    print(f"Atlas: {dashboard_summary['atlas_name']}")
    print(f"Workflow stages: {dashboard_summary['workflow_stage_count']}")
    print(f"Dashboard: {paths['html_dashboard']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

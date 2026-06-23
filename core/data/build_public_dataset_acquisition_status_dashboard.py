#!/usr/bin/env python3

import argparse
import html
import sys
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_STATUS_DASHBOARD_REQUEST = Path("configs/public_data_sources/public_dataset_acquisition_status_dashboard_request.yaml")


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


def read_table(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Table not found: {path}")
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_csv(path, sep="\t")


def ensure_dir(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_str(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    return str(value)


def safe_int(value, default=0):
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except TypeError:
        pass
    try:
        return int(value)
    except Exception:
        return default


def escape_html(value):
    return html.escape("" if value is None else str(value))


def dataframe_to_html_table(df, max_rows=250):
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


def require_columns(df, required_columns, table_name):
    missing = set(required_columns) - set(df.columns)
    if missing:
        raise ValueError(f"{table_name} missing columns: " + ", ".join(sorted(missing)))


def classify_acquisition_status(row):
    target_exists = safe_int(row.get("target_local_path_exists_current", 0))
    acquisition_needed = safe_int(row.get("acquisition_needed", 0))
    readme_exists = safe_int(row.get("dataset_readme_exists", 0))
    if target_exists == 1:
        return "local_file_present"
    if acquisition_needed == 1 and readme_exists == 1:
        return "pending_acquisition_workspace_ready"
    if acquisition_needed == 1 and readme_exists != 1:
        return "pending_acquisition_workspace_incomplete"
    return "status_unknown"


def build_status_dashboard(workspace_df):
    require_columns(
        workspace_df,
        {
            "dataset_id",
            "display_name",
            "source_id",
            "accession_or_project_id",
            "atlas_hint",
            "modality",
            "expected_file_type",
            "acquisition_needed",
            "target_local_path",
            "target_local_path_exists_current",
            "dataset_workspace_dir",
            "dataset_readme",
            "dataset_readme_exists",
            "next_action",
        },
        "acquisition_workspace_index",
    )
    df = workspace_df.copy()
    df["target_local_path_exists_current"] = df["target_local_path"].apply(
        lambda p: int(Path(safe_str(p)).exists()) if safe_str(p).strip() else 0
    )
    df["dataset_readme_exists_current"] = df["dataset_readme"].apply(
        lambda p: int(Path(safe_str(p)).exists()) if safe_str(p).strip() else 0
    )
    df["acquisition_status"] = df.apply(classify_acquisition_status, axis=1)
    df["operator_action"] = df.apply(
        lambda row: "Acquire/export public file and place at target_local_path" if row["acquisition_status"].startswith("pending_acquisition") else "Rerun readiness/execution/file-validation gates",
        axis=1,
    )
    keep = [
        "dataset_id",
        "display_name",
        "source_id",
        "accession_or_project_id",
        "atlas_hint",
        "modality",
        "expected_file_type",
        "acquisition_needed",
        "acquisition_status",
        "target_local_path",
        "target_local_path_exists_current",
        "dataset_workspace_dir",
        "dataset_readme",
        "dataset_readme_exists",
        "dataset_readme_exists_current",
        "next_action",
        "operator_action",
    ]
    return df.loc[:, keep].sort_values(["acquisition_status", "dataset_id"]).reset_index(drop=True)


def build_group_summary(status_df, group_column):
    if status_df.empty or group_column not in status_df.columns:
        return pd.DataFrame(columns=[group_column, "dataset_count", "pending_acquisition_count", "local_file_present_count"])
    rows = []
    for key, group in status_df.groupby(group_column, dropna=False):
        rows.append(
            {
                group_column: safe_str(key),
                "dataset_count": int(group.shape[0]),
                "pending_acquisition_count": int(group["acquisition_status"].astype(str).str.startswith("pending_acquisition").sum()),
                "local_file_present_count": int((group["acquisition_status"] == "local_file_present").sum()),
            }
        )
    return pd.DataFrame(rows).sort_values(group_column).reset_index(drop=True)


def build_source_artifact_index(request):
    inputs = request.get("inputs", {}) or {}
    rows = []
    for label in ["acquisition_workspace_index", "acquisition_workspace_summary", "acquisition_workspace_source_artifact_index"]:
        path = safe_str(inputs.get(label, ""))
        rows.append({"artifact_label": label, "path": path, "exists": int(Path(path).exists()) if path else 0})
    return pd.DataFrame(rows)


def build_html_report(request, status_df, source_summary_df, modality_summary_df, source_artifact_df, summary):
    title = "Public Dataset Acquisition Status Dashboard"
    parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        f"<title>{escape_html(title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This dashboard summarizes public dataset acquisition progress from the local acquisition workspace.</p>",
        f"<p><strong>Request:</strong> {escape_html(request.get('request_id', ''))}</p>",
        f"<p><strong>Atlas:</strong> {escape_html(request.get('atlas_name', ''))}</p>",
        f"<p><strong>Dataset count:</strong> {summary.get('dataset_count', 0)}</p>",
        f"<p><strong>Pending acquisition:</strong> {summary.get('pending_acquisition_count', 0)}</p>",
        f"<p><strong>Local files present:</strong> {summary.get('local_file_present_count', 0)}</p>",
        f"<p><strong>Workspace incomplete:</strong> {summary.get('workspace_incomplete_count', 0)}</p>",
        "<h2>Dataset acquisition status</h2>",
        dataframe_to_html_table(status_df),
        "<h2>Status by source</h2>",
        dataframe_to_html_table(source_summary_df),
        "<h2>Status by modality</h2>",
        dataframe_to_html_table(modality_summary_df),
        "<h2>Source artifacts</h2>",
        dataframe_to_html_table(source_artifact_df),
        "<h2>Next step</h2>",
        "<p>Use dataset README files to acquire public data and save files at target_local_path. Then rerun a23, a24, and a25 gates.</p>",
        "</body>",
        "</html>",
    ]
    return "\n".join(parts)


def build_public_dataset_acquisition_status_dashboard(request_path=DEFAULT_STATUS_DASHBOARD_REQUEST, output_dir=None):
    request = load_yaml_mapping(request_path)
    inputs = request.get("inputs", {}) or {}

    workspace_index_path = inputs.get("acquisition_workspace_index")
    workspace_summary_path = inputs.get("acquisition_workspace_summary")
    if not workspace_index_path:
        raise ValueError("Status dashboard request missing inputs.acquisition_workspace_index")
    if not workspace_summary_path:
        raise ValueError("Status dashboard request missing inputs.acquisition_workspace_summary")

    workspace_df = read_table(workspace_index_path)
    workspace_summary = load_yaml_mapping(workspace_summary_path)

    expected_outputs = request.get("expected_outputs", {}) or {}
    output_dir = ensure_dir(
        output_dir
        or expected_outputs.get(
            "acquisition_status_dashboard_dir",
            Path("outputs/public_data_acquisition")
            / request.get("atlas_name", "public_data_pilot")
            / "dataset_acquisition_status_dashboard",
        )
    )

    status_df = build_status_dashboard(workspace_df)
    source_summary_df = build_group_summary(status_df, "source_id")
    modality_summary_df = build_group_summary(status_df, "modality")
    source_artifact_df = build_source_artifact_index(request)

    status_counts = status_df["acquisition_status"].value_counts().to_dict() if not status_df.empty else {}
    pending_count = int(sum(count for status, count in status_counts.items() if str(status).startswith("pending_acquisition")))

    paths = {
        "status_dashboard": Path(output_dir) / "public_dataset_acquisition_status_dashboard.tsv",
        "status_by_source": Path(output_dir) / "public_dataset_acquisition_status_by_source.tsv",
        "status_by_modality": Path(output_dir) / "public_dataset_acquisition_status_by_modality.tsv",
        "source_artifact_index": Path(output_dir) / "public_dataset_acquisition_status_source_artifact_index.tsv",
        "status_summary": Path(output_dir) / "public_dataset_acquisition_status_summary.yaml",
        "status_report": Path(output_dir) / "public_dataset_acquisition_status_report.html",
    }

    status_df.to_csv(paths["status_dashboard"], sep="\t", index=False)
    source_summary_df.to_csv(paths["status_by_source"], sep="\t", index=False)
    modality_summary_df.to_csv(paths["status_by_modality"], sep="\t", index=False)
    source_artifact_df.to_csv(paths["source_artifact_index"], sep="\t", index=False)

    summary = {
        "request_id": str(request.get("request_id", "")),
        "atlas_name": str(request.get("atlas_name", "")),
        "upstream_workspace_request_id": str(workspace_summary.get("request_id", "")),
        "upstream_workspace_output_dir": str(workspace_summary.get("output_dir", "")),
        "dataset_count": int(status_df.shape[0]),
        "pending_acquisition_count": pending_count,
        "local_file_present_count": int(status_counts.get("local_file_present", 0)),
        "workspace_incomplete_count": int(status_counts.get("pending_acquisition_workspace_incomplete", 0)),
        "output_dir": str(output_dir),
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {
            "stage": "public_dataset_acquisition_status_dashboard",
            "purpose": "summarize acquisition status, pending work, source/modality rollups, and workspace links",
        },
    }

    write_yaml(paths["status_summary"], summary)
    paths["status_report"].write_text(
        build_html_report(request, status_df, source_summary_df, modality_summary_df, source_artifact_df, summary),
        encoding="utf-8",
    )
    return summary, status_df, source_summary_df, modality_summary_df, source_artifact_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Build public dataset acquisition status dashboard.")
    parser.add_argument("--request", type=Path, default=DEFAULT_STATUS_DASHBOARD_REQUEST)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        summary, status_df, source_summary_df, modality_summary_df, source_artifact_df, paths = build_public_dataset_acquisition_status_dashboard(
            request_path=args.request,
            output_dir=args.output_dir,
        )
    except Exception as exc:
        print(f"ERROR: Public dataset acquisition status dashboard build failed: {exc}", file=sys.stderr)
        return 1

    print("Public dataset acquisition status dashboard complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Datasets: {summary['dataset_count']}")
    print(f"Pending acquisition: {summary['pending_acquisition_count']}")
    print(f"Local files present: {summary['local_file_present_count']}")
    print(f"Workspace incomplete: {summary['workspace_incomplete_count']}")
    print(f"Report: {paths['status_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

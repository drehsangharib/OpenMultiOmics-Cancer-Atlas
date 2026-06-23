#!/usr/bin/env python3

import argparse
import html
import sys
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_READINESS_REQUEST = Path("configs/public_data_sources/public_dataset_replacement_readiness_request.yaml")


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
        text = str(value).strip().lower()
        if text in {"true", "yes"}:
            return 1
        if text in {"false", "no"}:
            return 0
        return default


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


def require_columns(df, required_columns, table_name):
    missing = set(required_columns) - set(df.columns)
    if missing:
        raise ValueError(f"{table_name} missing columns: " + ", ".join(sorted(missing)))


def normalize_replacement_manifest_inventory(inventory_df):
    required = {"dataset_id", "replacement_manifest_stub", "replacement_manifest_stub_exists"}
    require_columns(inventory_df, required, "replacement_manifest_inventory")
    keep = ["dataset_id", "replacement_manifest_stub", "replacement_manifest_stub_exists"]
    optional = ["atlas_hint", "modality", "source_manifest", "source_manifest_exists"]
    for column in optional:
        if column in inventory_df.columns:
            keep.append(column)
    return inventory_df.loc[:, keep].copy()


def make_readiness_message(row):
    status = safe_str(row.get("readiness_status", ""))
    if status == "ready_for_replacement_validation":
        return "Real replacement file and replacement manifest stub are present; candidate is ready for downstream validation."
    if status == "not_ready_missing_real_file":
        return f"Real replacement file is missing. Save the public dataset export to: {safe_str(row.get('local_replacement_path', ''))}"
    if status == "blocked_missing_manifest_stub":
        return "Replacement manifest stub is missing or not accessible; rerun the a22 replacement workflow builder."
    if status == "blocked_missing_required_metadata":
        return "Required metadata is missing from the replacement plan; inspect dataset registry and a22 workflow inputs."
    return "Readiness status could not be determined."


def classify_readiness(row):
    required_metadata_fields = ["dataset_id", "atlas_hint", "modality", "source_id", "accession_or_project_id", "local_replacement_path"]
    missing_metadata = [field for field in required_metadata_fields if safe_str(row.get(field, "")).strip() == ""]
    if missing_metadata:
        return "blocked_missing_required_metadata"
    replacement_manifest_stub = safe_str(row.get("replacement_manifest_stub", "")).strip()
    replacement_manifest_stub_exists = safe_int(row.get("replacement_manifest_stub_exists", 0))
    if replacement_manifest_stub == "" or replacement_manifest_stub_exists != 1 or not Path(replacement_manifest_stub).exists():
        return "blocked_missing_manifest_stub"
    local_replacement_path = safe_str(row.get("local_replacement_path", "")).strip()
    replacement_file_exists = safe_int(row.get("replacement_file_exists", 0))
    if local_replacement_path == "" or replacement_file_exists != 1 or not Path(local_replacement_path).exists():
        return "not_ready_missing_real_file"
    return "ready_for_replacement_validation"


def build_readiness_table(replacement_plan_df, replacement_manifest_inventory_df):
    required_plan_cols = {
        "dataset_id", "display_name", "source_id", "accession_or_project_id", "atlas_hint", "modality",
        "expected_file_type", "replacement_priority", "local_file_path", "placeholder_exists",
        "local_replacement_path", "replacement_file_exists", "materialized_manifest_stub", "replacement_status",
        "recommended_action", "notes",
    }
    require_columns(replacement_plan_df, required_plan_cols, "replacement_plan")
    manifest_df = normalize_replacement_manifest_inventory(replacement_manifest_inventory_df)
    merged = replacement_plan_df.merge(manifest_df, on="dataset_id", how="left", suffixes=("", "_replacement_manifest"))
    if "replacement_manifest_stub" not in merged.columns:
        merged["replacement_manifest_stub"] = ""
    if "replacement_manifest_stub_exists" not in merged.columns:
        merged["replacement_manifest_stub_exists"] = 0
    merged["placeholder_exists_current"] = merged["local_file_path"].apply(lambda p: int(Path(safe_str(p)).exists()) if safe_str(p).strip() else 0)
    merged["replacement_file_exists_current"] = merged["local_replacement_path"].apply(lambda p: int(Path(safe_str(p)).exists()) if safe_str(p).strip() else 0)
    merged["replacement_manifest_stub_exists_current"] = merged["replacement_manifest_stub"].apply(lambda p: int(Path(safe_str(p)).exists()) if safe_str(p).strip() else 0)
    merged["readiness_status"] = merged.apply(classify_readiness, axis=1)
    merged["readiness_message"] = merged.apply(make_readiness_message, axis=1)
    keep = [
        "dataset_id", "display_name", "source_id", "accession_or_project_id", "atlas_hint", "modality",
        "expected_file_type", "replacement_priority", "local_file_path", "placeholder_exists", "placeholder_exists_current",
        "local_replacement_path", "replacement_file_exists", "replacement_file_exists_current", "materialized_manifest_stub",
        "replacement_manifest_stub", "replacement_manifest_stub_exists", "replacement_manifest_stub_exists_current",
        "replacement_status", "readiness_status", "readiness_message", "recommended_action", "notes",
    ]
    return merged.loc[:, keep].copy()


def build_html_report(request, readiness_df, source_artifact_df, summary):
    title = "Public Dataset Replacement Readiness Report"
    return "\n".join([
        "<!DOCTYPE html>", "<html>", "<head>", "<meta charset='utf-8'>",
        f"<title>{escape_html(title)}</title>", "</head>", "<body>", f"<h1>{escape_html(title)}</h1>",
        "<p>This report validates whether a22 public dataset replacement candidates are ready for real-file replacement validation.</p>",
        f"<p><strong>Request:</strong> {escape_html(request.get('request_id', ''))}</p>",
        f"<p><strong>Atlas:</strong> {escape_html(request.get('atlas_name', ''))}</p>",
        f"<p><strong>Replacement candidates:</strong> {summary.get('replacement_candidate_count', 0)}</p>",
        f"<p><strong>Ready for replacement validation:</strong> {summary.get('ready_for_replacement_validation_count', 0)}</p>",
        f"<p><strong>Not ready — missing real file:</strong> {summary.get('not_ready_missing_real_file_count', 0)}</p>",
        f"<p><strong>Blocked — missing manifest stub:</strong> {summary.get('blocked_missing_manifest_stub_count', 0)}</p>",
        f"<p><strong>Blocked — missing metadata:</strong> {summary.get('blocked_missing_required_metadata_count', 0)}</p>",
        "<h2>Readiness table</h2>", dataframe_to_html_table(readiness_df),
        "<h2>Source artifacts</h2>", dataframe_to_html_table(source_artifact_df),
        "<h2>Next step</h2>",
        "<p>Download or export each missing public dataset file to its planned local replacement path, rerun this validator, then proceed only when candidates reach ready_for_replacement_validation.</p>",
        "</body>", "</html>",
    ])


def build_source_artifact_index(request):
    inputs = request.get("inputs", {}) or {}
    rows = []
    for label in ["replacement_plan", "replacement_manifest_inventory", "replacement_summary"]:
        path = safe_str(inputs.get(label, ""))
        rows.append({"artifact_label": label, "path": path, "exists": int(Path(path).exists()) if path else 0})
    return pd.DataFrame(rows)


def validate_public_dataset_replacement_readiness(request_path=DEFAULT_READINESS_REQUEST, output_dir=None):
    request = load_yaml_mapping(request_path)
    inputs = request.get("inputs", {}) or {}
    replacement_plan_path = inputs.get("replacement_plan")
    replacement_manifest_inventory_path = inputs.get("replacement_manifest_inventory")
    replacement_summary_path = inputs.get("replacement_summary")
    if not replacement_plan_path:
        raise ValueError("Readiness request missing inputs.replacement_plan")
    if not replacement_manifest_inventory_path:
        raise ValueError("Readiness request missing inputs.replacement_manifest_inventory")
    if not replacement_summary_path:
        raise ValueError("Readiness request missing inputs.replacement_summary")
    replacement_plan_df = read_table(replacement_plan_path)
    replacement_manifest_inventory_df = read_table(replacement_manifest_inventory_path)
    replacement_summary = load_yaml_mapping(replacement_summary_path)
    expected_outputs = request.get("expected_outputs", {}) or {}
    output_dir = ensure_dir(output_dir or expected_outputs.get("readiness_dir", Path("outputs/public_data_acquisition") / request.get("atlas_name", "public_data_pilot") / "dataset_replacement_readiness"))
    readiness_df = build_readiness_table(replacement_plan_df, replacement_manifest_inventory_df)
    source_artifact_df = build_source_artifact_index(request)
    status_counts = readiness_df["readiness_status"].value_counts().to_dict() if not readiness_df.empty else {}
    paths = {
        "readiness_table": Path(output_dir) / "public_dataset_replacement_readiness_table.tsv",
        "source_artifact_index": Path(output_dir) / "public_dataset_replacement_readiness_source_artifact_index.tsv",
        "readiness_summary": Path(output_dir) / "public_dataset_replacement_readiness_summary.yaml",
        "readiness_report": Path(output_dir) / "public_dataset_replacement_readiness_report.html",
    }
    readiness_df.to_csv(paths["readiness_table"], sep="\t", index=False)
    source_artifact_df.to_csv(paths["source_artifact_index"], sep="\t", index=False)
    summary = {
        "request_id": str(request.get("request_id", "")),
        "atlas_name": str(request.get("atlas_name", "")),
        "upstream_replacement_request_id": str(replacement_summary.get("request_id", "")),
        "upstream_replacement_workflow_dir": str(replacement_summary.get("output_dir", "")),
        "replacement_candidate_count": int(readiness_df.shape[0]),
        "ready_for_replacement_validation_count": int(status_counts.get("ready_for_replacement_validation", 0)),
        "not_ready_missing_real_file_count": int(status_counts.get("not_ready_missing_real_file", 0)),
        "blocked_missing_manifest_stub_count": int(status_counts.get("blocked_missing_manifest_stub", 0)),
        "blocked_missing_required_metadata_count": int(status_counts.get("blocked_missing_required_metadata", 0)),
        "output_dir": str(output_dir),
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {
            "stage": "public_dataset_replacement_readiness_validation",
            "purpose": "validate candidate readiness before replacing placeholder matrices with real public dataset files",
        },
    }
    write_yaml(paths["readiness_summary"], summary)
    paths["readiness_report"].write_text(build_html_report(request, readiness_df, source_artifact_df, summary), encoding="utf-8")
    return summary, readiness_df, source_artifact_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Validate public dataset replacement readiness.")
    parser.add_argument("--request", type=Path, default=DEFAULT_READINESS_REQUEST)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        summary, readiness_df, source_artifact_df, paths = validate_public_dataset_replacement_readiness(request_path=args.request, output_dir=args.output_dir)
    except Exception as exc:
        print(f"ERROR: Public dataset replacement readiness validation failed: {exc}", file=sys.stderr)
        return 1
    print("Public dataset replacement readiness validation complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Replacement candidates: {summary['replacement_candidate_count']}")
    print(f"Ready for replacement validation: {summary['ready_for_replacement_validation_count']}")
    print(f"Not ready missing real file: {summary['not_ready_missing_real_file_count']}")
    print(f"Blocked missing manifest stub: {summary['blocked_missing_manifest_stub_count']}")
    print(f"Blocked missing required metadata: {summary['blocked_missing_required_metadata_count']}")
    print(f"Report: {paths['readiness_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

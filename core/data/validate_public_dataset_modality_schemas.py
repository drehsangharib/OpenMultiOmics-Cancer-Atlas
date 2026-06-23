#!/usr/bin/env python3

import argparse
import html
import sys
from pathlib import Path

import pandas as pd
import yaml

DEFAULT_SCHEMA_REQUEST = Path("configs/public_data_sources/public_dataset_modality_schema_validation_request.yaml")


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


def dataframe_to_html_table(df, max_rows=300):
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


def allowed_extension(path, extensions):
    name = Path(path).name.lower()
    return any(name.endswith(str(ext).lower()) for ext in extensions)


def infer_separator(path):
    name = Path(path).name.lower()
    if name.endswith(".csv") or name.endswith(".csv.gz"):
        return ","
    return "\t"


def choose_candidate_file(row):
    target = safe_str(row.get("target_local_path", ""))
    if target and Path(target).exists():
        return target
    candidates = [x for x in safe_str(row.get("candidate_files", "")).split(";") if x]
    return candidates[0] if candidates else ""


def numeric_fraction(df):
    if df.empty or df.shape[1] <= 1:
        return 0.0
    data = df.iloc[:, 1:]
    total = data.shape[0] * data.shape[1]
    if total == 0:
        return 0.0
    numeric = data.apply(pd.to_numeric, errors="coerce").notna().sum().sum()
    return float(numeric) / float(total)


def modality_hints(policy, modality):
    hints = (policy.get("modality_id_hints", {}) or {}).get(safe_str(modality), [])
    if not hints:
        hints = ["sample", "feature", "id"]
    return [safe_str(x).lower() for x in hints]


def validate_file_schema(row, policy):
    path = choose_candidate_file(row)
    modality = safe_str(row.get("modality", ""))
    extensions = policy.get("allowed_extensions", [".tsv", ".csv", ".txt", ".tsv.gz", ".csv.gz"])
    min_rows = safe_int(policy.get("minimum_rows", 1), 1)
    min_columns = safe_int(policy.get("minimum_columns", 2), 2)
    threshold = float(policy.get("numeric_fraction_threshold", 0.5))
    result = {
        "schema_candidate_file": path,
        "schema_file_exists": 0,
        "schema_file_readable": 0,
        "schema_extension_allowed": 0,
        "schema_row_count": 0,
        "schema_column_count": 0,
        "schema_numeric_fraction": 0.0,
        "schema_first_column_id_like": 0,
        "schema_validation_status": "skipped_awaiting_file",
        "schema_validation_message": "No target or candidate real file is available for modality schema validation.",
    }
    if not path:
        return result
    file_path = Path(path)
    if not file_path.exists():
        result["schema_validation_status"] = "missing_candidate_file"
        result["schema_validation_message"] = "Candidate file path was recorded but does not exist."
        return result
    result["schema_file_exists"] = 1
    result["schema_extension_allowed"] = int(allowed_extension(file_path, extensions))
    if result["schema_extension_allowed"] != 1:
        result["schema_validation_status"] = "failed_disallowed_extension"
        result["schema_validation_message"] = f"File extension is not in allowed list: {file_path.name}"
        return result
    try:
        df = pd.read_csv(file_path, sep=infer_separator(file_path))
    except Exception as exc:
        result["schema_validation_status"] = "failed_unreadable_table"
        result["schema_validation_message"] = f"Could not read table: {exc}"
        return result
    result["schema_file_readable"] = 1
    result["schema_row_count"] = int(df.shape[0])
    result["schema_column_count"] = int(df.shape[1])
    result["schema_numeric_fraction"] = numeric_fraction(df)
    first_col = safe_str(df.columns[0]).lower() if len(df.columns) else ""
    result["schema_first_column_id_like"] = int(any(hint in first_col for hint in modality_hints(policy, modality)))
    if df.shape[0] < min_rows:
        result["schema_validation_status"] = "failed_too_few_rows"
        result["schema_validation_message"] = f"Table has {df.shape[0]} rows; minimum required is {min_rows}."
        return result
    if df.shape[1] < min_columns:
        result["schema_validation_status"] = "failed_too_few_columns"
        result["schema_validation_message"] = f"Table has {df.shape[1]} columns; minimum required is {min_columns}."
        return result
    if result["schema_numeric_fraction"] < threshold:
        result["schema_validation_status"] = "failed_low_numeric_fraction"
        result["schema_validation_message"] = f"Numeric value fraction is {result['schema_numeric_fraction']:.3f}; required threshold is {threshold:.3f}."
        return result
    if result["schema_first_column_id_like"] != 1:
        result["schema_validation_status"] = "warning_first_column_not_modality_id_like"
        result["schema_validation_message"] = "Table is readable but first column is not clearly compatible with modality-specific ID hints."
        return result
    result["schema_validation_status"] = "validated_modality_schema"
    result["schema_validation_message"] = "File passed modality-aware structural schema validation."
    return result


def build_schema_validation_table(intake_df, policy):
    require_columns(
        intake_df,
        {
            "dataset_id", "source_id", "accession_or_project_id", "atlas_hint", "modality", "expected_file_type",
            "target_local_path", "intake_status", "candidate_file_count", "candidate_files",
        },
        "real_file_intake_inventory",
    )
    rows = []
    for _, row in intake_df.iterrows():
        validation = validate_file_schema(row, policy)
        rows.append({
            "dataset_id": safe_str(row.get("dataset_id", "")),
            "source_id": safe_str(row.get("source_id", "")),
            "accession_or_project_id": safe_str(row.get("accession_or_project_id", "")),
            "atlas_hint": safe_str(row.get("atlas_hint", "")),
            "modality": safe_str(row.get("modality", "")),
            "expected_file_type": safe_str(row.get("expected_file_type", "")),
            "intake_status": safe_str(row.get("intake_status", "")),
            "target_local_path": safe_str(row.get("target_local_path", "")),
            "candidate_file_count": safe_int(row.get("candidate_file_count", 0)),
            **validation,
        })
    return pd.DataFrame(rows)


def build_modality_summary(validation_df):
    if validation_df.empty:
        return pd.DataFrame(columns=["modality", "dataset_count", "validated_count", "awaiting_file_count", "failed_or_warning_count"])
    rows = []
    for modality, group in validation_df.groupby("modality", dropna=False):
        statuses = group["schema_validation_status"].astype(str)
        rows.append({
            "modality": safe_str(modality),
            "dataset_count": int(group.shape[0]),
            "validated_count": int((statuses == "validated_modality_schema").sum()),
            "awaiting_file_count": int((statuses == "skipped_awaiting_file").sum()),
            "failed_or_warning_count": int((statuses.str.startswith("failed_") | statuses.str.startswith("warning_")).sum()),
        })
    return pd.DataFrame(rows).sort_values("modality").reset_index(drop=True)


def build_source_artifact_index(request):
    inputs = request.get("inputs", {}) or {}
    rows = []
    for label in ["real_file_intake_inventory", "real_file_intake_summary", "real_file_intake_source_artifact_index"]:
        path = safe_str(inputs.get(label, ""))
        rows.append({"artifact_label": label, "path": path, "exists": int(Path(path).exists()) if path else 0})
    return pd.DataFrame(rows)


def build_html_report(request, validation_df, modality_summary_df, source_artifact_df, summary):
    title = "Public Dataset Modality Schema Validation Report"
    return "\n".join([
        "<!DOCTYPE html>", "<html>", "<head>", "<meta charset='utf-8'>", f"<title>{escape_html(title)}</title>", "</head>", "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This report validates real public dataset files with modality-aware structural schema rules.</p>",
        f"<p><strong>Request:</strong> {escape_html(request.get('request_id', ''))}</p>",
        f"<p><strong>Atlas:</strong> {escape_html(request.get('atlas_name', ''))}</p>",
        f"<p><strong>Dataset count:</strong> {summary.get('dataset_count', 0)}</p>",
        f"<p><strong>Validated schemas:</strong> {summary.get('validated_schema_count', 0)}</p>",
        f"<p><strong>Awaiting files:</strong> {summary.get('awaiting_file_count', 0)}</p>",
        f"<p><strong>Failed or warning:</strong> {summary.get('failed_or_warning_count', 0)}</p>",
        "<h2>Schema validation table</h2>", dataframe_to_html_table(validation_df),
        "<h2>Modality summary</h2>", dataframe_to_html_table(modality_summary_df),
        "<h2>Source artifacts</h2>", dataframe_to_html_table(source_artifact_df),
        "</body>", "</html>",
    ])


def validate_public_dataset_modality_schemas(request_path=DEFAULT_SCHEMA_REQUEST, output_dir=None):
    request = load_yaml_mapping(request_path)
    inputs = request.get("inputs", {}) or {}
    policy = request.get("schema_policy", {}) or {}
    inventory_path = inputs.get("real_file_intake_inventory")
    summary_path = inputs.get("real_file_intake_summary")
    if not inventory_path:
        raise ValueError("Schema validation request missing inputs.real_file_intake_inventory")
    if not summary_path:
        raise ValueError("Schema validation request missing inputs.real_file_intake_summary")
    intake_df = read_table(inventory_path)
    intake_summary = load_yaml_mapping(summary_path)
    expected_outputs = request.get("expected_outputs", {}) or {}
    output_dir = ensure_dir(output_dir or expected_outputs.get("modality_schema_validation_dir", Path("outputs/public_data_acquisition") / request.get("atlas_name", "public_data_pilot") / "modality_schema_validation"))
    validation_df = build_schema_validation_table(intake_df, policy)
    modality_summary_df = build_modality_summary(validation_df)
    source_artifact_df = build_source_artifact_index(request)
    statuses = validation_df["schema_validation_status"].astype(str) if not validation_df.empty else pd.Series([], dtype=str)
    paths = {
        "schema_validation_table": Path(output_dir) / "public_dataset_modality_schema_validation_table.tsv",
        "modality_summary": Path(output_dir) / "public_dataset_modality_schema_validation_by_modality.tsv",
        "source_artifact_index": Path(output_dir) / "public_dataset_modality_schema_validation_source_artifact_index.tsv",
        "schema_validation_summary": Path(output_dir) / "public_dataset_modality_schema_validation_summary.yaml",
        "schema_validation_report": Path(output_dir) / "public_dataset_modality_schema_validation_report.html",
    }
    validation_df.to_csv(paths["schema_validation_table"], sep="\t", index=False)
    modality_summary_df.to_csv(paths["modality_summary"], sep="\t", index=False)
    source_artifact_df.to_csv(paths["source_artifact_index"], sep="\t", index=False)
    summary = {
        "request_id": str(request.get("request_id", "")),
        "atlas_name": str(request.get("atlas_name", "")),
        "upstream_intake_request_id": str(intake_summary.get("request_id", "")),
        "upstream_intake_output_dir": str(intake_summary.get("output_dir", "")),
        "dataset_count": int(validation_df.shape[0]),
        "validated_schema_count": int((statuses == "validated_modality_schema").sum()),
        "awaiting_file_count": int((statuses == "skipped_awaiting_file").sum()),
        "failed_or_warning_count": int((statuses.str.startswith("failed_") | statuses.str.startswith("warning_")).sum()) if not validation_df.empty else 0,
        "modalities_covered": int(validation_df["modality"].nunique()) if not validation_df.empty else 0,
        "output_dir": str(output_dir),
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {"stage": "public_dataset_modality_schema_validation", "purpose": "validate real public files with modality-specific structural schema rules"},
    }
    write_yaml(paths["schema_validation_summary"], summary)
    paths["schema_validation_report"].write_text(build_html_report(request, validation_df, modality_summary_df, source_artifact_df, summary), encoding="utf-8")
    return summary, validation_df, modality_summary_df, source_artifact_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Validate public dataset files with modality-specific schema rules.")
    parser.add_argument("--request", type=Path, default=DEFAULT_SCHEMA_REQUEST)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        summary, validation_df, modality_summary_df, source_artifact_df, paths = validate_public_dataset_modality_schemas(request_path=args.request, output_dir=args.output_dir)
    except Exception as exc:
        print(f"ERROR: Public dataset modality schema validation failed: {exc}", file=sys.stderr)
        return 1
    print("Public dataset modality schema validation complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Datasets: {summary['dataset_count']}")
    print(f"Validated schemas: {summary['validated_schema_count']}")
    print(f"Awaiting files: {summary['awaiting_file_count']}")
    print(f"Failed or warning: {summary['failed_or_warning_count']}")
    print(f"Report: {paths['schema_validation_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

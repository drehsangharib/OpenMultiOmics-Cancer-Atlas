#!/usr/bin/env python3

import argparse
import html
import sys
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_FILE_VALIDATION_REQUEST = Path("configs/public_data_sources/public_dataset_replacement_file_validation_request.yaml")
READY_EXECUTION_STATUS = "ready_execution_job"


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
    if value is None:
        return ""
    return html.escape(str(value))


def dataframe_to_html_table(df, max_rows=200):
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


def infer_separator(path):
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        return ","
    return "\t"


def validate_replacement_file(path, expected_file_type, policy):
    file_path = Path(safe_str(path))
    allowed_extensions = set(policy.get("allowed_extensions", [".tsv", ".csv", ".txt"]))
    min_rows = safe_int(policy.get("minimum_rows", 1), 1)
    min_columns = safe_int(policy.get("minimum_columns", 2), 2)

    result = {
        "real_file_exists": 0,
        "real_file_readable": 0,
        "real_file_extension_allowed": 0,
        "real_file_row_count": 0,
        "real_file_column_count": 0,
        "real_file_has_id_like_first_column": 0,
        "file_validation_status": "missing_real_file",
        "file_validation_message": "Real replacement file is missing.",
    }

    if not safe_str(path).strip() or not file_path.exists():
        return result

    result["real_file_exists"] = 1
    result["real_file_extension_allowed"] = int(file_path.suffix.lower() in allowed_extensions)

    if result["real_file_extension_allowed"] != 1:
        result["file_validation_status"] = "failed_disallowed_extension"
        result["file_validation_message"] = f"File extension {file_path.suffix} is not allowed."
        return result

    try:
        df = pd.read_csv(file_path, sep=infer_separator(file_path))
    except Exception as exc:
        result["file_validation_status"] = "failed_unreadable_table"
        result["file_validation_message"] = f"Could not read table: {exc}"
        return result

    result["real_file_readable"] = 1
    result["real_file_row_count"] = int(df.shape[0])
    result["real_file_column_count"] = int(df.shape[1])
    first_col = safe_str(df.columns[0]).lower() if len(df.columns) else ""
    id_tokens = ["id", "sample", "gene", "protein", "metabolite", "feature"]
    result["real_file_has_id_like_first_column"] = int(any(token in first_col for token in id_tokens))

    if df.shape[0] < min_rows:
        result["file_validation_status"] = "failed_too_few_rows"
        result["file_validation_message"] = f"Table has {df.shape[0]} rows; minimum required is {min_rows}."
        return result
    if df.shape[1] < min_columns:
        result["file_validation_status"] = "failed_too_few_columns"
        result["file_validation_message"] = f"Table has {df.shape[1]} columns; minimum required is {min_columns}."
        return result
    if result["real_file_has_id_like_first_column"] != 1:
        result["file_validation_status"] = "warning_missing_id_like_first_column"
        result["file_validation_message"] = "Table is readable but first column is not clearly ID-like."
        return result

    result["file_validation_status"] = "validated_real_file"
    result["file_validation_message"] = "Real replacement file is readable and passes basic structural validation."
    return result


def build_file_validation_table(execution_jobs_df, policy):
    required = {
        "execution_job_id",
        "dataset_id",
        "display_name",
        "source_id",
        "accession_or_project_id",
        "atlas_hint",
        "modality",
        "expected_file_type",
        "replacement_priority",
        "execution_status",
        "local_replacement_path",
        "replacement_manifest_stub",
    }
    require_columns(execution_jobs_df, required, "execution_jobs")

    rows = []
    for _, row in execution_jobs_df.sort_values("replacement_priority").iterrows():
        execution_status = safe_str(row.get("execution_status", ""))
        local_replacement_path = safe_str(row.get("local_replacement_path", ""))
        expected_file_type = safe_str(row.get("expected_file_type", ""))

        validation = validate_replacement_file(local_replacement_path, expected_file_type, policy)
        if execution_status != READY_EXECUTION_STATUS:
            validation["file_validation_status"] = "skipped_not_ready"
            validation["file_validation_message"] = safe_str(row.get("skip_reason", "")) or "Execution job is not ready; file validation skipped."

        rows.append(
            {
                "execution_job_id": safe_str(row.get("execution_job_id", "")),
                "dataset_id": safe_str(row.get("dataset_id", "")),
                "display_name": safe_str(row.get("display_name", "")),
                "source_id": safe_str(row.get("source_id", "")),
                "accession_or_project_id": safe_str(row.get("accession_or_project_id", "")),
                "atlas_hint": safe_str(row.get("atlas_hint", "")),
                "modality": safe_str(row.get("modality", "")),
                "expected_file_type": expected_file_type,
                "replacement_priority": safe_int(row.get("replacement_priority", 999), 999),
                "execution_status": execution_status,
                "local_replacement_path": local_replacement_path,
                "replacement_manifest_stub": safe_str(row.get("replacement_manifest_stub", "")),
                **validation,
            }
        )
    return pd.DataFrame(rows)


def build_source_artifact_index(request):
    inputs = request.get("inputs", {}) or {}
    rows = []
    for label in ["execution_jobs", "execution_summary", "execution_source_artifact_index"]:
        path = safe_str(inputs.get(label, ""))
        rows.append({"artifact_label": label, "path": path, "exists": int(Path(path).exists()) if path else 0})
    return pd.DataFrame(rows)


def build_html_report(request, validation_df, source_artifact_df, summary):
    title = "Public Dataset Replacement File Validation Report"
    parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        f"<title>{escape_html(title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This report validates local real public dataset replacement files before downstream replacement execution.</p>",
        f"<p><strong>Request:</strong> {escape_html(request.get('request_id', ''))}</p>",
        f"<p><strong>Atlas:</strong> {escape_html(request.get('atlas_name', ''))}</p>",
        f"<p><strong>Replacement candidates:</strong> {summary.get('replacement_candidate_count', 0)}</p>",
        f"<p><strong>Ready execution jobs:</strong> {summary.get('ready_execution_job_count', 0)}</p>",
        f"<p><strong>Validated real files:</strong> {summary.get('validated_real_file_count', 0)}</p>",
        f"<p><strong>Skipped not ready:</strong> {summary.get('skipped_not_ready_count', 0)}</p>",
        f"<p><strong>Missing real files:</strong> {summary.get('missing_real_file_count', 0)}</p>",
        f"<p><strong>Failed validation:</strong> {summary.get('failed_validation_count', 0)}</p>",
        "<h2>File validation table</h2>",
        dataframe_to_html_table(validation_df),
        "<h2>Source artifacts</h2>",
        dataframe_to_html_table(source_artifact_df),
        "<h2>Next step</h2>",
        "<p>Add real public replacement files to the planned local paths, rerun a23 readiness validation, rerun a24 execution scaffold, then rerun this validator.</p>",
        "</body>",
        "</html>",
    ]
    return "\n".join(parts)


def validate_public_dataset_replacement_files(request_path=DEFAULT_FILE_VALIDATION_REQUEST, output_dir=None):
    request = load_yaml_mapping(request_path)
    inputs = request.get("inputs", {}) or {}
    policy = request.get("validation_policy", {}) or {}

    execution_jobs_path = inputs.get("execution_jobs")
    execution_summary_path = inputs.get("execution_summary")
    if not execution_jobs_path:
        raise ValueError("File validation request missing inputs.execution_jobs")
    if not execution_summary_path:
        raise ValueError("File validation request missing inputs.execution_summary")

    execution_jobs_df = read_table(execution_jobs_path)
    execution_summary = load_yaml_mapping(execution_summary_path)

    expected_outputs = request.get("expected_outputs", {}) or {}
    output_dir = ensure_dir(
        output_dir
        or expected_outputs.get(
            "file_validation_dir",
            Path("outputs/public_data_acquisition")
            / request.get("atlas_name", "public_data_pilot")
            / "dataset_replacement_file_validation",
        )
    )

    validation_df = build_file_validation_table(execution_jobs_df, policy)
    source_artifact_df = build_source_artifact_index(request)
    status_counts = validation_df["file_validation_status"].value_counts().to_dict() if not validation_df.empty else {}

    failed_validation_count = int(
        sum(
            count
            for status, count in status_counts.items()
            if status.startswith("failed_") or status.startswith("warning_")
        )
    )

    paths = {
        "file_validation_table": Path(output_dir) / "public_dataset_replacement_file_validation_table.tsv",
        "source_artifact_index": Path(output_dir) / "public_dataset_replacement_file_validation_source_artifact_index.tsv",
        "file_validation_summary": Path(output_dir) / "public_dataset_replacement_file_validation_summary.yaml",
        "file_validation_report": Path(output_dir) / "public_dataset_replacement_file_validation_report.html",
    }

    validation_df.to_csv(paths["file_validation_table"], sep="\t", index=False)
    source_artifact_df.to_csv(paths["source_artifact_index"], sep="\t", index=False)

    summary = {
        "request_id": str(request.get("request_id", "")),
        "atlas_name": str(request.get("atlas_name", "")),
        "upstream_execution_request_id": str(execution_summary.get("request_id", "")),
        "upstream_execution_output_dir": str(execution_summary.get("output_dir", "")),
        "replacement_candidate_count": int(validation_df.shape[0]),
        "ready_execution_job_count": int((validation_df["execution_status"] == READY_EXECUTION_STATUS).sum()) if not validation_df.empty else 0,
        "validated_real_file_count": int(status_counts.get("validated_real_file", 0)),
        "skipped_not_ready_count": int(status_counts.get("skipped_not_ready", 0)),
        "missing_real_file_count": int(status_counts.get("missing_real_file", 0)),
        "failed_validation_count": failed_validation_count,
        "output_dir": str(output_dir),
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {
            "stage": "public_dataset_replacement_file_validation",
            "purpose": "validate real local replacement files before modality-specific replacement execution",
        },
    }

    write_yaml(paths["file_validation_summary"], summary)
    paths["file_validation_report"].write_text(
        build_html_report(request, validation_df, source_artifact_df, summary),
        encoding="utf-8",
    )
    return summary, validation_df, source_artifact_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Validate local public dataset replacement files.")
    parser.add_argument("--request", type=Path, default=DEFAULT_FILE_VALIDATION_REQUEST)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        summary, validation_df, source_artifact_df, paths = validate_public_dataset_replacement_files(
            request_path=args.request,
            output_dir=args.output_dir,
        )
    except Exception as exc:
        print(f"ERROR: Public dataset replacement file validation failed: {exc}", file=sys.stderr)
        return 1

    print("Public dataset replacement file validation complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Replacement candidates: {summary['replacement_candidate_count']}")
    print(f"Ready execution jobs: {summary['ready_execution_job_count']}")
    print(f"Validated real files: {summary['validated_real_file_count']}")
    print(f"Skipped not ready: {summary['skipped_not_ready_count']}")
    print(f"Missing real files: {summary['missing_real_file_count']}")
    print(f"Failed validation: {summary['failed_validation_count']}")
    print(f"Report: {paths['file_validation_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

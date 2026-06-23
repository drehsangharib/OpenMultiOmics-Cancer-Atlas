#!/usr/bin/env python3

import argparse
import html
import sys
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_EXECUTION_REQUEST = Path("configs/public_data_sources/public_dataset_replacement_execution_request.yaml")
READY_STATUS = "ready_for_replacement_validation"


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


def slugify_parts(*parts):
    cleaned = []
    for part in parts:
        text = safe_str(part).strip().lower()
        text = "".join(ch if ch.isalnum() else "_" for ch in text)
        text = "_".join(token for token in text.split("_") if token)
        if text:
            cleaned.append(text)
    return "_".join(cleaned) or "replacement_candidate"


def make_skip_reason(row):
    status = safe_str(row.get("readiness_status", ""))
    if status == READY_STATUS:
        return ""
    message = safe_str(row.get("readiness_message", ""))
    if message:
        return message
    if status:
        return f"Candidate readiness status is {status}."
    return "Candidate is not marked ready_for_replacement_validation."


def build_execution_jobs(readiness_df):
    required = {
        "dataset_id",
        "display_name",
        "source_id",
        "accession_or_project_id",
        "atlas_hint",
        "modality",
        "expected_file_type",
        "replacement_priority",
        "local_replacement_path",
        "replacement_manifest_stub",
        "readiness_status",
    }
    require_columns(readiness_df, required, "readiness_table")

    rows = []
    for _, row in readiness_df.sort_values("replacement_priority").iterrows():
        readiness_status = safe_str(row.get("readiness_status", ""))
        ready = readiness_status == READY_STATUS
        dataset_id = safe_str(row.get("dataset_id", ""))
        atlas_hint = safe_str(row.get("atlas_hint", ""))
        modality = safe_str(row.get("modality", ""))
        job_id = slugify_parts("execute", dataset_id, atlas_hint, modality)
        execution_status = "ready_execution_job" if ready else "skipped_not_ready"

        rows.append(
            {
                "execution_job_id": job_id,
                "dataset_id": dataset_id,
                "display_name": safe_str(row.get("display_name", "")),
                "source_id": safe_str(row.get("source_id", "")),
                "accession_or_project_id": safe_str(row.get("accession_or_project_id", "")),
                "atlas_hint": atlas_hint,
                "modality": modality,
                "expected_file_type": safe_str(row.get("expected_file_type", "")),
                "replacement_priority": safe_int(row.get("replacement_priority", 999), 999),
                "readiness_status": readiness_status,
                "execution_status": execution_status,
                "skip_reason": make_skip_reason(row),
                "local_replacement_path": safe_str(row.get("local_replacement_path", "")),
                "replacement_manifest_stub": safe_str(row.get("replacement_manifest_stub", "")),
                "materialized_manifest_stub": safe_str(row.get("materialized_manifest_stub", "")),
                "recommended_action": safe_str(row.get("recommended_action", "")),
                "notes": safe_str(row.get("notes", "")),
            }
        )
    return pd.DataFrame(rows)


def make_execution_job_manifests(execution_jobs_df, output_dir):
    manifest_dir = ensure_dir(Path(output_dir) / "execution_job_manifests")
    rows = []
    if execution_jobs_df.empty:
        return pd.DataFrame(columns=["execution_job_id", "dataset_id", "execution_job_manifest", "execution_job_manifest_exists"])

    ready_df = execution_jobs_df[execution_jobs_df["execution_status"] == "ready_execution_job"].copy()
    for _, job in ready_df.iterrows():
        job_id = safe_str(job["execution_job_id"])
        manifest_path = manifest_dir / f"{job_id}_execution_job.yaml"
        manifest = {
            "execution_job_id": job_id,
            "dataset_id": safe_str(job["dataset_id"]),
            "atlas_hint": safe_str(job["atlas_hint"]),
            "modality": safe_str(job["modality"]),
            "source_id": safe_str(job["source_id"]),
            "accession_or_project_id": safe_str(job["accession_or_project_id"]),
            "local_replacement_path": safe_str(job["local_replacement_path"]),
            "replacement_manifest_stub": safe_str(job["replacement_manifest_stub"]),
            "execution_status": safe_str(job["execution_status"]),
            "planned_actions": [
                "validate real replacement file exists and matches expected file type",
                "validate replacement manifest references the real replacement path",
                "handoff to future modality-specific replacement executor",
            ],
            "non_destructive_policy": {
                "do_not_modify_source_readiness_outputs": True,
                "do_not_overwrite_replacement_manifests": True,
                "do_not_copy_or_modify_real_data_files": True,
            },
            "agent_role": {
                "stage": "public_dataset_replacement_execution_job_manifest",
                "purpose": "describe a candidate replacement execution job after readiness validation passed",
            },
        }
        write_yaml(manifest_path, manifest)
        rows.append(
            {
                "execution_job_id": job_id,
                "dataset_id": safe_str(job["dataset_id"]),
                "execution_job_manifest": str(manifest_path),
                "execution_job_manifest_exists": int(manifest_path.exists()),
            }
        )
    return pd.DataFrame(rows)


def build_source_artifact_index(request):
    inputs = request.get("inputs", {}) or {}
    rows = []
    for label in ["readiness_table", "readiness_summary", "readiness_source_artifact_index"]:
        path = safe_str(inputs.get(label, ""))
        rows.append({"artifact_label": label, "path": path, "exists": int(Path(path).exists()) if path else 0})
    return pd.DataFrame(rows)


def build_html_report(request, execution_jobs_df, execution_manifest_df, source_artifact_df, summary):
    title = "Public Dataset Replacement Execution Scaffold Report"
    parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        f"<title>{escape_html(title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This report builds a non-destructive execution scaffold from public dataset replacement readiness outputs.</p>",
        f"<p><strong>Request:</strong> {escape_html(request.get('request_id', ''))}</p>",
        f"<p><strong>Atlas:</strong> {escape_html(request.get('atlas_name', ''))}</p>",
        f"<p><strong>Replacement candidates:</strong> {summary.get('replacement_candidate_count', 0)}</p>",
        f"<p><strong>Ready execution jobs:</strong> {summary.get('ready_execution_job_count', 0)}</p>",
        f"<p><strong>Skipped not ready:</strong> {summary.get('skipped_not_ready_count', 0)}</p>",
        f"<p><strong>Execution job manifests:</strong> {summary.get('execution_job_manifest_count', 0)}</p>",
        "<h2>Execution jobs</h2>",
        dataframe_to_html_table(execution_jobs_df),
        "<h2>Execution job manifests</h2>",
        dataframe_to_html_table(execution_manifest_df),
        "<h2>Source artifacts</h2>",
        dataframe_to_html_table(source_artifact_df),
        "<h2>Next step</h2>",
        "<p>Add real public replacement files, rerun readiness validation, then rerun this execution scaffold to generate ready execution job manifests.</p>",
        "</body>",
        "</html>",
    ]
    return "\n".join(parts)


def build_public_dataset_replacement_execution_scaffold(request_path=DEFAULT_EXECUTION_REQUEST, output_dir=None):
    request = load_yaml_mapping(request_path)
    inputs = request.get("inputs", {}) or {}

    readiness_table_path = inputs.get("readiness_table")
    readiness_summary_path = inputs.get("readiness_summary")
    if not readiness_table_path:
        raise ValueError("Execution request missing inputs.readiness_table")
    if not readiness_summary_path:
        raise ValueError("Execution request missing inputs.readiness_summary")

    readiness_df = read_table(readiness_table_path)
    readiness_summary = load_yaml_mapping(readiness_summary_path)

    expected_outputs = request.get("expected_outputs", {}) or {}
    output_dir = ensure_dir(
        output_dir
        or expected_outputs.get(
            "execution_scaffold_dir",
            Path("outputs/public_data_acquisition")
            / request.get("atlas_name", "public_data_pilot")
            / "dataset_replacement_execution_scaffold",
        )
    )

    execution_jobs_df = build_execution_jobs(readiness_df)
    execution_manifest_df = make_execution_job_manifests(execution_jobs_df, output_dir)
    source_artifact_df = build_source_artifact_index(request)

    status_counts = execution_jobs_df["execution_status"].value_counts().to_dict() if not execution_jobs_df.empty else {}

    paths = {
        "execution_jobs": Path(output_dir) / "public_dataset_replacement_execution_jobs.tsv",
        "execution_manifest_inventory": Path(output_dir) / "public_dataset_replacement_execution_manifest_inventory.tsv",
        "source_artifact_index": Path(output_dir) / "public_dataset_replacement_execution_source_artifact_index.tsv",
        "execution_summary": Path(output_dir) / "public_dataset_replacement_execution_summary.yaml",
        "execution_report": Path(output_dir) / "public_dataset_replacement_execution_report.html",
    }

    execution_jobs_df.to_csv(paths["execution_jobs"], sep="\t", index=False)
    execution_manifest_df.to_csv(paths["execution_manifest_inventory"], sep="\t", index=False)
    source_artifact_df.to_csv(paths["source_artifact_index"], sep="\t", index=False)

    summary = {
        "request_id": str(request.get("request_id", "")),
        "atlas_name": str(request.get("atlas_name", "")),
        "upstream_readiness_request_id": str(readiness_summary.get("request_id", "")),
        "upstream_readiness_output_dir": str(readiness_summary.get("output_dir", "")),
        "replacement_candidate_count": int(execution_jobs_df.shape[0]),
        "ready_execution_job_count": int(status_counts.get("ready_execution_job", 0)),
        "skipped_not_ready_count": int(status_counts.get("skipped_not_ready", 0)),
        "execution_job_manifest_count": int(execution_manifest_df["execution_job_manifest_exists"].sum()) if not execution_manifest_df.empty else 0,
        "output_dir": str(output_dir),
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {
            "stage": "public_dataset_replacement_execution_scaffold",
            "purpose": "prepare auditable non-destructive execution jobs from readiness-validated public dataset replacement candidates",
        },
    }

    write_yaml(paths["execution_summary"], summary)
    paths["execution_report"].write_text(
        build_html_report(request, execution_jobs_df, execution_manifest_df, source_artifact_df, summary),
        encoding="utf-8",
    )
    return summary, execution_jobs_df, execution_manifest_df, source_artifact_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Build a public dataset replacement execution scaffold.")
    parser.add_argument("--request", type=Path, default=DEFAULT_EXECUTION_REQUEST)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        summary, execution_jobs_df, execution_manifest_df, source_artifact_df, paths = build_public_dataset_replacement_execution_scaffold(
            request_path=args.request,
            output_dir=args.output_dir,
        )
    except Exception as exc:
        print(f"ERROR: Public dataset replacement execution scaffold build failed: {exc}", file=sys.stderr)
        return 1

    print("Public dataset replacement execution scaffold complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Replacement candidates: {summary['replacement_candidate_count']}")
    print(f"Ready execution jobs: {summary['ready_execution_job_count']}")
    print(f"Skipped not ready: {summary['skipped_not_ready_count']}")
    print(f"Execution job manifests: {summary['execution_job_manifest_count']}")
    print(f"Report: {paths['execution_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

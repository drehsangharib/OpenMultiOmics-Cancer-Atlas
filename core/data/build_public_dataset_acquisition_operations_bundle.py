#!/usr/bin/env python3

import argparse
import html
import sys
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_OPERATIONS_REQUEST = Path("configs/public_data_sources/public_dataset_acquisition_operations_request.yaml")


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


def normalize_task_status(acquisition_status):
    status = safe_str(acquisition_status)
    if status == "local_file_present":
        return "complete_local_file_present"
    if status.startswith("pending_acquisition"):
        return "open_pending_acquisition"
    return "review_status_unknown"


def source_template(source_id, accession, modality, target_path):
    src = safe_str(source_id).lower()
    accession = safe_str(accession)
    modality = safe_str(modality)
    target_path = safe_str(target_path)
    if src == "gdc_tcga":
        return f"GDC/TCGA: export {accession} {modality} data as a tabular matrix or manifest-derived table; save to {target_path}."
    if src == "cptac":
        return f"CPTAC: export/download {accession} {modality} abundance table; save to {target_path}."
    if src == "metabolomics_workbench":
        return f"Metabolomics Workbench: select the cancer metabolomics study accession, export abundance data, and save to {target_path}."
    return f"Acquire/export {accession} {modality} public dataset and save to {target_path}."


def build_task_board(status_df):
    required = {
        "dataset_id", "display_name", "source_id", "accession_or_project_id", "atlas_hint", "modality",
        "expected_file_type", "acquisition_status", "target_local_path", "target_local_path_exists_current",
        "dataset_workspace_dir", "dataset_readme", "dataset_readme_exists_current", "operator_action",
    }
    require_columns(status_df, required, "acquisition_status_dashboard")
    rows = []
    for _, row in status_df.iterrows():
        task_status = normalize_task_status(row.get("acquisition_status", ""))
        rows.append({
            "task_id": f"acquire_{safe_str(row.get('dataset_id', '')).lower()}",
            "dataset_id": safe_str(row.get("dataset_id", "")),
            "display_name": safe_str(row.get("display_name", "")),
            "source_id": safe_str(row.get("source_id", "")),
            "accession_or_project_id": safe_str(row.get("accession_or_project_id", "")),
            "atlas_hint": safe_str(row.get("atlas_hint", "")),
            "modality": safe_str(row.get("modality", "")),
            "expected_file_type": safe_str(row.get("expected_file_type", "")),
            "task_status": task_status,
            "acquisition_status": safe_str(row.get("acquisition_status", "")),
            "target_local_path": safe_str(row.get("target_local_path", "")),
            "target_local_path_exists_current": safe_int(row.get("target_local_path_exists_current", 0)),
            "dataset_workspace_dir": safe_str(row.get("dataset_workspace_dir", "")),
            "dataset_readme": safe_str(row.get("dataset_readme", "")),
            "dataset_readme_exists_current": safe_int(row.get("dataset_readme_exists_current", 0)),
            "operator_action": safe_str(row.get("operator_action", "")),
            "source_template": source_template(row.get("source_id", ""), row.get("accession_or_project_id", ""), row.get("modality", ""), row.get("target_local_path", "")),
        })
    return pd.DataFrame(rows).sort_values(["task_status", "source_id", "modality", "dataset_id"]).reset_index(drop=True)


def build_checklist(task_board_df):
    lines = [
        "# Public Dataset Acquisition Checklist",
        "",
        "Use this checklist to acquire/export each real public dataset file and place it at the expected local replacement path.",
        "",
    ]
    for _, row in task_board_df.iterrows():
        checked = "x" if safe_str(row.get("task_status")) == "complete_local_file_present" else " "
        lines.extend([
            f"- [{checked}] **{safe_str(row.get('dataset_id'))}** — {safe_str(row.get('source_id'))} / {safe_str(row.get('modality'))}",
            f"  - accession_or_project_id: `{safe_str(row.get('accession_or_project_id'))}`",
            f"  - target_local_path: `{safe_str(row.get('target_local_path'))}`",
            f"  - task_status: `{safe_str(row.get('task_status'))}`",
            f"  - workspace_readme: `{safe_str(row.get('dataset_readme'))}`",
            f"  - instruction: {safe_str(row.get('source_template'))}",
            "",
        ])
    lines.extend([
        "## After placing files",
        "",
        "Run:",
        "",
        "```powershell",
        "python -m core.data.validate_public_dataset_replacement_readiness",
        "python -m core.data.build_public_dataset_replacement_execution_scaffold",
        "python -m core.data.validate_public_dataset_replacement_files",
        "```",
        "",
    ])
    return "\n".join(lines)


def build_source_templates(task_board_df):
    if task_board_df.empty:
        return pd.DataFrame(columns=["source_id", "dataset_count", "template"])
    rows = []
    for source_id, group in task_board_df.groupby("source_id"):
        examples = "; ".join(group["accession_or_project_id"].astype(str).tolist())
        if safe_str(source_id).lower() == "gdc_tcga":
            template = "Use GDC portal/API exports for TCGA projects; save tabular matrix outputs to each target_local_path."
        elif safe_str(source_id).lower() == "cptac":
            template = "Use CPTAC portal exports for proteomics abundance tables; save output tables to each target_local_path."
        elif safe_str(source_id).lower() == "metabolomics_workbench":
            template = "Use Metabolomics Workbench study exports for metabolite abundance data; save the selected export to target_local_path."
        else:
            template = "Use the source repository export mechanism and save the resulting table to target_local_path."
        rows.append({"source_id": source_id, "dataset_count": int(group.shape[0]), "example_accessions": examples, "template": template})
    return pd.DataFrame(rows).sort_values("source_id").reset_index(drop=True)


def build_progress_rollup(task_board_df):
    if task_board_df.empty:
        return pd.DataFrame(columns=["metric", "value"])
    total = int(task_board_df.shape[0])
    complete = int((task_board_df["task_status"] == "complete_local_file_present").sum())
    open_tasks = int((task_board_df["task_status"] == "open_pending_acquisition").sum())
    review = int((task_board_df["task_status"] == "review_status_unknown").sum())
    return pd.DataFrame([
        {"metric": "dataset_count", "value": total},
        {"metric": "tasks_complete", "value": complete},
        {"metric": "tasks_open", "value": open_tasks},
        {"metric": "tasks_review", "value": review},
        {"metric": "sources_covered", "value": int(task_board_df["source_id"].nunique())},
        {"metric": "modalities_covered", "value": int(task_board_df["modality"].nunique())},
    ])


def build_html_report(request, task_board_df, source_templates_df, progress_rollup_df, summary):
    title = "Public Dataset Acquisition Operations Bundle Report"
    return "\n".join([
        "<!DOCTYPE html>", "<html>", "<head>", "<meta charset='utf-8'>", f"<title>{escape_html(title)}</title>", "</head>", "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This report bundles acquisition operations: task board, checklist, source templates, and progress rollup.</p>",
        f"<p><strong>Request:</strong> {escape_html(request.get('request_id', ''))}</p>",
        f"<p><strong>Atlas:</strong> {escape_html(request.get('atlas_name', ''))}</p>",
        f"<p><strong>Datasets:</strong> {summary.get('dataset_count', 0)}</p>",
        f"<p><strong>Open tasks:</strong> {summary.get('tasks_open', 0)}</p>",
        f"<p><strong>Complete tasks:</strong> {summary.get('tasks_complete', 0)}</p>",
        "<h2>Task board</h2>", dataframe_to_html_table(task_board_df),
        "<h2>Source templates</h2>", dataframe_to_html_table(source_templates_df),
        "<h2>Progress rollup</h2>", dataframe_to_html_table(progress_rollup_df),
        "</body>", "</html>",
    ])


def build_public_dataset_acquisition_operations_bundle(request_path=DEFAULT_OPERATIONS_REQUEST, output_dir=None):
    request = load_yaml_mapping(request_path)
    inputs = request.get("inputs", {}) or {}
    status_dashboard_path = inputs.get("acquisition_status_dashboard")
    status_summary_path = inputs.get("acquisition_status_summary")
    if not status_dashboard_path:
        raise ValueError("Operations request missing inputs.acquisition_status_dashboard")
    if not status_summary_path:
        raise ValueError("Operations request missing inputs.acquisition_status_summary")

    status_df = read_table(status_dashboard_path)
    status_summary = load_yaml_mapping(status_summary_path)
    expected_outputs = request.get("expected_outputs", {}) or {}
    output_dir = ensure_dir(
        output_dir or expected_outputs.get(
            "acquisition_operations_dir",
            Path("outputs/public_data_acquisition") / request.get("atlas_name", "public_data_pilot") / "dataset_acquisition_operations",
        )
    )

    task_board_df = build_task_board(status_df)
    source_templates_df = build_source_templates(task_board_df)
    progress_rollup_df = build_progress_rollup(task_board_df)

    paths = {
        "task_board": Path(output_dir) / "public_dataset_acquisition_task_board.tsv",
        "checklist": Path(output_dir) / "public_dataset_acquisition_checklist.md",
        "source_templates": Path(output_dir) / "public_dataset_acquisition_source_templates.tsv",
        "progress_rollup": Path(output_dir) / "public_dataset_acquisition_progress_rollup.tsv",
        "operations_summary": Path(output_dir) / "public_dataset_acquisition_operations_summary.yaml",
        "operations_report": Path(output_dir) / "public_dataset_acquisition_operations_report.html",
    }

    task_board_df.to_csv(paths["task_board"], sep="\t", index=False)
    paths["checklist"].write_text(build_checklist(task_board_df), encoding="utf-8")
    source_templates_df.to_csv(paths["source_templates"], sep="\t", index=False)
    progress_rollup_df.to_csv(paths["progress_rollup"], sep="\t", index=False)

    metrics = {row["metric"]: int(row["value"]) for _, row in progress_rollup_df.iterrows()}
    summary = {
        "request_id": str(request.get("request_id", "")),
        "atlas_name": str(request.get("atlas_name", "")),
        "upstream_status_request_id": str(status_summary.get("request_id", "")),
        "upstream_status_output_dir": str(status_summary.get("output_dir", "")),
        "dataset_count": int(metrics.get("dataset_count", 0)),
        "tasks_open": int(metrics.get("tasks_open", 0)),
        "tasks_complete": int(metrics.get("tasks_complete", 0)),
        "tasks_review": int(metrics.get("tasks_review", 0)),
        "source_template_count": int(source_templates_df.shape[0]),
        "sources_covered": int(metrics.get("sources_covered", 0)),
        "modalities_covered": int(metrics.get("modalities_covered", 0)),
        "output_dir": str(output_dir),
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {
            "stage": "public_dataset_acquisition_operations_bundle",
            "purpose": "create task board, checklist, source templates, and progress rollup for public dataset acquisition",
        },
    }

    write_yaml(paths["operations_summary"], summary)
    paths["operations_report"].write_text(
        build_html_report(request, task_board_df, source_templates_df, progress_rollup_df, summary),
        encoding="utf-8",
    )
    return summary, task_board_df, source_templates_df, progress_rollup_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Build public dataset acquisition operations bundle.")
    parser.add_argument("--request", type=Path, default=DEFAULT_OPERATIONS_REQUEST)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        summary, task_board_df, source_templates_df, progress_rollup_df, paths = build_public_dataset_acquisition_operations_bundle(
            request_path=args.request,
            output_dir=args.output_dir,
        )
    except Exception as exc:
        print(f"ERROR: Public dataset acquisition operations bundle build failed: {exc}", file=sys.stderr)
        return 1

    print("Public dataset acquisition operations bundle complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Datasets: {summary['dataset_count']}")
    print(f"Open tasks: {summary['tasks_open']}")
    print(f"Complete tasks: {summary['tasks_complete']}")
    print(f"Source templates: {summary['source_template_count']}")
    print(f"Report: {paths['operations_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3

import argparse
import html
import sys
from pathlib import Path

import pandas as pd
import yaml

DEFAULT_INTAKE_REQUEST = Path("configs/public_data_sources/public_dataset_real_file_intake_request.yaml")


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


def slugify(value):
    text = safe_str(value).strip().lower()
    text = "".join(ch if ch.isalnum() else "_" for ch in text)
    return "_".join(token for token in text.split("_") if token) or "dataset"


def is_allowed_candidate(path, extensions):
    name = Path(path).name.lower()
    return any(name.endswith(str(ext).lower()) for ext in extensions)


def make_dropzone_readme(row, dropzone_dir):
    return "\n".join([
        f"# Real File Dropzone: {safe_str(row.get('dataset_id', ''))}",
        "",
        "Place the real public dataset export for this candidate in this directory or directly at the expected target path.",
        "",
        "## Dataset",
        f"- dataset_id: `{safe_str(row.get('dataset_id', ''))}`",
        f"- source_id: `{safe_str(row.get('source_id', ''))}`",
        f"- accession_or_project_id: `{safe_str(row.get('accession_or_project_id', ''))}`",
        f"- modality: `{safe_str(row.get('modality', ''))}`",
        f"- expected_file_type: `{safe_str(row.get('expected_file_type', ''))}`",
        "",
        "## Expected target local path",
        f"```text\n{safe_str(row.get('target_local_path', ''))}\n```",
        "",
        "## Dropzone directory",
        f"```text\n{dropzone_dir}\n```",
        "",
        "## After placing the file",
        "```powershell",
        "python -m core.data.validate_public_dataset_replacement_readiness",
        "python -m core.data.build_public_dataset_replacement_execution_scaffold",
        "python -m core.data.validate_public_dataset_replacement_files",
        "python -m core.data.build_public_dataset_acquisition_status_dashboard",
        "```",
        "",
        "Do not overwrite generated manifests or outputs. Only add real public data files.",
        "",
    ])


def scan_dropzone(dropzone_dir, extensions):
    dropzone_dir = Path(dropzone_dir)
    if not dropzone_dir.exists():
        return []
    return [str(p) for p in sorted(dropzone_dir.rglob("*")) if p.is_file() and is_allowed_candidate(p, extensions)]


def build_intake_bundle(task_board_df, dropzone_root, policy):
    required = {
        "task_id", "dataset_id", "source_id", "accession_or_project_id", "atlas_hint", "modality",
        "expected_file_type", "task_status", "target_local_path", "target_local_path_exists_current",
        "dataset_workspace_dir", "dataset_readme", "operator_action", "source_template",
    }
    require_columns(task_board_df, required, "acquisition_task_board")
    extensions = policy.get("candidate_extensions", [".tsv", ".csv", ".txt", ".tsv.gz", ".csv.gz"])
    dropzone_root = ensure_dir(dropzone_root)
    rows = []
    readme_rows = []
    for _, row in task_board_df.iterrows():
        dataset_id = safe_str(row.get("dataset_id", ""))
        atlas_hint = safe_str(row.get("atlas_hint", ""))
        modality = safe_str(row.get("modality", ""))
        dataset_dropzone_dir = dropzone_root / slugify(atlas_hint) / slugify(modality) / slugify(dataset_id)
        if bool(policy.get("create_dropzone_directories", True)):
            ensure_dir(dataset_dropzone_dir)
        readme_path = dataset_dropzone_dir / "README.md"
        if bool(policy.get("create_per_dataset_dropzone_readmes", True)):
            readme_path.write_text(make_dropzone_readme(row, dataset_dropzone_dir), encoding="utf-8")
        candidate_files = scan_dropzone(dataset_dropzone_dir, extensions) if bool(policy.get("scan_existing_candidate_files", True)) else []
        target_local_path = safe_str(row.get("target_local_path", ""))
        rows.append({
            "dataset_id": dataset_id,
            "source_id": safe_str(row.get("source_id", "")),
            "accession_or_project_id": safe_str(row.get("accession_or_project_id", "")),
            "atlas_hint": atlas_hint,
            "modality": modality,
            "expected_file_type": safe_str(row.get("expected_file_type", "")),
            "task_status": safe_str(row.get("task_status", "")),
            "target_local_path": target_local_path,
            "target_local_path_exists_current": int(Path(target_local_path).exists()) if target_local_path else 0,
            "dropzone_dir": str(dataset_dropzone_dir),
            "dropzone_dir_exists": int(dataset_dropzone_dir.exists()),
            "dropzone_readme": str(readme_path),
            "dropzone_readme_exists": int(readme_path.exists()),
            "candidate_file_count": len(candidate_files),
            "candidate_files": ";".join(candidate_files),
            "intake_status": "target_file_present" if target_local_path and Path(target_local_path).exists() else ("candidate_file_in_dropzone" if candidate_files else "awaiting_file"),
            "next_action": "Move/copy selected candidate file to target_local_path and rerun validation gates" if candidate_files else "Place real public dataset export in dropzone or target_local_path",
        })
        readme_rows.append({"dataset_id": dataset_id, "dropzone_readme": str(readme_path), "exists": int(readme_path.exists())})
    return pd.DataFrame(rows), pd.DataFrame(readme_rows)


def build_source_artifact_index(request):
    inputs = request.get("inputs", {}) or {}
    rows = []
    for label in ["acquisition_task_board", "acquisition_operations_summary", "acquisition_checklist"]:
        path = safe_str(inputs.get(label, ""))
        rows.append({"artifact_label": label, "path": path, "exists": int(Path(path).exists()) if path else 0})
    return pd.DataFrame(rows)


def build_html_report(request, intake_df, readme_df, source_artifact_df, summary):
    title = "Public Dataset Real File Intake Bundle Report"
    return "\n".join([
        "<!DOCTYPE html>", "<html>", "<head>", "<meta charset='utf-8'>", f"<title>{escape_html(title)}</title>", "</head>", "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This report summarizes the real public dataset file intake/dropzone workspace.</p>",
        f"<p><strong>Request:</strong> {escape_html(request.get('request_id', ''))}</p>",
        f"<p><strong>Atlas:</strong> {escape_html(request.get('atlas_name', ''))}</p>",
        f"<p><strong>Dataset count:</strong> {summary.get('dataset_count', 0)}</p>",
        f"<p><strong>Dropzone directories:</strong> {summary.get('dropzone_dir_count', 0)}</p>",
        f"<p><strong>Candidate files found:</strong> {summary.get('candidate_file_count', 0)}</p>",
        f"<p><strong>Target files present:</strong> {summary.get('target_file_present_count', 0)}</p>",
        "<h2>Intake inventory</h2>", dataframe_to_html_table(intake_df),
        "<h2>Dropzone README inventory</h2>", dataframe_to_html_table(readme_df),
        "<h2>Source artifacts</h2>", dataframe_to_html_table(source_artifact_df),
        "</body>", "</html>",
    ])


def build_public_dataset_real_file_intake_bundle(request_path=DEFAULT_INTAKE_REQUEST, output_dir=None, dropzone_root=None):
    request = load_yaml_mapping(request_path)
    inputs = request.get("inputs", {}) or {}
    policy = request.get("intake_policy", {}) or {}
    task_board_path = inputs.get("acquisition_task_board")
    operations_summary_path = inputs.get("acquisition_operations_summary")
    if not task_board_path:
        raise ValueError("Intake request missing inputs.acquisition_task_board")
    if not operations_summary_path:
        raise ValueError("Intake request missing inputs.acquisition_operations_summary")
    task_board_df = read_table(task_board_path)
    operations_summary = load_yaml_mapping(operations_summary_path)
    expected_outputs = request.get("expected_outputs", {}) or {}
    output_dir = ensure_dir(output_dir or expected_outputs.get("real_file_intake_dir", Path("outputs/public_data_acquisition") / request.get("atlas_name", "public_data_pilot") / "real_file_intake"))
    dropzone_root = Path(dropzone_root or expected_outputs.get("dropzone_root", Path("data/public") / request.get("atlas_name", "public_data_pilot") / "real_file_dropzone"))
    intake_df, readme_df = build_intake_bundle(task_board_df, dropzone_root, policy)
    source_artifact_df = build_source_artifact_index(request)
    paths = {
        "intake_inventory": Path(output_dir) / "public_dataset_real_file_intake_inventory.tsv",
        "dropzone_readme_inventory": Path(output_dir) / "public_dataset_real_file_dropzone_readme_inventory.tsv",
        "source_artifact_index": Path(output_dir) / "public_dataset_real_file_intake_source_artifact_index.tsv",
        "intake_summary": Path(output_dir) / "public_dataset_real_file_intake_summary.yaml",
        "intake_report": Path(output_dir) / "public_dataset_real_file_intake_report.html",
    }
    intake_df.to_csv(paths["intake_inventory"], sep="\t", index=False)
    readme_df.to_csv(paths["dropzone_readme_inventory"], sep="\t", index=False)
    source_artifact_df.to_csv(paths["source_artifact_index"], sep="\t", index=False)
    status_counts = intake_df["intake_status"].value_counts().to_dict() if not intake_df.empty else {}
    summary = {
        "request_id": str(request.get("request_id", "")),
        "atlas_name": str(request.get("atlas_name", "")),
        "upstream_operations_request_id": str(operations_summary.get("request_id", "")),
        "upstream_operations_output_dir": str(operations_summary.get("output_dir", "")),
        "dataset_count": int(intake_df.shape[0]),
        "dropzone_dir_count": int(intake_df["dropzone_dir_exists"].sum()) if not intake_df.empty else 0,
        "dropzone_readme_count": int(intake_df["dropzone_readme_exists"].sum()) if not intake_df.empty else 0,
        "candidate_file_count": int(intake_df["candidate_file_count"].sum()) if not intake_df.empty else 0,
        "target_file_present_count": int(status_counts.get("target_file_present", 0)),
        "awaiting_file_count": int(status_counts.get("awaiting_file", 0)),
        "candidate_file_in_dropzone_count": int(status_counts.get("candidate_file_in_dropzone", 0)),
        "dropzone_root": str(dropzone_root),
        "output_dir": str(output_dir),
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {"stage": "public_dataset_real_file_intake_bundle", "purpose": "create local dropzone and intake inventory for real public dataset files"},
    }
    write_yaml(paths["intake_summary"], summary)
    paths["intake_report"].write_text(build_html_report(request, intake_df, readme_df, source_artifact_df, summary), encoding="utf-8")
    return summary, intake_df, readme_df, source_artifact_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Build public dataset real file intake/dropzone bundle.")
    parser.add_argument("--request", type=Path, default=DEFAULT_INTAKE_REQUEST)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--dropzone-root", type=Path, default=None)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        summary, intake_df, readme_df, source_artifact_df, paths = build_public_dataset_real_file_intake_bundle(request_path=args.request, output_dir=args.output_dir, dropzone_root=args.dropzone_root)
    except Exception as exc:
        print(f"ERROR: Public dataset real file intake bundle build failed: {exc}", file=sys.stderr)
        return 1
    print("Public dataset real file intake bundle complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Datasets: {summary['dataset_count']}")
    print(f"Dropzone directories: {summary['dropzone_dir_count']}")
    print(f"Candidate files found: {summary['candidate_file_count']}")
    print(f"Target files present: {summary['target_file_present_count']}")
    print(f"Awaiting files: {summary['awaiting_file_count']}")
    print(f"Report: {paths['intake_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

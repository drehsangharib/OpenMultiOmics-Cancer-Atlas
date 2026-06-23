#!/usr/bin/env python3

import argparse
import html
import sys
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_WORKSPACE_REQUEST = Path("configs/public_data_sources/public_dataset_acquisition_workspace_request.yaml")


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


def slugify(value):
    text = safe_str(value).strip().lower()
    text = "".join(ch if ch.isalnum() else "_" for ch in text)
    return "_".join(token for token in text.split("_") if token) or "dataset"


def build_dataset_readme(row):
    dataset_id = safe_str(row.get("dataset_id", ""))
    title = safe_str(row.get("display_name", dataset_id))
    lines = [
        f"# Acquisition Workspace: {title}",
        "",
        "## Dataset identity",
        "",
        f"- dataset_id: `{dataset_id}`",
        f"- source_id: `{safe_str(row.get('source_id', ''))}`",
        f"- accession_or_project_id: `{safe_str(row.get('accession_or_project_id', ''))}`",
        f"- atlas_hint: `{safe_str(row.get('atlas_hint', ''))}`",
        f"- modality: `{safe_str(row.get('modality', ''))}`",
        f"- expected_file_type: `{safe_str(row.get('expected_file_type', ''))}`",
        "",
        "## Target local replacement path",
        "",
        f"```text\n{safe_str(row.get('target_local_path', ''))}\n```",
        "",
        "## Acquisition instruction",
        "",
        safe_str(row.get("acquisition_instruction", "")),
        "",
        "## Next action",
        "",
        safe_str(row.get("next_action", "")),
        "",
        "## Post-acquisition validation commands",
        "",
        "```powershell",
    ]
    commands = safe_str(row.get("post_acquisition_validation_commands", ""))
    for cmd in commands.split(";"):
        cmd = cmd.strip()
        if cmd:
            lines.append(cmd)
    lines.extend([
        "```",
        "",
        "## Non-destructive rule",
        "",
        "Do not overwrite placeholder manifests or generated workflow outputs. Place only the exported real public dataset file at the target local replacement path, then rerun validation gates.",
        "",
    ])
    return "\n".join(lines)


def build_workspace_index(instructions_df, output_dir, policy):
    require_columns(
        instructions_df,
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
            "acquisition_instruction",
            "next_action",
            "post_acquisition_validation_commands",
        },
        "acquisition_instructions",
    )
    workspace_root = ensure_dir(Path(output_dir) / "dataset_workspaces")
    rows = []
    for _, row in instructions_df.sort_values(["acquisition_needed", "dataset_id"], ascending=[False, True]).iterrows():
        dataset_id = safe_str(row.get("dataset_id", ""))
        dataset_workspace_dir = workspace_root / slugify(dataset_id)
        readme_path = dataset_workspace_dir / "README.md"
        if bool(policy.get("create_dataset_workspace_dirs", True)):
            ensure_dir(dataset_workspace_dir)
        if bool(policy.get("create_per_dataset_readme_files", True)):
            ensure_dir(dataset_workspace_dir)
            readme_path.write_text(build_dataset_readme(row), encoding="utf-8")

        target_local_path = safe_str(row.get("target_local_path", ""))
        rows.append(
            {
                "dataset_id": dataset_id,
                "display_name": safe_str(row.get("display_name", "")),
                "source_id": safe_str(row.get("source_id", "")),
                "accession_or_project_id": safe_str(row.get("accession_or_project_id", "")),
                "atlas_hint": safe_str(row.get("atlas_hint", "")),
                "modality": safe_str(row.get("modality", "")),
                "expected_file_type": safe_str(row.get("expected_file_type", "")),
                "acquisition_needed": safe_int(row.get("acquisition_needed", 0)),
                "target_local_path": target_local_path,
                "target_local_path_exists_current": int(Path(target_local_path).exists()) if target_local_path else 0,
                "dataset_workspace_dir": str(dataset_workspace_dir),
                "dataset_readme": str(readme_path),
                "dataset_readme_exists": int(readme_path.exists()),
                "next_action": safe_str(row.get("next_action", "")),
            }
        )
    return pd.DataFrame(rows)


def build_source_artifact_index(request):
    inputs = request.get("inputs", {}) or {}
    rows = []
    for label in ["acquisition_instructions", "acquisition_summary", "acquisition_source_artifact_index"]:
        path = safe_str(inputs.get(label, ""))
        rows.append({"artifact_label": label, "path": path, "exists": int(Path(path).exists()) if path else 0})
    return pd.DataFrame(rows)


def build_html_report(request, workspace_df, source_artifact_df, summary):
    title = "Public Dataset Acquisition Workspace Report"
    return "\n".join(
        [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<meta charset='utf-8'>",
            f"<title>{escape_html(title)}</title>",
            "</head>",
            "<body>",
            f"<h1>{escape_html(title)}</h1>",
            "<p>This report summarizes the local acquisition workspace generated from public dataset acquisition instructions.</p>",
            f"<p><strong>Request:</strong> {escape_html(request.get('request_id', ''))}</p>",
            f"<p><strong>Atlas:</strong> {escape_html(request.get('atlas_name', ''))}</p>",
            f"<p><strong>Workspace dataset count:</strong> {summary.get('workspace_dataset_count', 0)}</p>",
            f"<p><strong>Acquisition needed:</strong> {summary.get('acquisition_needed_count', 0)}</p>",
            f"<p><strong>Dataset README count:</strong> {summary.get('dataset_readme_count', 0)}</p>",
            "<h2>Workspace index</h2>",
            dataframe_to_html_table(workspace_df),
            "<h2>Source artifacts</h2>",
            dataframe_to_html_table(source_artifact_df),
            "<h2>Next step</h2>",
            "<p>Use each dataset workspace README to acquire/export public data, save it at target_local_path, then rerun a23/a24/a25 validation gates.</p>",
            "</body>",
            "</html>",
        ]
    )


def build_public_dataset_acquisition_workspace(request_path=DEFAULT_WORKSPACE_REQUEST, output_dir=None):
    request = load_yaml_mapping(request_path)
    inputs = request.get("inputs", {}) or {}
    policy = request.get("workspace_policy", {}) or {}

    instructions_path = inputs.get("acquisition_instructions")
    acquisition_summary_path = inputs.get("acquisition_summary")
    if not instructions_path:
        raise ValueError("Workspace request missing inputs.acquisition_instructions")
    if not acquisition_summary_path:
        raise ValueError("Workspace request missing inputs.acquisition_summary")

    instructions_df = read_table(instructions_path)
    acquisition_summary = load_yaml_mapping(acquisition_summary_path)

    expected_outputs = request.get("expected_outputs", {}) or {}
    output_dir = ensure_dir(
        output_dir
        or expected_outputs.get(
            "acquisition_workspace_dir",
            Path("outputs/public_data_acquisition")
            / request.get("atlas_name", "public_data_pilot")
            / "dataset_acquisition_workspace",
        )
    )

    workspace_df = build_workspace_index(instructions_df, output_dir, policy)
    source_artifact_df = build_source_artifact_index(request)

    paths = {
        "workspace_index": Path(output_dir) / "public_dataset_acquisition_workspace_index.tsv",
        "source_artifact_index": Path(output_dir) / "public_dataset_acquisition_workspace_source_artifact_index.tsv",
        "workspace_summary": Path(output_dir) / "public_dataset_acquisition_workspace_summary.yaml",
        "workspace_report": Path(output_dir) / "public_dataset_acquisition_workspace_report.html",
    }

    workspace_df.to_csv(paths["workspace_index"], sep="\t", index=False)
    source_artifact_df.to_csv(paths["source_artifact_index"], sep="\t", index=False)

    summary = {
        "request_id": str(request.get("request_id", "")),
        "atlas_name": str(request.get("atlas_name", "")),
        "upstream_acquisition_request_id": str(acquisition_summary.get("request_id", "")),
        "upstream_acquisition_output_dir": str(acquisition_summary.get("output_dir", "")),
        "workspace_dataset_count": int(workspace_df.shape[0]),
        "acquisition_needed_count": int(workspace_df["acquisition_needed"].sum()) if not workspace_df.empty else 0,
        "dataset_readme_count": int(workspace_df["dataset_readme_exists"].sum()) if not workspace_df.empty else 0,
        "local_file_present_count": int(workspace_df["target_local_path_exists_current"].sum()) if not workspace_df.empty else 0,
        "output_dir": str(output_dir),
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {
            "stage": "public_dataset_acquisition_workspace_builder",
            "purpose": "create local workspace directories and per-dataset checklists for public dataset acquisition",
        },
    }

    write_yaml(paths["workspace_summary"], summary)
    paths["workspace_report"].write_text(
        build_html_report(request, workspace_df, source_artifact_df, summary),
        encoding="utf-8",
    )
    return summary, workspace_df, source_artifact_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Build public dataset acquisition workspace.")
    parser.add_argument("--request", type=Path, default=DEFAULT_WORKSPACE_REQUEST)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        summary, workspace_df, source_artifact_df, paths = build_public_dataset_acquisition_workspace(
            request_path=args.request,
            output_dir=args.output_dir,
        )
    except Exception as exc:
        print(f"ERROR: Public dataset acquisition workspace build failed: {exc}", file=sys.stderr)
        return 1

    print("Public dataset acquisition workspace complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Workspace datasets: {summary['workspace_dataset_count']}")
    print(f"Acquisition needed: {summary['acquisition_needed_count']}")
    print(f"Dataset READMEs: {summary['dataset_readme_count']}")
    print(f"Local files already present: {summary['local_file_present_count']}")
    print(f"Report: {paths['workspace_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

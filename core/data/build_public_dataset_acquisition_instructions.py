#!/usr/bin/env python3

import argparse
import html
import sys
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_ACQUISITION_REQUEST = Path("configs/public_data_sources/public_dataset_acquisition_instructions_request.yaml")


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


def normalize_registry(registry):
    datasets = registry.get("datasets", {})
    if not isinstance(datasets, dict) or not datasets:
        raise ValueError("Dataset accession registry must contain a non-empty datasets mapping")
    rows = []
    for dataset_id, item in datasets.items():
        item = item if isinstance(item, dict) else {}
        rows.append(
            {
                "dataset_id": str(dataset_id),
                "display_name_registry": str(item.get("display_name", dataset_id)),
                "source_id_registry": str(item.get("source_id", "")),
                "accession_or_project_id_registry": str(item.get("accession_or_project_id", "")),
                "atlas_hint_registry": str(item.get("atlas_hint", "")),
                "modality_registry": str(item.get("modality", "")),
                "expected_file_type_registry": str(item.get("expected_file_type", "")),
                "replacement_priority_registry": safe_int(item.get("replacement_priority", 999), 999),
                "local_replacement_path_registry": str(item.get("local_replacement_path", "")),
                "notes_registry": str(item.get("notes", "")),
            }
        )
    return pd.DataFrame(rows)


def optional_read_table(path):
    path = Path(safe_str(path))
    if not safe_str(path):
        return pd.DataFrame()
    if not path.exists():
        return pd.DataFrame()
    return read_table(path)


def source_guidance(source_id, accession_or_project_id, modality, expected_file_type):
    source = safe_str(source_id).lower()
    accession = safe_str(accession_or_project_id)
    modality_text = safe_str(modality)
    expected = safe_str(expected_file_type)
    if source == "gdc_tcga":
        return f"Use the GDC portal/API to export/download {accession} {modality_text} data as {expected}; save the resulting matrix or manifest-derived table to the planned local_replacement_path."
    if source == "cptac":
        return f"Use the CPTAC portal/export workflow to obtain {accession} {modality_text} abundance data as {expected}; save the table to the planned local_replacement_path."
    if source == "metabolomics_workbench":
        return f"Use Metabolomics Workbench to select a cancer metabolomics study accession, export abundance data as {expected}, and save it to the planned local_replacement_path."
    return f"Acquire/export {accession} {modality_text} public dataset as {expected} and save it to the planned local_replacement_path."


def build_acquisition_instructions(registry_df, replacement_plan_df, readiness_df, execution_jobs_df, file_validation_df, policy):
    require_columns(
        replacement_plan_df,
        {
            "dataset_id",
            "display_name",
            "source_id",
            "accession_or_project_id",
            "atlas_hint",
            "modality",
            "expected_file_type",
            "replacement_priority",
            "local_replacement_path",
            "replacement_file_exists",
            "replacement_status",
            "recommended_action",
        },
        "replacement_plan",
    )

    df = replacement_plan_df.copy()
    if not registry_df.empty:
        df = df.merge(registry_df, on="dataset_id", how="left")

    if not readiness_df.empty and "dataset_id" in readiness_df.columns:
        slim = readiness_df[[col for col in ["dataset_id", "readiness_status", "readiness_message"] if col in readiness_df.columns]].copy()
        df = df.merge(slim, on="dataset_id", how="left")
    else:
        df["readiness_status"] = ""
        df["readiness_message"] = ""

    if not execution_jobs_df.empty and "dataset_id" in execution_jobs_df.columns:
        slim = execution_jobs_df[[col for col in ["dataset_id", "execution_status", "skip_reason"] if col in execution_jobs_df.columns]].copy()
        df = df.merge(slim, on="dataset_id", how="left")
    else:
        df["execution_status"] = ""
        df["skip_reason"] = ""

    if not file_validation_df.empty and "dataset_id" in file_validation_df.columns:
        slim = file_validation_df[[col for col in ["dataset_id", "file_validation_status", "file_validation_message"] if col in file_validation_df.columns]].copy()
        df = df.merge(slim, on="dataset_id", how="left")
    else:
        df["file_validation_status"] = ""
        df["file_validation_message"] = ""

    df["local_replacement_path_exists_current"] = df["local_replacement_path"].apply(
        lambda p: int(Path(safe_str(p)).exists()) if safe_str(p).strip() else 0
    )
    df["acquisition_needed"] = df["local_replacement_path_exists_current"].apply(lambda x: int(safe_int(x) != 1))
    df["acquisition_priority"] = df["replacement_priority"].apply(lambda x: safe_int(x, 999))
    df["acquisition_instruction"] = df.apply(
        lambda row: source_guidance(
            row.get("source_id", ""),
            row.get("accession_or_project_id", ""),
            row.get("modality", ""),
            row.get("expected_file_type", ""),
        ),
        axis=1,
    )
    df["target_local_path"] = df["local_replacement_path"]
    df["post_acquisition_validation_commands"] = (
        "python -m core.data.validate_public_dataset_replacement_readiness; "
        "python -m core.data.build_public_dataset_replacement_execution_scaffold; "
        "python -m core.data.validate_public_dataset_replacement_files"
    )
    df["next_action"] = df.apply(
        lambda row: f"Acquire/export data and save to {row['target_local_path']}" if safe_int(row["acquisition_needed"]) else "File exists locally; rerun readiness/execution/file validation gates.",
        axis=1,
    )

    if bool(policy.get("include_only_not_ready_or_unvalidated", False)):
        df = df[df["acquisition_needed"] == 1].copy()

    keep = [
        "dataset_id",
        "display_name",
        "source_id",
        "accession_or_project_id",
        "atlas_hint",
        "modality",
        "expected_file_type",
        "acquisition_priority",
        "replacement_status",
        "readiness_status",
        "execution_status",
        "file_validation_status",
        "target_local_path",
        "local_replacement_path_exists_current",
        "acquisition_needed",
        "acquisition_instruction",
        "next_action",
        "post_acquisition_validation_commands",
        "recommended_action",
        "notes",
    ]
    for col in keep:
        if col not in df.columns:
            df[col] = ""
    return df.loc[:, keep].sort_values("acquisition_priority").reset_index(drop=True)


def build_source_artifact_index(request):
    inputs = request.get("inputs", {}) or {}
    rows = []
    labels = [
        "dataset_accession_registry",
        "replacement_plan",
        "readiness_table",
        "execution_jobs",
        "file_validation_table",
    ]
    for label in labels:
        path = safe_str(inputs.get(label, ""))
        rows.append({"artifact_label": label, "path": path, "exists": int(Path(path).exists()) if path else 0})
    return pd.DataFrame(rows)


def build_html_report(request, instructions_df, source_artifact_df, summary):
    title = "Public Dataset Acquisition Instructions Report"
    parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        f"<title>{escape_html(title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This report provides actionable instructions for acquiring or exporting real public dataset files and placing them at the expected local replacement paths.</p>",
        f"<p><strong>Request:</strong> {escape_html(request.get('request_id', ''))}</p>",
        f"<p><strong>Atlas:</strong> {escape_html(request.get('atlas_name', ''))}</p>",
        f"<p><strong>Instruction count:</strong> {summary.get('instruction_count', 0)}</p>",
        f"<p><strong>Acquisition needed:</strong> {summary.get('acquisition_needed_count', 0)}</p>",
        f"<p><strong>Local files already present:</strong> {summary.get('local_file_present_count', 0)}</p>",
        "<h2>Acquisition instructions</h2>",
        dataframe_to_html_table(instructions_df),
        "<h2>Source artifacts</h2>",
        dataframe_to_html_table(source_artifact_df),
        "<h2>Next step</h2>",
        "<p>Acquire the listed public files, place them at target_local_path, then rerun readiness, execution scaffold, and file validation gates.</p>",
        "</body>",
        "</html>",
    ]
    return "\n".join(parts)


def build_public_dataset_acquisition_instructions(request_path=DEFAULT_ACQUISITION_REQUEST, output_dir=None):
    request = load_yaml_mapping(request_path)
    inputs = request.get("inputs", {}) or {}
    policy = request.get("instruction_policy", {}) or {}

    registry_path = inputs.get("dataset_accession_registry")
    replacement_plan_path = inputs.get("replacement_plan")
    if not registry_path:
        raise ValueError("Acquisition instruction request missing inputs.dataset_accession_registry")
    if not replacement_plan_path:
        raise ValueError("Acquisition instruction request missing inputs.replacement_plan")

    registry_df = normalize_registry(load_yaml_mapping(registry_path))
    replacement_plan_df = read_table(replacement_plan_path)
    readiness_df = optional_read_table(inputs.get("readiness_table", ""))
    execution_jobs_df = optional_read_table(inputs.get("execution_jobs", ""))
    file_validation_df = optional_read_table(inputs.get("file_validation_table", ""))

    expected_outputs = request.get("expected_outputs", {}) or {}
    output_dir = ensure_dir(
        output_dir
        or expected_outputs.get(
            "acquisition_instructions_dir",
            Path("outputs/public_data_acquisition")
            / request.get("atlas_name", "public_data_pilot")
            / "dataset_acquisition_instructions",
        )
    )

    instructions_df = build_acquisition_instructions(
        registry_df,
        replacement_plan_df,
        readiness_df,
        execution_jobs_df,
        file_validation_df,
        policy,
    )
    source_artifact_df = build_source_artifact_index(request)

    paths = {
        "acquisition_instructions": Path(output_dir) / "public_dataset_acquisition_instructions.tsv",
        "source_artifact_index": Path(output_dir) / "public_dataset_acquisition_instructions_source_artifact_index.tsv",
        "acquisition_summary": Path(output_dir) / "public_dataset_acquisition_instructions_summary.yaml",
        "acquisition_report": Path(output_dir) / "public_dataset_acquisition_instructions_report.html",
    }

    instructions_df.to_csv(paths["acquisition_instructions"], sep="\t", index=False)
    source_artifact_df.to_csv(paths["source_artifact_index"], sep="\t", index=False)

    summary = {
        "request_id": str(request.get("request_id", "")),
        "atlas_name": str(request.get("atlas_name", "")),
        "instruction_count": int(instructions_df.shape[0]),
        "acquisition_needed_count": int(instructions_df["acquisition_needed"].sum()) if not instructions_df.empty else 0,
        "local_file_present_count": int((instructions_df["local_replacement_path_exists_current"] == 1).sum()) if not instructions_df.empty else 0,
        "output_dir": str(output_dir),
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {
            "stage": "public_dataset_acquisition_instructions_builder",
            "purpose": "generate actionable instructions for acquiring real public dataset replacement files",
        },
    }

    write_yaml(paths["acquisition_summary"], summary)
    paths["acquisition_report"].write_text(
        build_html_report(request, instructions_df, source_artifact_df, summary),
        encoding="utf-8",
    )
    return summary, instructions_df, source_artifact_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Build public dataset acquisition instructions.")
    parser.add_argument("--request", type=Path, default=DEFAULT_ACQUISITION_REQUEST)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        summary, instructions_df, source_artifact_df, paths = build_public_dataset_acquisition_instructions(
            request_path=args.request,
            output_dir=args.output_dir,
        )
    except Exception as exc:
        print(f"ERROR: Public dataset acquisition instructions build failed: {exc}", file=sys.stderr)
        return 1

    print("Public dataset acquisition instructions complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Instructions: {summary['instruction_count']}")
    print(f"Acquisition needed: {summary['acquisition_needed_count']}")
    print(f"Local files already present: {summary['local_file_present_count']}")
    print(f"Report: {paths['acquisition_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

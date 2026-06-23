#!/usr/bin/env python3

import argparse
import html
import sys
from pathlib import Path

import pandas as pd
import yaml

DEFAULT_SOURCE_ACCESS_REQUEST = Path("configs/public_data_sources/public_dataset_source_access_packet_request.yaml")


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
    if not safe_str(path):
        return pd.DataFrame()
    if not path.exists():
        return pd.DataFrame()
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


def normalize_registry(registry):
    datasets = registry.get("datasets", {})
    if not isinstance(datasets, dict) or not datasets:
        raise ValueError("Dataset accession registry must contain a non-empty datasets mapping")
    rows = []
    for dataset_id, item in datasets.items():
        item = item if isinstance(item, dict) else {}
        rows.append({
            "dataset_id": str(dataset_id),
            "display_name": str(item.get("display_name", dataset_id)),
            "source_id": str(item.get("source_id", "")),
            "accession_or_project_id": str(item.get("accession_or_project_id", "")),
            "atlas_hint": str(item.get("atlas_hint", "")),
            "modality": str(item.get("modality", "")),
            "expected_file_type": str(item.get("expected_file_type", "")),
            "replacement_priority": safe_int(item.get("replacement_priority", 999), 999),
            "local_replacement_path": str(item.get("local_replacement_path", "")),
            "notes": str(item.get("notes", "")),
        })
    return pd.DataFrame(rows).sort_values("replacement_priority").reset_index(drop=True)


def slugify(value):
    text = safe_str(value).lower().strip()
    text = "".join(ch if ch.isalnum() else "_" for ch in text)
    return "_".join(t for t in text.split("_") if t) or "dataset"


def portal_url(source_id, accession):
    source = safe_str(source_id).lower()
    acc = safe_str(accession)
    if source == "gdc_tcga":
        return f"https://portal.gdc.cancer.gov/projects/{acc}"
    if source == "cptac":
        return "https://proteomic.datacommons.cancer.gov/pdc/"
    if source == "metabolomics_workbench":
        if acc and not acc.startswith("REPLACE_WITH"):
            return f"https://www.metabolomicsworkbench.org/data/DRCCMetadata.php?Mode=Study&StudyID={acc}"
        return "https://www.metabolomicsworkbench.org/data/"
    return ""


def command_template(source_id, accession, target_path):
    source = safe_str(source_id).lower()
    acc = safe_str(accession)
    target = safe_str(target_path)
    if source == "gdc_tcga":
        return f"# GDC portal/API export needed for {acc}; save exported table to: {target}"
    if source == "cptac":
        return f"# CPTAC/PDC portal export needed for {acc}; save protein abundance table to: {target}"
    if source == "metabolomics_workbench":
        return f"# Metabolomics Workbench study export needed; replace accession if needed and save abundance table to: {target}"
    return f"# Source export needed for {acc}; save table to: {target}"


def merge_optional_status(base_df, task_board_df, intake_df, schema_df):
    df = base_df.copy()
    if not task_board_df.empty and "dataset_id" in task_board_df.columns:
        cols = [c for c in ["dataset_id", "task_status", "target_local_path", "operator_action"] if c in task_board_df.columns]
        df = df.merge(task_board_df[cols], on="dataset_id", how="left")
    if not intake_df.empty and "dataset_id" in intake_df.columns:
        cols = [c for c in ["dataset_id", "intake_status", "candidate_file_count", "dropzone_dir"] if c in intake_df.columns]
        df = df.merge(intake_df[cols], on="dataset_id", how="left")
    if not schema_df.empty and "dataset_id" in schema_df.columns:
        cols = [c for c in ["dataset_id", "schema_validation_status", "schema_candidate_file"] if c in schema_df.columns]
        df = df.merge(schema_df[cols], on="dataset_id", how="left")
    return df


def build_access_packet_table(registry_df, task_board_df, intake_df, schema_df):
    df = merge_optional_status(registry_df, task_board_df, intake_df, schema_df)
    if "target_local_path" not in df.columns:
        df["target_local_path"] = df["local_replacement_path"]
    df["target_local_path"] = df["target_local_path"].fillna(df["local_replacement_path"])
    for col in ["task_status", "intake_status", "schema_validation_status", "candidate_file_count", "dropzone_dir", "schema_candidate_file", "operator_action"]:
        if col not in df.columns:
            df[col] = ""
    df["portal_url"] = df.apply(lambda r: portal_url(r["source_id"], r["accession_or_project_id"]), axis=1)
    df["command_template"] = df.apply(lambda r: command_template(r["source_id"], r["accession_or_project_id"], r["target_local_path"]), axis=1)
    df["source_packet_id"] = df.apply(lambda r: slugify(f"{r['dataset_id']}_{r['source_id']}_{r['modality']}"), axis=1)
    df["operator_next_step"] = df.apply(
        lambda r: "Resolve placeholder accession before acquisition" if safe_str(r["accession_or_project_id"]).startswith("REPLACE_WITH") else "Open portal_url, export/download table, save to target_local_path, rerun a23-a31 validation sequence",
        axis=1,
    )
    keep = [
        "source_packet_id", "dataset_id", "display_name", "source_id", "accession_or_project_id", "atlas_hint", "modality",
        "expected_file_type", "replacement_priority", "target_local_path", "task_status", "intake_status", "schema_validation_status",
        "candidate_file_count", "dropzone_dir", "schema_candidate_file", "portal_url", "command_template", "operator_next_step", "notes",
    ]
    return df.loc[:, keep].sort_values("replacement_priority").reset_index(drop=True)


def write_packet_yamls(packet_df, output_dir):
    packet_dir = ensure_dir(Path(output_dir) / "source_packet_yamls")
    rows = []
    for _, row in packet_df.iterrows():
        out = packet_dir / f"{safe_str(row['source_packet_id'])}.yaml"
        packet = {col: (int(row[col]) if col in ["replacement_priority", "candidate_file_count"] and safe_str(row[col]) else safe_str(row[col])) for col in packet_df.columns}
        packet["post_acquisition_validation_commands"] = [
            "python -m core.data.validate_public_dataset_replacement_readiness",
            "python -m core.data.build_public_dataset_replacement_execution_scaffold",
            "python -m core.data.validate_public_dataset_replacement_files",
            "python -m core.data.validate_public_dataset_modality_schemas",
        ]
        packet["agent_role"] = {"stage": "public_dataset_source_access_packet", "purpose": "operator-ready public source access packet"}
        write_yaml(out, packet)
        rows.append({"dataset_id": safe_str(row["dataset_id"]), "source_packet_yaml": str(out), "source_packet_yaml_exists": int(out.exists())})
    return pd.DataFrame(rows)


def build_html_report(request, packet_df, packet_inventory_df, summary):
    title = "Public Dataset Source Access Packet Report"
    return "\n".join([
        "<!DOCTYPE html>", "<html>", "<head>", "<meta charset='utf-8'>", f"<title>{escape_html(title)}</title>", "</head>", "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This report provides source-specific access packets for acquiring real public dataset files.</p>",
        f"<p><strong>Request:</strong> {escape_html(request.get('request_id', ''))}</p>",
        f"<p><strong>Atlas:</strong> {escape_html(request.get('atlas_name', ''))}</p>",
        f"<p><strong>Packet count:</strong> {summary.get('source_packet_count', 0)}</p>",
        f"<p><strong>Placeholder accession count:</strong> {summary.get('placeholder_accession_count', 0)}</p>",
        "<h2>Source access packets</h2>", dataframe_to_html_table(packet_df),
        "<h2>Packet YAML inventory</h2>", dataframe_to_html_table(packet_inventory_df),
        "</body>", "</html>",
    ])


def build_public_dataset_source_access_packet(request_path=DEFAULT_SOURCE_ACCESS_REQUEST, output_dir=None):
    request = load_yaml_mapping(request_path)
    inputs = request.get("inputs", {}) or {}
    registry_path = inputs.get("dataset_accession_registry")
    if not registry_path:
        raise ValueError("Source access request missing inputs.dataset_accession_registry")
    registry_df = normalize_registry(load_yaml_mapping(registry_path))
    task_board_df = read_table(inputs.get("acquisition_task_board", ""))
    intake_df = read_table(inputs.get("real_file_intake_inventory", ""))
    schema_df = read_table(inputs.get("modality_schema_validation_table", ""))
    expected_outputs = request.get("expected_outputs", {}) or {}
    output_dir = ensure_dir(output_dir or expected_outputs.get("source_access_packet_dir", Path("outputs/public_data_acquisition") / request.get("atlas_name", "public_data_pilot") / "source_access_packets"))
    packet_df = build_access_packet_table(registry_df, task_board_df, intake_df, schema_df)
    packet_inventory_df = write_packet_yamls(packet_df, output_dir)
    paths = {
        "source_access_packets": Path(output_dir) / "public_dataset_source_access_packets.tsv",
        "portal_link_table": Path(output_dir) / "public_dataset_source_portal_links.tsv",
        "command_templates": Path(output_dir) / "public_dataset_source_command_templates.ps1",
        "packet_yaml_inventory": Path(output_dir) / "public_dataset_source_packet_yaml_inventory.tsv",
        "source_access_summary": Path(output_dir) / "public_dataset_source_access_summary.yaml",
        "source_access_report": Path(output_dir) / "public_dataset_source_access_report.html",
    }
    packet_df.to_csv(paths["source_access_packets"], sep="\t", index=False)
    packet_df[["dataset_id", "source_id", "accession_or_project_id", "portal_url", "target_local_path"]].to_csv(paths["portal_link_table"], sep="\t", index=False)
    paths["command_templates"].write_text("\n".join(packet_df["command_template"].astype(str).tolist()) + "\n", encoding="utf-8")
    packet_inventory_df.to_csv(paths["packet_yaml_inventory"], sep="\t", index=False)
    summary = {
        "request_id": str(request.get("request_id", "")),
        "atlas_name": str(request.get("atlas_name", "")),
        "source_packet_count": int(packet_df.shape[0]),
        "source_count": int(packet_df["source_id"].nunique()) if not packet_df.empty else 0,
        "modality_count": int(packet_df["modality"].nunique()) if not packet_df.empty else 0,
        "placeholder_accession_count": int(packet_df["accession_or_project_id"].astype(str).str.startswith("REPLACE_WITH").sum()) if not packet_df.empty else 0,
        "packet_yaml_count": int(packet_inventory_df["source_packet_yaml_exists"].sum()) if not packet_inventory_df.empty else 0,
        "output_dir": str(output_dir),
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {"stage": "public_dataset_source_access_packet_bundle", "purpose": "create source-specific access packets and operator templates for public data acquisition"},
    }
    write_yaml(paths["source_access_summary"], summary)
    paths["source_access_report"].write_text(build_html_report(request, packet_df, packet_inventory_df, summary), encoding="utf-8")
    return summary, packet_df, packet_inventory_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Build public dataset source access packets.")
    parser.add_argument("--request", type=Path, default=DEFAULT_SOURCE_ACCESS_REQUEST)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        summary, packet_df, packet_inventory_df, paths = build_public_dataset_source_access_packet(request_path=args.request, output_dir=args.output_dir)
    except Exception as exc:
        print(f"ERROR: Public dataset source access packet build failed: {exc}", file=sys.stderr)
        return 1
    print("Public dataset source access packet bundle complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Source packets: {summary['source_packet_count']}")
    print(f"Sources: {summary['source_count']}")
    print(f"Modalities: {summary['modality_count']}")
    print(f"Placeholder accessions: {summary['placeholder_accession_count']}")
    print(f"Packet YAMLs: {summary['packet_yaml_count']}")
    print(f"Report: {paths['source_access_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

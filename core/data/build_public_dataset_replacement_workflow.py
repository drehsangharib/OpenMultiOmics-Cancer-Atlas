#!/usr/bin/env python3

import argparse
import html
import sys
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_REPLACEMENT_REQUEST = Path("configs/public_data_sources/public_dataset_replacement_request.yaml")


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


def normalize_dataset_registry(registry):
    datasets = registry.get("datasets", {})
    if not isinstance(datasets, dict) or not datasets:
        raise ValueError("Dataset accession registry must contain a non-empty datasets mapping")
    rows = []
    for dataset_id, item in datasets.items():
        if not isinstance(item, dict):
            item = {}
        rows.append(
            {
                "dataset_id": str(dataset_id),
                "display_name": str(item.get("display_name", dataset_id)),
                "source_id": str(item.get("source_id", "")),
                "accession_or_project_id": str(item.get("accession_or_project_id", "")),
                "atlas_hint": str(item.get("atlas_hint", "")),
                "modality": str(item.get("modality", "")),
                "expected_file_type": str(item.get("expected_file_type", "")),
                "replacement_priority": int(item.get("replacement_priority", 999)),
                "local_replacement_path": str(item.get("local_replacement_path", "")),
                "notes": str(item.get("notes", "")),
            }
        )
    return pd.DataFrame(rows).sort_values("replacement_priority").reset_index(drop=True)


def build_replacement_plan(dataset_df, local_requirements_df, manifest_inventory_df):
    required_cols = {"atlas_hint", "modality", "local_file_path"}
    missing = required_cols - set(local_requirements_df.columns)
    if missing:
        raise ValueError("local_file_requirements table missing columns: " + ", ".join(sorted(missing)))
    if "materialized_manifest_stub" not in manifest_inventory_df.columns:
        raise ValueError("materialized_manifest_inventory table must contain materialized_manifest_stub")

    merged = dataset_df.merge(
        local_requirements_df,
        on=["atlas_hint", "modality"],
        how="left",
        suffixes=("", "_placeholder"),
    )
    merged = merged.merge(
        manifest_inventory_df[["atlas_hint", "modality", "materialized_manifest_stub"]],
        on=["atlas_hint", "modality"],
        how="left",
    )
    merged["placeholder_exists"] = merged["local_file_path"].apply(lambda p: int(Path(str(p)).exists()) if pd.notna(p) else 0)
    merged["replacement_file_exists"] = merged["local_replacement_path"].apply(lambda p: int(Path(str(p)).exists()) if pd.notna(p) else 0)
    merged["replacement_status"] = merged.apply(
        lambda row: "ready_with_real_file" if int(row["replacement_file_exists"]) == 1 else "awaiting_real_public_file",
        axis=1,
    )
    merged["recommended_action"] = merged.apply(
        lambda row: f"Download/export {row['accession_or_project_id']} {row['modality']} data and save to {row['local_replacement_path']}",
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
        "replacement_priority",
        "local_file_path",
        "placeholder_exists",
        "local_replacement_path",
        "replacement_file_exists",
        "materialized_manifest_stub",
        "replacement_status",
        "recommended_action",
        "notes",
    ]
    return merged.loc[:, keep].copy()


def make_replacement_stubs(replacement_plan_df, output_dir):
    stub_dir = ensure_dir(Path(output_dir) / "replacement_manifest_stubs")
    rows = []
    for _, row in replacement_plan_df.iterrows():
        source_manifest = Path(str(row["materialized_manifest_stub"]))
        if not source_manifest.exists():
            rows.append(
                {
                    "dataset_id": row["dataset_id"],
                    "replacement_manifest_stub": "",
                    "source_manifest_exists": 0,
                    "replacement_manifest_stub_exists": 0,
                }
            )
            continue
        manifest = load_yaml_mapping(source_manifest)
        manifest["manifest_id"] = str(manifest.get("manifest_id", row["dataset_id"])).replace("materialized_public_data_manifest", "real_public_data_manifest")
        manifest["source_accession_or_project_id"] = str(row["accession_or_project_id"])
        manifest["source_dataset_id"] = str(row["dataset_id"])
        manifest["replacement_status"] = str(row["replacement_status"])
        if manifest.get("input_files") and isinstance(manifest["input_files"], list):
            manifest["input_files"][0]["placeholder_path"] = str(row["local_file_path"])
            manifest["input_files"][0]["path"] = str(row["local_replacement_path"])
        manifest["agent_role"] = {
            "stage": "real_public_data_manifest_replacement_stub",
            "purpose": "use this manifest after replacing placeholder paths with real public repository files",
        }
        out_path = stub_dir / f"{row['atlas_hint']}_{row['modality']}_real_public_data_manifest.yaml"
        write_yaml(out_path, manifest)
        rows.append(
            {
                "dataset_id": row["dataset_id"],
                "atlas_hint": row["atlas_hint"],
                "modality": row["modality"],
                "source_manifest": str(source_manifest),
                "replacement_manifest_stub": str(out_path),
                "source_manifest_exists": 1,
                "replacement_manifest_stub_exists": int(out_path.exists()),
            }
        )
    return pd.DataFrame(rows)


def build_html_report(request, replacement_plan_df, replacement_stub_df, source_artifact_df, summary):
    title = "Public Dataset Replacement Workflow Report"
    parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        f"<title>{escape_html(title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This report maps placeholder public-data matrices to real public dataset accession candidates and replacement manifest stubs.</p>",
        f"<p><strong>Request:</strong> {escape_html(request.get('request_id', ''))}</p>",
        f"<p><strong>Atlas:</strong> {escape_html(request.get('atlas_name', ''))}</p>",
        f"<p><strong>Replacement candidates:</strong> {summary.get('replacement_candidate_count', 0)}</p>",
        f"<p><strong>Ready with real files:</strong> {summary.get('ready_replacement_file_count', 0)}</p>",
        "<h2>Replacement plan</h2>",
        dataframe_to_html_table(replacement_plan_df),
        "<h2>Replacement manifest stubs</h2>",
        dataframe_to_html_table(replacement_stub_df),
        "<h2>Source artifacts</h2>",
        dataframe_to_html_table(source_artifact_df),
        "<h2>Next step</h2>",
        "<p>Download or export each listed public dataset, save each file to the planned local replacement path, then rerun the corresponding real public-data manifests through the modality processors.</p>",
        "</body>",
        "</html>",
    ]
    return "\n".join(parts)


def build_public_dataset_replacement_workflow(request_path=DEFAULT_REPLACEMENT_REQUEST, output_dir=None):
    request = load_yaml_mapping(request_path)
    registry = load_yaml_mapping(request["dataset_accession_registry"])
    dataset_df = normalize_dataset_registry(registry)
    local_requirements_df = read_table(request["local_file_requirements"])
    manifest_inventory_df = read_table(request["materialized_manifest_inventory"])
    dashboard_summary = load_yaml_mapping(request["portfolio_dashboard_summary"])

    expected_outputs = request.get("expected_outputs", {}) or {}
    output_dir = ensure_dir(output_dir or expected_outputs.get("replacement_workflow_dir", Path("outputs/public_data_acquisition") / request.get("atlas_name", "public_data_pilot") / "dataset_replacement_workflow"))

    replacement_plan_df = build_replacement_plan(dataset_df, local_requirements_df, manifest_inventory_df)
    replacement_stub_df = make_replacement_stubs(replacement_plan_df, output_dir)

    source_artifact_df = pd.DataFrame(
        [
            {"artifact_label": "dataset_accession_registry", "path": str(request["dataset_accession_registry"]), "exists": int(Path(request["dataset_accession_registry"]).exists())},
            {"artifact_label": "local_file_requirements", "path": str(request["local_file_requirements"]), "exists": int(Path(request["local_file_requirements"]).exists())},
            {"artifact_label": "materialized_manifest_inventory", "path": str(request["materialized_manifest_inventory"]), "exists": int(Path(request["materialized_manifest_inventory"]).exists())},
            {"artifact_label": "portfolio_dashboard_summary", "path": str(request["portfolio_dashboard_summary"]), "exists": int(Path(request["portfolio_dashboard_summary"]).exists())},
        ]
    )

    paths = {
        "replacement_plan": Path(output_dir) / "public_dataset_replacement_plan.tsv",
        "replacement_manifest_inventory": Path(output_dir) / "replacement_manifest_inventory.tsv",
        "source_artifact_index": Path(output_dir) / "replacement_source_artifact_index.tsv",
        "replacement_summary": Path(output_dir) / "public_dataset_replacement_summary.yaml",
        "replacement_report": Path(output_dir) / "public_dataset_replacement_report.html",
    }

    replacement_plan_df.to_csv(paths["replacement_plan"], sep="\t", index=False)
    replacement_stub_df.to_csv(paths["replacement_manifest_inventory"], sep="\t", index=False)
    source_artifact_df.to_csv(paths["source_artifact_index"], sep="\t", index=False)

    summary = {
        "request_id": str(request.get("request_id", "")),
        "atlas_name": str(request.get("atlas_name", "")),
        "portfolio_id": str(dashboard_summary.get("portfolio_id", "")),
        "dataset_accession_registry": str(request["dataset_accession_registry"]),
        "replacement_candidate_count": int(replacement_plan_df.shape[0]),
        "ready_replacement_file_count": int(replacement_plan_df["replacement_file_exists"].sum()) if not replacement_plan_df.empty else 0,
        "replacement_manifest_stub_count": int(replacement_stub_df["replacement_manifest_stub_exists"].sum()) if not replacement_stub_df.empty else 0,
        "output_dir": str(output_dir),
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {
            "stage": "public_dataset_replacement_workflow",
            "purpose": "formalize replacement of placeholder matrices with real public dataset accession files",
        },
    }

    write_yaml(paths["replacement_summary"], summary)
    paths["replacement_report"].write_text(build_html_report(request, replacement_plan_df, replacement_stub_df, source_artifact_df, summary), encoding="utf-8")
    return summary, replacement_plan_df, replacement_stub_df, source_artifact_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Build a public dataset accession replacement workflow.")
    parser.add_argument("--request", type=Path, default=DEFAULT_REPLACEMENT_REQUEST)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        summary, replacement_plan_df, replacement_stub_df, source_artifact_df, paths = build_public_dataset_replacement_workflow(
            request_path=args.request,
            output_dir=args.output_dir,
        )
    except Exception as exc:
        print(f"ERROR: Public dataset replacement workflow build failed: {exc}", file=sys.stderr)
        return 1

    print("Public dataset replacement workflow complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Replacement candidates: {summary['replacement_candidate_count']}")
    print(f"Ready real files: {summary['ready_replacement_file_count']}")
    print(f"Replacement manifest stubs: {summary['replacement_manifest_stub_count']}")
    print(f"Report: {paths['replacement_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

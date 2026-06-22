#!/usr/bin/env python3

import argparse
import html
import sys
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_SOURCE_REGISTRY = Path("configs/public_data_sources/public_data_source_registry.yaml")
DEFAULT_ACQUISITION_REQUEST = Path("configs/public_data_sources/multi_cancer_public_data_acquisition_request.yaml")
DEFAULT_OUTPUT_ROOT = Path("outputs/public_data_acquisition")


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


def ensure_dir(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def escape_html(value):
    if value is None:
        return ""
    return html.escape(str(value))


def dataframe_to_html_table(df, max_rows=100):
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


def normalize_sources(source_registry):
    sources = source_registry.get("sources", {})
    if not isinstance(sources, dict) or not sources:
        raise ValueError("Source registry must contain a non-empty sources mapping")
    rows = []
    for source_id, item in sources.items():
        if not isinstance(item, dict):
            item = {}
        rows.append(
            {
                "source_id": str(source_id),
                "display_name": str(item.get("display_name", source_id)),
                "source_type": str(item.get("source_type", "unknown")),
                "access_mode": str(item.get("access_mode", "unknown")),
                "status": str(item.get("status", "unknown")),
                "supported_modalities": ";".join([str(x) for x in item.get("supported_modalities", [])]) if isinstance(item.get("supported_modalities", []), list) else "",
                "suggested_atlases": ";".join([str(x) for x in item.get("suggested_atlases", [])]) if isinstance(item.get("suggested_atlases", []), list) else "",
                "identifier_examples": ";".join([str(x) for x in item.get("identifier_examples", [])]) if isinstance(item.get("identifier_examples", []), list) else "",
                "acquisition_notes": str(item.get("acquisition_notes", "")),
            }
        )
    return pd.DataFrame(rows)


def validate_requested_sources(request, source_inventory_df):
    requested = request.get("requested_sources", [])
    if not isinstance(requested, list) or not requested:
        raise ValueError("Acquisition request must contain a non-empty requested_sources list")
    available_sources = set(source_inventory_df["source_id"].astype(str))
    rows = []
    for index, item in enumerate(requested, start=1):
        if not isinstance(item, dict):
            raise ValueError("Each requested source entry must be a mapping")
        source_id = str(item.get("source_id", ""))
        if source_id not in available_sources:
            raise ValueError(f"Requested source_id is not in source registry: {source_id}")
        rows.append(
            {
                "acquisition_step": int(index),
                "source_id": source_id,
                "atlas_hint": str(item.get("atlas_hint", "")),
                "modality": str(item.get("modality", "")),
                "dataset_query": str(item.get("dataset_query", "")),
                "priority": int(item.get("priority", index)),
                "requires_user_exported_manifest": 1,
                "network_required_by_core_tests": 0,
                "planned_local_manifest_name": f"{str(item.get('atlas_hint', 'atlas'))}_{str(item.get('modality', 'modality'))}_public_data_manifest.yaml",
            }
        )
    return pd.DataFrame(rows).sort_values("priority").reset_index(drop=True)


def build_manifest_template(row, request):
    atlas_name = str(request.get("atlas_name", row.get("atlas_hint", "atlas")))
    modality = str(row["modality"])
    atlas_hint = str(row["atlas_hint"])
    source_id = str(row["source_id"])
    query = str(row["dataset_query"])
    return {
        "manifest_id": f"{atlas_hint}_{modality}_public_data_manifest",
        "atlas_name": atlas_hint,
        "modality": modality,
        "data_type": f"public_{modality}_matrix_or_manifest",
        "source_name": source_id,
        "source_query": query,
        "access_level": "public_or_user_exported_manifest",
        "input_files": [
            {
                "file_id": f"{modality}_matrix_or_manifest_placeholder",
                "path": f"data/public/{atlas_name}/{modality}/REPLACE_WITH_LOCAL_FILE.tsv",
                "file_format": "tsv",
                "matrix_orientation": "samples_by_features",
                "sample_id_column": "sample_id",
                "feature_id_type": "replace_with_modality_specific_feature_id_type",
            }
        ],
        "processing_plan": {
            "normalization": "replace_with_modality_pipeline_default",
            "missing_value_strategy": "replace_with_modality_pipeline_default",
            "batch_correction": "none_or_future",
            "feature_filtering": "replace_with_modality_pipeline_default",
            "max_missing_fraction": 0.5,
        },
        "agent_role": {
            "stage": "public_data_manifest_template",
            "purpose": "bridge public repository discovery to local feature-store execution",
        },
    }


def write_manifest_templates(acquisition_plan_df, request, output_dir):
    template_dir = ensure_dir(Path(output_dir) / "manifest_templates")
    rows = []
    for _, row in acquisition_plan_df.iterrows():
        template = build_manifest_template(row, request)
        template_path = template_dir / str(row["planned_local_manifest_name"])
        write_yaml(template_path, template)
        rows.append(
            {
                "source_id": row["source_id"],
                "modality": row["modality"],
                "atlas_hint": row["atlas_hint"],
                "manifest_template": str(template_path),
            }
        )
    return pd.DataFrame(rows)


def build_html_report(request, source_inventory_df, acquisition_plan_df, template_inventory_df):
    title = "Public Data Acquisition Plan"
    parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        f"<title>{escape_html(title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This report scaffolds the transition from synthetic/demo matrices toward real public-data-backed OpenMultiOmics runs.</p>",
        f"<p><strong>Request:</strong> {escape_html(request.get('request_id', ''))}</p>",
        f"<p><strong>Atlas:</strong> {escape_html(request.get('atlas_name', ''))}</p>",
        "<h2>Registered public data sources</h2>",
        dataframe_to_html_table(source_inventory_df),
        "<h2>Acquisition plan</h2>",
        dataframe_to_html_table(acquisition_plan_df),
        "<h2>Generated manifest templates</h2>",
        dataframe_to_html_table(template_inventory_df),
        "<h2>Recommended next steps</h2>",
        "<ul>",
        "<li>Export file manifests or processed matrices from the selected public repositories.</li>",
        "<li>Replace placeholder file paths in generated manifest templates with local downloaded files.</li>",
        "<li>Run modality feature-store processors on the real public-data manifests.</li>",
        "<li>Run the end-to-end demo runner on real feature stores.</li>",
        "</ul>",
        "</body>",
        "</html>",
    ]
    return "\n".join(parts)


def build_public_data_acquisition_plan(
    request_path=DEFAULT_ACQUISITION_REQUEST,
    source_registry_path=DEFAULT_SOURCE_REGISTRY,
    output_dir=None,
):
    request = load_yaml_mapping(request_path)
    source_registry = load_yaml_mapping(source_registry_path)
    source_inventory_df = normalize_sources(source_registry)
    acquisition_plan_df = validate_requested_sources(request, source_inventory_df)

    expected_outputs = request.get("expected_outputs", {})
    output_dir = ensure_dir(output_dir or expected_outputs.get("acquisition_plan_dir", DEFAULT_OUTPUT_ROOT / request.get("atlas_name", "public_data_demo")))

    template_inventory_df = write_manifest_templates(acquisition_plan_df, request, output_dir)

    paths = {
        "source_inventory": Path(output_dir) / "public_data_source_inventory.tsv",
        "acquisition_plan": Path(output_dir) / "public_data_acquisition_plan.tsv",
        "manifest_template_inventory": Path(output_dir) / "manifest_template_inventory.tsv",
        "acquisition_summary": Path(output_dir) / "public_data_acquisition_summary.yaml",
        "acquisition_report": Path(output_dir) / "public_data_acquisition_report.html",
    }

    source_inventory_df.to_csv(paths["source_inventory"], sep="\t", index=False)
    acquisition_plan_df.to_csv(paths["acquisition_plan"], sep="\t", index=False)
    template_inventory_df.to_csv(paths["manifest_template_inventory"], sep="\t", index=False)

    summary = {
        "request_id": str(request.get("request_id", "")),
        "atlas_name": str(request.get("atlas_name", "")),
        "source_registry": str(source_registry_path),
        "request_path": str(request_path),
        "registered_source_count": int(source_inventory_df.shape[0]),
        "requested_dataset_count": int(acquisition_plan_df.shape[0]),
        "manifest_template_count": int(template_inventory_df.shape[0]),
        "output_dir": str(output_dir),
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {
            "stage": "public_data_acquisition_planning",
            "purpose": "prepare reproducible public-data acquisition manifests for real-dataset OpenMultiOmics execution",
        },
    }

    write_yaml(paths["acquisition_summary"], summary)
    paths["acquisition_report"].write_text(
        build_html_report(request, source_inventory_df, acquisition_plan_df, template_inventory_df),
        encoding="utf-8",
    )

    return summary, source_inventory_df, acquisition_plan_df, template_inventory_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Build a public-data acquisition plan and manifest templates for OpenMultiOmics."
    )
    parser.add_argument("--request", type=Path, default=DEFAULT_ACQUISITION_REQUEST)
    parser.add_argument("--source-registry", type=Path, default=DEFAULT_SOURCE_REGISTRY)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        summary, source_inventory_df, acquisition_plan_df, template_inventory_df, paths = build_public_data_acquisition_plan(
            request_path=args.request,
            source_registry_path=args.source_registry,
            output_dir=args.output_dir,
        )
    except Exception as exc:
        print(f"ERROR: Public data acquisition plan build failed: {exc}", file=sys.stderr)
        return 1

    print("Public data acquisition plan complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Registered sources: {summary['registered_source_count']}")
    print(f"Requested datasets: {summary['requested_dataset_count']}")
    print(f"Manifest templates: {summary['manifest_template_count']}")
    print(f"Report: {paths['acquisition_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

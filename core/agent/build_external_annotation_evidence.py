#!/usr/bin/env python3

import argparse
import html
import sys
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_CONNECTOR_REGISTRY = Path("configs/external_annotation_connectors/external_annotation_connector_registry.yaml")
DEFAULT_LOCAL_ANNOTATION_SEED = Path("configs/external_annotation_connectors/local_external_annotation_seed.tsv")


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


def dataframe_to_html_table(df, max_rows=75):
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


def normalize_entity_id(value):
    return str(value).strip().upper()


def build_connector_inventory(connector_registry):
    connectors = connector_registry.get("connectors", {})
    if not isinstance(connectors, dict) or not connectors:
        raise ValueError("Connector registry must contain a non-empty connectors mapping")
    rows = []
    for connector_id, item in connectors.items():
        if not isinstance(item, dict):
            item = {}
        rows.append(
            {
                "connector_id": str(connector_id),
                "display_name": str(item.get("display_name", connector_id)),
                "connector_type": str(item.get("connector_type", "unknown")),
                "status": str(item.get("status", "unknown")),
                "supported_entity_types": ";".join([str(x) for x in item.get("supported_entity_types", [])]) if isinstance(item.get("supported_entity_types", []), list) else "",
                "description": str(item.get("description", "")),
            }
        )
    return pd.DataFrame(rows)


def build_external_annotation_evidence_table(feature_evidence_df, local_annotation_seed_df):
    feature_df = feature_evidence_df.copy()
    seed_df = local_annotation_seed_df.copy()
    if "pathway_ready_entity_id" not in feature_df.columns:
        raise ValueError("feature_evidence_table must contain pathway_ready_entity_id")
    if "pathway_ready_entity_id" not in seed_df.columns:
        raise ValueError("local annotation seed must contain pathway_ready_entity_id")

    feature_df["entity_id_normalized"] = feature_df["pathway_ready_entity_id"].map(normalize_entity_id)
    seed_df["entity_id_normalized"] = seed_df["pathway_ready_entity_id"].map(normalize_entity_id)

    merged = feature_df.merge(seed_df, on="entity_id_normalized", how="left", suffixes=("", "_external"))
    merged["external_annotation_status"] = merged["external_term_id"].apply(
        lambda value: "mapped_to_local_external_seed" if pd.notna(value) and str(value).strip() else "pending_external_connector_mapping"
    )
    merged["combined_evidence_score"] = merged.apply(
        lambda row: float(row.get("abs_PC1_loading", 0.0)) * float(row.get("evidence_strength", 0.0) if pd.notna(row.get("evidence_strength", 0.0)) else 0.0),
        axis=1,
    )

    keep_cols = [
        "rank",
        "feature_id",
        "modality",
        "raw_feature_id",
        "pathway_ready_entity_id",
        "pathway_ready_program",
        "pathway_ready_evidence_source",
        "external_resource_id",
        "external_resource_name",
        "external_term_id",
        "external_term_name",
        "evidence_type",
        "evidence_strength",
        "combined_evidence_score",
        "external_annotation_status",
    ]
    keep_cols = [col for col in keep_cols if col in merged.columns]
    return merged.loc[:, keep_cols].copy()


def build_external_term_summary(external_evidence_df):
    if external_evidence_df.empty:
        return pd.DataFrame(columns=["external_term_id", "external_term_name", "feature_count", "mean_combined_evidence_score"])
    mapped = external_evidence_df.loc[external_evidence_df["external_annotation_status"] == "mapped_to_local_external_seed"].copy()
    if mapped.empty:
        return pd.DataFrame(columns=["external_term_id", "external_term_name", "feature_count", "mean_combined_evidence_score"])
    out = (
        mapped.groupby(["external_resource_id", "external_resource_name", "external_term_id", "external_term_name"], dropna=False)
        .agg(
            feature_count=("feature_id", "count"),
            mean_combined_evidence_score=("combined_evidence_score", "mean"),
            max_combined_evidence_score=("combined_evidence_score", "max"),
        )
        .reset_index()
    )
    return out.sort_values("mean_combined_evidence_score", ascending=False).reset_index(drop=True)


def build_connector_readiness_summary(connector_inventory_df, external_evidence_df):
    mapped_count = int((external_evidence_df["external_annotation_status"] == "mapped_to_local_external_seed").sum()) if not external_evidence_df.empty else 0
    total_count = int(external_evidence_df.shape[0])
    return pd.DataFrame(
        [
            {"metric": "connectors_registered", "value": int(connector_inventory_df.shape[0])},
            {"metric": "external_evidence_rows", "value": total_count},
            {"metric": "mapped_external_evidence_rows", "value": mapped_count},
            {"metric": "pending_external_connector_rows", "value": int(total_count - mapped_count)},
        ]
    )


def build_html_report(external_evidence_df, external_term_summary_df, connector_inventory_df, readiness_df, summary):
    title = "External Annotation Evidence Report"
    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        f"<title>{escape_html(title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This report provides the connector-ready scaffold for external biological annotation resources.</p>",
        "<p><strong>Interpretation status:</strong> local external seed mapping; future steps should connect real curated resources.</p>",
        f"<p><strong>Atlas:</strong> {escape_html(summary.get('atlas_name', ''))}</p>",
        "<h2>Connector readiness summary</h2>",
        dataframe_to_html_table(readiness_df),
        "<h2>External term summary</h2>",
        dataframe_to_html_table(external_term_summary_df),
        "<h2>External evidence table</h2>",
        dataframe_to_html_table(external_evidence_df),
        "<h2>Connector registry inventory</h2>",
        dataframe_to_html_table(connector_inventory_df),
        "</body>",
        "</html>",
    ]
    return "\n".join(html_parts)


def build_external_annotation_evidence(
    pathway_ready_evidence_dir,
    connector_registry_path=DEFAULT_CONNECTOR_REGISTRY,
    local_annotation_seed_path=DEFAULT_LOCAL_ANNOTATION_SEED,
    output_dir=None,
):
    pathway_ready_evidence_dir = Path(pathway_ready_evidence_dir)
    feature_evidence_path = pathway_ready_evidence_dir / "feature_evidence_table.tsv"
    pathway_summary_path = pathway_ready_evidence_dir / "pathway_ready_evidence_summary.yaml"

    feature_evidence_df = read_table(feature_evidence_path)
    pathway_summary = load_yaml_mapping(pathway_summary_path)
    connector_inventory_df = build_connector_inventory(load_yaml_mapping(connector_registry_path))
    local_annotation_seed_df = read_table(local_annotation_seed_path)

    external_evidence_df = build_external_annotation_evidence_table(feature_evidence_df, local_annotation_seed_df)
    external_term_summary_df = build_external_term_summary(external_evidence_df)
    readiness_df = build_connector_readiness_summary(connector_inventory_df, external_evidence_df)

    output_dir = ensure_dir(output_dir or pathway_ready_evidence_dir / "external_annotation_evidence")
    paths = {
        "external_annotation_evidence": output_dir / "external_annotation_evidence.tsv",
        "external_term_summary": output_dir / "external_term_summary.tsv",
        "connector_inventory": output_dir / "connector_inventory.tsv",
        "connector_readiness_summary": output_dir / "connector_readiness_summary.tsv",
        "external_annotation_summary": output_dir / "external_annotation_summary.yaml",
        "external_annotation_report": output_dir / "external_annotation_report.html",
    }

    external_evidence_df.to_csv(paths["external_annotation_evidence"], sep="\t", index=False)
    external_term_summary_df.to_csv(paths["external_term_summary"], sep="\t", index=False)
    connector_inventory_df.to_csv(paths["connector_inventory"], sep="\t", index=False)
    readiness_df.to_csv(paths["connector_readiness_summary"], sep="\t", index=False)

    mapped_count = int((external_evidence_df["external_annotation_status"] == "mapped_to_local_external_seed").sum()) if not external_evidence_df.empty else 0
    summary = {
        "external_annotation_id": f"{pathway_summary.get('atlas_name', 'atlas')}_external_annotation_evidence",
        "atlas_name": str(pathway_summary.get("atlas_name", "")),
        "pathway_ready_evidence_dir": str(pathway_ready_evidence_dir),
        "connector_registry": str(connector_registry_path),
        "local_annotation_seed": str(local_annotation_seed_path),
        "external_evidence_rows": int(external_evidence_df.shape[0]),
        "mapped_external_evidence_rows": mapped_count,
        "external_term_count": int(external_term_summary_df.shape[0]),
        "interpretation_status": "external_annotation_connector_scaffold_requires_real_resource_binding",
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {
            "stage": "external_annotation_connector_scaffold",
            "purpose": "prepare pathway-ready evidence for future connection to curated external annotation resources",
        },
    }

    write_yaml(paths["external_annotation_summary"], summary)
    report_html = build_html_report(external_evidence_df, external_term_summary_df, connector_inventory_df, readiness_df, summary)
    paths["external_annotation_report"].write_text(report_html, encoding="utf-8")

    return summary, external_evidence_df, external_term_summary_df, connector_inventory_df, readiness_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Build external annotation evidence scaffold from pathway-ready evidence outputs."
    )
    parser.add_argument("--pathway-ready-evidence-dir", required=True, type=Path)
    parser.add_argument("--connector-registry", type=Path, default=DEFAULT_CONNECTOR_REGISTRY)
    parser.add_argument("--local-annotation-seed", type=Path, default=DEFAULT_LOCAL_ANNOTATION_SEED)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        summary, _, _, _, _, paths = build_external_annotation_evidence(
            pathway_ready_evidence_dir=args.pathway_ready_evidence_dir,
            connector_registry_path=args.connector_registry,
            local_annotation_seed_path=args.local_annotation_seed,
            output_dir=args.output_dir,
        )
    except Exception as exc:
        print(f"ERROR: External annotation evidence build failed: {exc}", file=sys.stderr)
        return 1

    print("External annotation evidence scaffold complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"External evidence rows: {summary['external_evidence_rows']}")
    print(f"Mapped external evidence rows: {summary['mapped_external_evidence_rows']}")
    print(f"Report: {paths['external_annotation_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

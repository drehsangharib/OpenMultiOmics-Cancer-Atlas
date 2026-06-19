#!/usr/bin/env python3

import argparse
import html
import sys
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_RESOURCE_REGISTRY = Path("configs/annotation_resources/annotation_resource_registry.yaml")
DEFAULT_SEED_ANNOTATION_MAP = Path("configs/annotation_resources/seed_feature_annotation_map.tsv")


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


def build_resource_inventory(resource_registry):
    resources = resource_registry.get("resources", {})
    if not isinstance(resources, dict) or not resources:
        raise ValueError("Annotation resource registry must contain a non-empty resources mapping")
    rows = []
    for resource_id, item in resources.items():
        if not isinstance(item, dict):
            item = {}
        supported = item.get("supported_modalities", [])
        if not isinstance(supported, list):
            supported = []
        rows.append(
            {
                "resource_id": str(resource_id),
                "display_name": str(item.get("display_name", resource_id)),
                "entity_type": str(item.get("entity_type", "unknown")),
                "resource_type": str(item.get("resource_type", "unknown")),
                "supported_modalities": ";".join([str(x) for x in supported]),
                "description": str(item.get("description", "")),
            }
        )
    return pd.DataFrame(rows)


def build_feature_evidence_table(program_annotated_features_df, seed_annotation_df):
    features = program_annotated_features_df.copy()
    seeds = seed_annotation_df.copy()
    if "raw_feature_id" not in features.columns:
        raise ValueError("program_annotated_features table must contain raw_feature_id")
    if "entity_id" not in seeds.columns:
        raise ValueError("seed annotation map must contain entity_id")
    features["entity_id_normalized"] = features["raw_feature_id"].map(normalize_entity_id)
    seeds["entity_id_normalized"] = seeds["entity_id"].map(normalize_entity_id)
    merged = features.merge(seeds, on="entity_id_normalized", how="left", suffixes=("", "_seed"))
    merged["evidence_status"] = merged["candidate_program"].apply(
        lambda value: "mapped_to_seed_scaffold" if pd.notna(value) and str(value).strip() else "unmapped_requires_external_annotation"
    )
    merged["pathway_ready_entity_id"] = merged["canonical_label"].fillna(merged["raw_feature_id"])
    merged["pathway_ready_program"] = merged["candidate_program"].fillna(merged["program_id"])
    merged["pathway_ready_evidence_label"] = merged["evidence_label"].fillna("No local scaffold evidence yet")
    merged["pathway_ready_evidence_source"] = merged["evidence_source"].fillna("unmapped")
    keep_cols = [
        "rank", "feature_id", "modality", "raw_feature_id", "program_id",
        "program_display_name", "interpretation_layer", "abs_PC1_loading",
        "pathway_ready_entity_id", "pathway_ready_program",
        "pathway_ready_evidence_label", "pathway_ready_evidence_source", "evidence_status",
    ]
    keep_cols = [col for col in keep_cols if col in merged.columns]
    return merged.loc[:, keep_cols].copy()


def build_program_evidence_summary(feature_evidence_df):
    if feature_evidence_df.empty:
        return pd.DataFrame(columns=["pathway_ready_program", "feature_count", "mapped_feature_count", "mean_abs_PC1_loading", "max_abs_PC1_loading", "mapping_fraction"])
    out = (
        feature_evidence_df.groupby("pathway_ready_program", dropna=False)
        .agg(
            feature_count=("feature_id", "count"),
            mapped_feature_count=("evidence_status", lambda values: int((values == "mapped_to_seed_scaffold").sum())),
            mean_abs_PC1_loading=("abs_PC1_loading", "mean"),
            max_abs_PC1_loading=("abs_PC1_loading", "max"),
        )
        .reset_index()
    )
    out["mapping_fraction"] = out["mapped_feature_count"] / out["feature_count"].replace(0, 1)
    return out.sort_values(["mean_abs_PC1_loading", "mapping_fraction"], ascending=False).reset_index(drop=True)


def build_pathway_prioritization_table(program_evidence_summary_df):
    if program_evidence_summary_df.empty:
        return pd.DataFrame(columns=["priority_rank", "pathway_ready_program", "priority_score", "priority_rationale"])
    out = program_evidence_summary_df.copy()
    out["priority_score"] = out["mean_abs_PC1_loading"].astype(float) * (1.0 + out["mapping_fraction"].astype(float)) * out["feature_count"].astype(float)
    out = out.sort_values("priority_score", ascending=False).reset_index(drop=True)
    out.insert(0, "priority_rank", range(1, len(out) + 1))
    out["priority_rationale"] = out.apply(
        lambda row: f"{row['pathway_ready_program']} has {int(row['feature_count'])} supporting features, mapping fraction {float(row['mapping_fraction']):.2f}, and mean absolute PC1 loading {float(row['mean_abs_PC1_loading']):.4f}.",
        axis=1,
    )
    return out


def build_html_report(feature_evidence_df, program_summary_df, priority_df, resource_inventory_df, summary):
    title = "Pathway-Ready Evidence Layer Report"
    html_parts = [
        "<!DOCTYPE html>", "<html>", "<head>", "<meta charset='utf-8'>",
        f"<title>{escape_html(title)}</title>", "</head>", "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This report converts program-annotated features into a pathway-ready evidence scaffold.</p>",
        "<p><strong>Interpretation status:</strong> local seed scaffold; external pathway database validation is the next layer.</p>",
        f"<p><strong>Atlas:</strong> {escape_html(summary.get('atlas_name', ''))}</p>",
        f"<p><strong>Feature evidence rows:</strong> {summary.get('feature_evidence_count', 0)}</p>",
        f"<p><strong>Mapped feature count:</strong> {summary.get('mapped_feature_count', 0)}</p>",
        "<h2>Pathway/program prioritization</h2>", dataframe_to_html_table(priority_df),
        "<h2>Program evidence summary</h2>", dataframe_to_html_table(program_summary_df),
        "<h2>Feature evidence table</h2>", dataframe_to_html_table(feature_evidence_df),
        "<h2>Annotation resources</h2>", dataframe_to_html_table(resource_inventory_df),
        "</body>", "</html>",
    ]
    return "\n".join(html_parts)


def build_pathway_ready_evidence_layer(program_annotation_dir, resource_registry_path=DEFAULT_RESOURCE_REGISTRY, seed_annotation_map_path=DEFAULT_SEED_ANNOTATION_MAP, output_dir=None):
    program_annotation_dir = Path(program_annotation_dir)
    program_annotated_features_path = program_annotation_dir / "program_annotated_features.tsv"
    program_annotation_summary_path = program_annotation_dir / "program_annotation_summary.yaml"
    program_annotated_features_df = read_table(program_annotated_features_path)
    program_annotation_summary = load_yaml_mapping(program_annotation_summary_path)
    resource_inventory_df = build_resource_inventory(load_yaml_mapping(resource_registry_path))
    seed_annotation_df = read_table(seed_annotation_map_path)
    feature_evidence_df = build_feature_evidence_table(program_annotated_features_df, seed_annotation_df)
    program_summary_df = build_program_evidence_summary(feature_evidence_df)
    priority_df = build_pathway_prioritization_table(program_summary_df)
    output_dir = ensure_dir(output_dir or program_annotation_dir / "pathway_ready_evidence")
    paths = {
        "feature_evidence_table": output_dir / "feature_evidence_table.tsv",
        "program_evidence_summary": output_dir / "program_evidence_summary.tsv",
        "pathway_prioritization_table": output_dir / "pathway_prioritization_table.tsv",
        "annotation_resource_inventory": output_dir / "annotation_resource_inventory.tsv",
        "pathway_ready_evidence_summary": output_dir / "pathway_ready_evidence_summary.yaml",
        "pathway_ready_evidence_report": output_dir / "pathway_ready_evidence_report.html",
    }
    feature_evidence_df.to_csv(paths["feature_evidence_table"], sep="\t", index=False)
    program_summary_df.to_csv(paths["program_evidence_summary"], sep="\t", index=False)
    priority_df.to_csv(paths["pathway_prioritization_table"], sep="\t", index=False)
    resource_inventory_df.to_csv(paths["annotation_resource_inventory"], sep="\t", index=False)
    mapped_feature_count = int((feature_evidence_df["evidence_status"] == "mapped_to_seed_scaffold").sum())
    summary = {
        "pathway_ready_evidence_id": f"{program_annotation_summary.get('atlas_name', 'atlas')}_pathway_ready_evidence_layer",
        "atlas_name": str(program_annotation_summary.get("atlas_name", "")),
        "program_annotation_dir": str(program_annotation_dir),
        "resource_registry": str(resource_registry_path),
        "seed_annotation_map": str(seed_annotation_map_path),
        "feature_evidence_count": int(feature_evidence_df.shape[0]),
        "mapped_feature_count": mapped_feature_count,
        "unmapped_feature_count": int(feature_evidence_df.shape[0] - mapped_feature_count),
        "program_evidence_count": int(program_summary_df.shape[0]),
        "interpretation_status": "pathway_ready_seed_scaffold_requires_external_validation",
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {
            "stage": "pathway_ready_evidence_preparation",
            "purpose": "prepare program-annotated feature evidence for downstream pathway and ontology validation",
        },
    }
    write_yaml(paths["pathway_ready_evidence_summary"], summary)
    report_html = build_html_report(feature_evidence_df, program_summary_df, priority_df, resource_inventory_df, summary)
    paths["pathway_ready_evidence_report"].write_text(report_html, encoding="utf-8")
    return summary, feature_evidence_df, program_summary_df, priority_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Build a pathway-ready evidence layer from program annotation outputs.")
    parser.add_argument("--program-annotation-dir", required=True, type=Path)
    parser.add_argument("--resource-registry", type=Path, default=DEFAULT_RESOURCE_REGISTRY)
    parser.add_argument("--seed-annotation-map", type=Path, default=DEFAULT_SEED_ANNOTATION_MAP)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        summary, _, _, _, paths = build_pathway_ready_evidence_layer(
            program_annotation_dir=args.program_annotation_dir,
            resource_registry_path=args.resource_registry,
            seed_annotation_map_path=args.seed_annotation_map,
            output_dir=args.output_dir,
        )
    except Exception as exc:
        print(f"ERROR: Pathway-ready evidence layer build failed: {exc}", file=sys.stderr)
        return 1
    print("Pathway-ready evidence layer complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Feature evidence rows: {summary['feature_evidence_count']}")
    print(f"Mapped features: {summary['mapped_feature_count']}")
    print(f"Report: {paths['pathway_ready_evidence_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

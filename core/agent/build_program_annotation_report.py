#!/usr/bin/env python3

import argparse
import html
import sys
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_PROGRAM_REGISTRY = Path("configs/biological_programs/biological_program_registry.yaml")


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


def normalize_program_registry(raw_registry):
    programs = raw_registry.get("programs", {})
    if not isinstance(programs, dict):
        raise ValueError("Program registry must contain a 'programs' mapping")
    normalized = {}
    for program_id, item in programs.items():
        if not isinstance(item, dict):
            item = {}
        normalized[str(program_id)] = {
            "program_id": str(program_id),
            "display_name": str(item.get("display_name", program_id)),
            "modality": str(item.get("modality", "unknown")),
            "interpretation_layer": str(item.get("interpretation_layer", "unclassified")),
            "description": str(item.get("description", "")),
            "seed_keywords": item.get("seed_keywords", []) if isinstance(item.get("seed_keywords", []), list) else [],
        }
    return normalized


def annotate_feature_programs(ranked_feature_annotations_df, program_registry):
    rows = []
    for _, row in ranked_feature_annotations_df.iterrows():
        group = str(row.get("candidate_interpretation_group", "unknown_state_signal"))
        program = program_registry.get(group, {
            "program_id": group,
            "display_name": group,
            "modality": str(row.get("modality", "unknown")),
            "interpretation_layer": "unclassified",
            "description": "No curated scaffold entry available yet.",
            "seed_keywords": [],
        })
        rows.append(
            {
                "rank": int(row.get("rank", len(rows) + 1)),
                "feature_id": str(row.get("feature_id", "")),
                "modality": str(row.get("modality", "")),
                "raw_feature_id": str(row.get("raw_feature_id", "")),
                "candidate_interpretation_group": group,
                "program_id": program["program_id"],
                "program_display_name": program["display_name"],
                "interpretation_layer": program["interpretation_layer"],
                "program_description": program["description"],
                "seed_keywords": ";".join([str(x) for x in program.get("seed_keywords", [])]),
                "abs_PC1_loading": float(row.get("abs_PC1_loading", 0.0)),
                "interpretation_status": "program_annotation_scaffold_requires_validation",
            }
        )
    return pd.DataFrame(rows)


def build_program_level_summary(program_annotations_df):
    if program_annotations_df.empty:
        return pd.DataFrame(columns=["program_id", "program_display_name", "modality", "feature_count", "mean_abs_PC1_loading", "max_abs_PC1_loading"])
    return (
        program_annotations_df.groupby(["program_id", "program_display_name", "modality", "interpretation_layer"], dropna=False)
        .agg(
            feature_count=("feature_id", "count"),
            mean_abs_PC1_loading=("abs_PC1_loading", "mean"),
            max_abs_PC1_loading=("abs_PC1_loading", "max"),
        )
        .reset_index()
        .sort_values("mean_abs_PC1_loading", ascending=False)
        .reset_index(drop=True)
    )


def build_interpretation_priority_table(program_summary_df):
    if program_summary_df.empty:
        return pd.DataFrame(columns=["priority_rank", "program_id", "priority_score", "priority_rationale"])
    out = program_summary_df.copy()
    out["priority_score"] = out["mean_abs_PC1_loading"].astype(float) * out["feature_count"].astype(float)
    out = out.sort_values("priority_score", ascending=False).reset_index(drop=True)
    out.insert(0, "priority_rank", range(1, len(out) + 1))
    out["priority_rationale"] = out.apply(
        lambda row: f"{row['program_display_name']} has {int(row['feature_count'])} top-ranked features and mean absolute PC1 loading {float(row['mean_abs_PC1_loading']):.4f}.",
        axis=1,
    )
    return out


def build_html_report(program_annotations_df, program_summary_df, priority_df, summary):
    title = "Program Annotation Report"
    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        f"<title>{escape_html(title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This report maps biological insight seed features onto a curated program annotation scaffold.</p>",
        "<p><strong>Interpretation status:</strong> scaffold-level annotation; requires validation against curated pathway and ontology resources.</p>",
        f"<p><strong>Atlas:</strong> {escape_html(summary.get('atlas_name', ''))}</p>",
        f"<p><strong>Annotated features:</strong> {summary.get('annotated_feature_count', 0)}</p>",
        f"<p><strong>Program count:</strong> {summary.get('program_count', 0)}</p>",
        "<h2>Interpretation priority table</h2>",
        dataframe_to_html_table(priority_df),
        "<h2>Program-level summary</h2>",
        dataframe_to_html_table(program_summary_df),
        "<h2>Program-annotated ranked features</h2>",
        dataframe_to_html_table(program_annotations_df),
        "</body>",
        "</html>",
    ]
    return "\n".join(html_parts)


def build_program_annotation_report(
    biological_insight_seed_dir,
    program_registry_path=DEFAULT_PROGRAM_REGISTRY,
    output_dir=None,
):
    biological_insight_seed_dir = Path(biological_insight_seed_dir)
    ranked_feature_annotations_path = biological_insight_seed_dir / "ranked_feature_annotations.tsv"
    insight_summary_path = biological_insight_seed_dir / "biological_insight_seed_summary.yaml"

    ranked_feature_annotations_df = read_table(ranked_feature_annotations_path)
    insight_summary = load_yaml_mapping(insight_summary_path)
    registry = normalize_program_registry(load_yaml_mapping(program_registry_path))

    program_annotations_df = annotate_feature_programs(ranked_feature_annotations_df, registry)
    program_summary_df = build_program_level_summary(program_annotations_df)
    priority_df = build_interpretation_priority_table(program_summary_df)

    output_dir = ensure_dir(output_dir or biological_insight_seed_dir / "program_annotation")
    paths = {
        "program_annotated_features": output_dir / "program_annotated_features.tsv",
        "program_level_summary": output_dir / "program_level_summary.tsv",
        "interpretation_priority_table": output_dir / "interpretation_priority_table.tsv",
        "program_annotation_summary": output_dir / "program_annotation_summary.yaml",
        "program_annotation_report": output_dir / "program_annotation_report.html",
    }

    program_annotations_df.to_csv(paths["program_annotated_features"], sep="\t", index=False)
    program_summary_df.to_csv(paths["program_level_summary"], sep="\t", index=False)
    priority_df.to_csv(paths["interpretation_priority_table"], sep="\t", index=False)

    summary = {
        "program_annotation_id": f"{insight_summary.get('atlas_name', 'atlas')}_program_annotation_report",
        "atlas_name": str(insight_summary.get("atlas_name", "")),
        "biological_insight_seed_dir": str(biological_insight_seed_dir),
        "program_registry": str(program_registry_path),
        "annotated_feature_count": int(program_annotations_df.shape[0]),
        "program_count": int(program_summary_df.shape[0]),
        "interpretation_priority_count": int(priority_df.shape[0]),
        "interpretation_status": "program_scaffold_requires_validation",
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {
            "stage": "program_annotation_scaffold",
            "purpose": "map biological insight seed features and themes to a curated program scaffold for downstream biological interpretation",
        },
    }

    write_yaml(paths["program_annotation_summary"], summary)
    report_html = build_html_report(program_annotations_df, program_summary_df, priority_df, summary)
    paths["program_annotation_report"].write_text(report_html, encoding="utf-8")

    return summary, program_annotations_df, program_summary_df, priority_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Build a curated biological program annotation scaffold report from biological insight seed outputs."
    )
    parser.add_argument("--biological-insight-seed-dir", required=True, type=Path)
    parser.add_argument("--program-registry", type=Path, default=DEFAULT_PROGRAM_REGISTRY)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        summary, program_annotations_df, program_summary_df, priority_df, paths = build_program_annotation_report(
            biological_insight_seed_dir=args.biological_insight_seed_dir,
            program_registry_path=args.program_registry,
            output_dir=args.output_dir,
        )
    except Exception as exc:
        print(f"ERROR: Program annotation report build failed: {exc}", file=sys.stderr)
        return 1

    print("Program annotation report complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Annotated features: {summary['annotated_feature_count']}")
    print(f"Programs: {summary['program_count']}")
    print(f"Report: {paths['program_annotation_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

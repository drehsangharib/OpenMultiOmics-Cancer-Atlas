#!/usr/bin/env python3

import argparse
import html
import sys
from pathlib import Path

import pandas as pd
import yaml


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


def dataframe_to_html_table(df, max_rows=50):
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


def parse_feature_id(feature_id):
    text = str(feature_id)
    if "__" in text:
        modality, raw_feature_id = text.split("__", 1)
    else:
        modality, raw_feature_id = "unknown", text
    return modality, raw_feature_id


def infer_feature_family(modality, raw_feature_id):
    raw = str(raw_feature_id).upper()
    modality = str(modality)

    if modality == "transcriptomics":
        return "gene_expression_feature"
    if modality == "proteomics":
        return "protein_abundance_feature"
    if modality == "epigenome":
        if raw.startswith("CG"):
            return "dna_methylation_cpg_feature"
        return "epigenomic_feature"
    if modality == "metabolomics":
        return "metabolite_abundance_feature"
    return "unclassified_feature"


def infer_interpretation_group(modality):
    mapping = {
        "transcriptomics": "expression_state_signal",
        "proteomics": "protein_abundance_signal",
        "epigenome": "epigenetic_state_signal",
        "metabolomics": "metabolic_state_signal",
    }
    return mapping.get(str(modality), "unknown_state_signal")


def annotate_ranked_features(feature_rankings_df):
    if feature_rankings_df.empty:
        return pd.DataFrame(
            columns=[
                "rank",
                "feature_id",
                "modality",
                "raw_feature_id",
                "feature_family",
                "candidate_interpretation_group",
                "abs_PC1_loading",
                "PC1_loading",
            ]
        )

    rows = []
    for _, row in feature_rankings_df.iterrows():
        modality, raw_feature_id = parse_feature_id(row.get("feature_id", ""))
        rows.append(
            {
                "rank": int(row.get("rank", len(rows) + 1)),
                "feature_id": str(row.get("feature_id", "")),
                "modality": modality,
                "raw_feature_id": raw_feature_id,
                "feature_family": infer_feature_family(modality, raw_feature_id),
                "candidate_interpretation_group": infer_interpretation_group(modality),
                "abs_PC1_loading": float(row.get("abs_PC1_loading", 0.0)),
                "PC1_loading": float(row.get("PC1_loading", 0.0)),
            }
        )

    return pd.DataFrame(rows)


def build_modality_program_summary(annotated_features_df, modality_block_summary_df):
    if annotated_features_df.empty:
        return pd.DataFrame(
            columns=[
                "modality",
                "top_ranked_feature_count",
                "dominant_interpretation_group",
                "mean_abs_PC1_loading_top_features",
                "block_mean_abs_PC1_loading",
                "block_feature_count",
            ]
        )

    grouped = (
        annotated_features_df.groupby("modality")
        .agg(
            top_ranked_feature_count=("feature_id", "count"),
            mean_abs_PC1_loading_top_features=("abs_PC1_loading", "mean"),
        )
        .reset_index()
    )

    dominant_groups = []
    for modality, sub in annotated_features_df.groupby("modality"):
        counts = sub["candidate_interpretation_group"].value_counts()
        dominant_groups.append(
            {
                "modality": modality,
                "dominant_interpretation_group": counts.index[0] if not counts.empty else "unknown_state_signal",
            }
        )
    dominant_df = pd.DataFrame(dominant_groups)
    out = grouped.merge(dominant_df, on="modality", how="left")

    if not modality_block_summary_df.empty and "modality" in modality_block_summary_df.columns:
        block_cols = [
            col
            for col in ["modality", "mean_abs_PC1_loading", "feature_count", "max_abs_PC1_loading"]
            if col in modality_block_summary_df.columns
        ]
        block_df = modality_block_summary_df.loc[:, block_cols].copy()
        block_df = block_df.rename(
            columns={
                "mean_abs_PC1_loading": "block_mean_abs_PC1_loading",
                "feature_count": "block_feature_count",
                "max_abs_PC1_loading": "block_max_abs_PC1_loading",
            }
        )
        out = out.merge(block_df, on="modality", how="left")

    for column in ["block_mean_abs_PC1_loading", "block_feature_count", "block_max_abs_PC1_loading"]:
        if column not in out.columns:
            out[column] = 0

    return out.sort_values("mean_abs_PC1_loading_top_features", ascending=False).reset_index(drop=True)


def build_candidate_biological_themes(annotated_features_df, modality_program_summary_df):
    theme_map = {
        "transcriptomics": (
            "expression_state_signal",
            "Transcriptomic features dominate parts of the baseline structure and may reflect gene-expression state differences.",
        ),
        "proteomics": (
            "protein_abundance_signal",
            "Proteomic features contribute protein-abundance state information that may complement transcriptomic signals.",
        ),
        "epigenome": (
            "epigenetic_state_signal",
            "Epigenomic features may reflect DNA methylation or chromatin-associated state differences.",
        ),
        "metabolomics": (
            "metabolic_state_signal",
            "Metabolomic features may reflect metabolic state differences linked to sample grouping or biological programs.",
        ),
    }

    rows = []
    observed_modalities = set(modality_program_summary_df["modality"].astype(str)) if not modality_program_summary_df.empty else set()

    for modality in sorted(observed_modalities):
        theme_name, description = theme_map.get(
            modality,
            (
                "unknown_state_signal",
                "Unclassified feature block may contain signal requiring downstream biological annotation.",
            ),
        )
        sub = annotated_features_df.loc[annotated_features_df["modality"] == modality]
        top_features = ";".join(sub.head(5)["raw_feature_id"].astype(str).tolist()) if not sub.empty else ""
        mean_loading = float(sub["abs_PC1_loading"].mean()) if not sub.empty else 0.0
        rows.append(
            {
                "theme_name": theme_name,
                "modality": modality,
                "candidate_description": description,
                "top_feature_examples": top_features,
                "supporting_top_feature_count": int(sub.shape[0]),
                "mean_abs_PC1_loading_top_features": mean_loading,
                "interpretation_status": "seed_hypothesis_requires_validation",
            }
        )

    if len(observed_modalities) >= 2:
        rows.append(
            {
                "theme_name": "cross_modality_state_signal",
                "modality": "multiomics",
                "candidate_description": "Multiple modality blocks contribute to the integrated structure, suggesting a candidate cross-modality biological-state signal.",
                "top_feature_examples": "",
                "supporting_top_feature_count": int(annotated_features_df.shape[0]),
                "mean_abs_PC1_loading_top_features": float(annotated_features_df["abs_PC1_loading"].mean()) if not annotated_features_df.empty else 0.0,
                "interpretation_status": "seed_hypothesis_requires_validation",
            }
        )

    return pd.DataFrame(rows).sort_values("mean_abs_PC1_loading_top_features", ascending=False).reset_index(drop=True)


def build_html_report(context, cluster_summary_df, annotated_features_df, modality_program_summary_df, candidate_themes_df, summary):
    title = "Biological Insight Seed Report"
    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        f"<title>{escape_html(title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This report converts baseline AI multi-omics analysis outputs into seed biological interpretation candidates.</p>",
        "<p><strong>Interpretation status:</strong> These are scaffolded hypotheses requiring downstream biological validation.</p>",
        f"<p><strong>Atlas:</strong> {escape_html(context.get('atlas_name', ''))}</p>",
        f"<p><strong>Top annotated features:</strong> {summary['top_annotated_feature_count']}</p>",
        f"<p><strong>Candidate themes:</strong> {summary['candidate_theme_count']}</p>",
        "<h2>Cluster summary</h2>",
        dataframe_to_html_table(cluster_summary_df),
        "<h2>Candidate biological themes</h2>",
        dataframe_to_html_table(candidate_themes_df),
        "<h2>Modality program summary</h2>",
        dataframe_to_html_table(modality_program_summary_df),
        "<h2>Ranked feature annotations</h2>",
        dataframe_to_html_table(annotated_features_df, max_rows=50),
        "<h2>Recommended next AI-agent actions</h2>",
        "<ul>",
        "<li>Validate top-ranked features against curated pathway and gene-set databases.</li>",
        "<li>Map epigenomic probes and metabolite identifiers to biological programs.</li>",
        "<li>Run cluster-level differential feature analysis after larger real cohorts are connected.</li>",
        "<li>Generate pathway and mechanism-level summaries from validated annotations.</li>",
        "</ul>",
        "</body>",
        "</html>",
    ]
    return "\n".join(html_parts)


def build_biological_insight_seed(
    analysis_context_path,
    baseline_analysis_dir,
    output_dir=None,
    top_n_features=50,
):
    analysis_context_path = Path(analysis_context_path)
    baseline_analysis_dir = Path(baseline_analysis_dir)
    context = load_yaml_mapping(analysis_context_path)

    feature_rankings_path = baseline_analysis_dir / "feature_rankings.tsv"
    modality_block_summary_path = baseline_analysis_dir / "modality_block_summary.tsv"
    cluster_summary_path = baseline_analysis_dir / "cluster_summary.tsv"

    feature_rankings_df = read_table(feature_rankings_path)
    modality_block_summary_df = read_table(modality_block_summary_path)
    cluster_summary_df = read_table(cluster_summary_path)

    selected_rankings_df = feature_rankings_df.head(top_n_features).copy()
    annotated_features_df = annotate_ranked_features(selected_rankings_df)
    modality_program_summary_df = build_modality_program_summary(annotated_features_df, modality_block_summary_df)
    candidate_themes_df = build_candidate_biological_themes(annotated_features_df, modality_program_summary_df)

    output_dir = ensure_dir(output_dir or baseline_analysis_dir.parent / "biological_insight_seed")

    paths = {
        "ranked_feature_annotations": output_dir / "ranked_feature_annotations.tsv",
        "modality_program_summary": output_dir / "modality_program_summary.tsv",
        "candidate_biological_themes": output_dir / "candidate_biological_themes.tsv",
        "biological_insight_seed_summary": output_dir / "biological_insight_seed_summary.yaml",
        "biological_insight_seed_report": output_dir / "biological_insight_seed_report.html",
    }

    annotated_features_df.to_csv(paths["ranked_feature_annotations"], sep="\t", index=False)
    modality_program_summary_df.to_csv(paths["modality_program_summary"], sep="\t", index=False)
    candidate_themes_df.to_csv(paths["candidate_biological_themes"], sep="\t", index=False)

    summary = {
        "insight_seed_id": f"{context.get('atlas_name', 'atlas')}_biological_insight_seed",
        "atlas_name": str(context.get("atlas_name", "")),
        "analysis_context": str(analysis_context_path),
        "baseline_analysis_dir": str(baseline_analysis_dir),
        "top_annotated_feature_count": int(annotated_features_df.shape[0]),
        "modality_program_count": int(modality_program_summary_df.shape[0]),
        "candidate_theme_count": int(candidate_themes_df.shape[0]),
        "interpretation_status": "seed_hypotheses_require_validation",
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {
            "stage": "biological_insight_seed_generation",
            "purpose": "convert baseline AI multi-omics outputs into scaffolded biological interpretation candidates",
        },
    }

    write_yaml(paths["biological_insight_seed_summary"], summary)
    report_html = build_html_report(
        context,
        cluster_summary_df,
        annotated_features_df,
        modality_program_summary_df,
        candidate_themes_df,
        summary,
    )
    paths["biological_insight_seed_report"].write_text(report_html, encoding="utf-8")

    return summary, annotated_features_df, modality_program_summary_df, candidate_themes_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Build a biological insight seed report from baseline AI multi-omics analysis outputs."
    )
    parser.add_argument("--analysis-context", required=True, type=Path)
    parser.add_argument("--baseline-analysis-dir", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--top-n-features", type=int, default=50)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        summary, annotated_features_df, modality_program_summary_df, candidate_themes_df, paths = build_biological_insight_seed(
            analysis_context_path=args.analysis_context,
            baseline_analysis_dir=args.baseline_analysis_dir,
            output_dir=args.output_dir,
            top_n_features=args.top_n_features,
        )
    except Exception as exc:
        print(f"ERROR: Biological insight seed build failed: {exc}", file=sys.stderr)
        return 1

    print("Biological insight seed report complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Annotated features: {summary['top_annotated_feature_count']}")
    print(f"Candidate themes: {summary['candidate_theme_count']}")
    print(f"Report: {paths['biological_insight_seed_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

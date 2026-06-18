#!/usr/bin/env python3

import argparse
import html
import sys
from pathlib import Path

import numpy as np
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


def dataframe_to_html_table(df, max_rows=25):
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


def prepare_numeric_matrix(feature_df, sample_id_column="sample_id"):
    if sample_id_column not in feature_df.columns:
        raise ValueError(f"sample_id column '{sample_id_column}' is missing from integrated feature matrix")

    sample_ids = feature_df[sample_id_column].astype(str).tolist()
    numeric_df = feature_df.drop(columns=[sample_id_column]).apply(pd.to_numeric, errors="coerce")

    for column in numeric_df.columns:
        median_value = numeric_df[column].median()
        if pd.isna(median_value):
            median_value = 0.0
        numeric_df[column] = numeric_df[column].fillna(median_value)

    means = numeric_df.mean(axis=0)
    stds = numeric_df.std(axis=0, ddof=0).replace(0, 1.0).fillna(1.0)
    scaled_df = (numeric_df - means) / stds

    return sample_ids, scaled_df


def compute_pca_embedding(scaled_df, sample_ids, n_components=2):
    x = scaled_df.to_numpy(dtype=float)
    if x.shape[0] == 0 or x.shape[1] == 0:
        raise ValueError("Integrated feature matrix has no samples or no numeric features")

    x_centered = x - x.mean(axis=0, keepdims=True)
    u, singular_values, vt = np.linalg.svd(x_centered, full_matrices=False)

    component_count = min(n_components, vt.shape[0])
    scores = u[:, :component_count] * singular_values[:component_count]

    embedding = pd.DataFrame({"sample_id": sample_ids})
    for idx in range(component_count):
        embedding[f"PC{idx + 1}"] = scores[:, idx]

    if component_count < n_components:
        for idx in range(component_count, n_components):
            embedding[f"PC{idx + 1}"] = 0.0

    variance = singular_values**2
    total_variance = float(variance.sum()) if variance.size else 0.0
    explained = []
    for idx in range(n_components):
        value = float(variance[idx] / total_variance) if idx < len(variance) and total_variance > 0 else 0.0
        explained.append(value)

    loadings = pd.DataFrame({"feature_id": scaled_df.columns})
    for idx in range(component_count):
        loadings[f"PC{idx + 1}_loading"] = vt[idx, :]
    for idx in range(component_count, n_components):
        loadings[f"PC{idx + 1}_loading"] = 0.0

    return embedding, loadings, explained


def assign_clusters_from_pc1(embedding_df, cluster_count=2):
    out = embedding_df[["sample_id"]].copy()
    if "PC1" not in embedding_df.columns:
        out["cluster_id"] = "cluster_1"
        return out

    if cluster_count <= 1 or embedding_df.shape[0] <= 1:
        out["cluster_id"] = "cluster_1"
        return out

    ranks = embedding_df["PC1"].rank(method="first")
    bins = pd.qcut(ranks, q=min(cluster_count, embedding_df.shape[0]), labels=False, duplicates="drop")
    out["cluster_id"] = [f"cluster_{int(value) + 1}" for value in bins]
    return out


def build_cluster_summary(clusters_df):
    return (
        clusters_df["cluster_id"]
        .value_counts()
        .rename_axis("cluster_id")
        .reset_index(name="sample_count")
        .sort_values("cluster_id")
        .reset_index(drop=True)
    )


def infer_modality_from_feature(feature_id):
    text = str(feature_id)
    if "__" in text:
        return text.split("__", 1)[0]
    return "unknown"


def build_feature_rankings(loadings_df, top_n=None):
    out = loadings_df.copy()
    out["modality"] = out["feature_id"].map(infer_modality_from_feature)
    out["abs_PC1_loading"] = out["PC1_loading"].abs()
    out = out.sort_values("abs_PC1_loading", ascending=False).reset_index(drop=True)
    out.insert(0, "rank", range(1, len(out) + 1))
    if top_n is not None:
        out = out.head(top_n).copy()
    return out


def build_modality_block_summary(scaled_df, loadings_df):
    rows = []
    feature_to_modality = {feature: infer_modality_from_feature(feature) for feature in scaled_df.columns}
    for modality in sorted(set(feature_to_modality.values())):
        features = [feature for feature, mod in feature_to_modality.items() if mod == modality]
        subset = scaled_df[features]
        pc1_loadings = loadings_df.loc[loadings_df["feature_id"].isin(features), "PC1_loading"].abs()
        rows.append(
            {
                "modality": modality,
                "feature_count": int(len(features)),
                "mean_feature_variance_after_scaling": float(subset.var(axis=0, ddof=0).mean()) if features else 0.0,
                "mean_abs_PC1_loading": float(pc1_loadings.mean()) if not pc1_loadings.empty else 0.0,
                "max_abs_PC1_loading": float(pc1_loadings.max()) if not pc1_loadings.empty else 0.0,
            }
        )
    return pd.DataFrame(rows).sort_values("mean_abs_PC1_loading", ascending=False).reset_index(drop=True)


def build_html_report(context, cluster_summary_df, modality_summary_df, feature_rankings_df, explained_variance, paths):
    title = "Baseline AI Multi-Omics Analysis Report"
    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        f"<title>{escape_html(title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This report is a baseline analysis layer for the AI multi-omics analysis agent/system.</p>",
        "<p><strong>Scope:</strong> unsupervised PCA-style embedding, sample grouping, modality-block summary, and feature ranking.</p>",
        f"<p><strong>Atlas:</strong> {escape_html(context.get('atlas_name', ''))}</p>",
        f"<p><strong>PC1 explained variance fraction:</strong> {explained_variance[0]:.4f}</p>",
        f"<p><strong>PC2 explained variance fraction:</strong> {explained_variance[1]:.4f}</p>",
        "<h2>Cluster summary</h2>",
        dataframe_to_html_table(cluster_summary_df),
        "<h2>Modality block summary</h2>",
        dataframe_to_html_table(modality_summary_df),
        "<h2>Top ranked features by absolute PC1 loading</h2>",
        dataframe_to_html_table(feature_rankings_df.head(25)),
        "<h2>Generated artifacts</h2>",
        "<ul>",
    ]
    for key, path in paths.items():
        html_parts.append(f"<li><strong>{escape_html(key)}:</strong> {escape_html(path)}</li>")
    html_parts.extend(["</ul>", "</body>", "</html>"])
    return "\n".join(html_parts)


def run_baseline_multiomics_analysis(
    analysis_context_path,
    output_dir=None,
    sample_id_column="sample_id",
    cluster_count=2,
    top_n_features=50,
):
    analysis_context_path = Path(analysis_context_path)
    context = load_yaml_mapping(analysis_context_path)
    inputs = context.get("inputs", {})
    feature_matrix_path = inputs.get("integrated_feature_matrix")
    if not feature_matrix_path:
        raise ValueError("AI analysis context missing inputs.integrated_feature_matrix")

    feature_df = read_table(feature_matrix_path)
    sample_ids, scaled_df = prepare_numeric_matrix(feature_df, sample_id_column=sample_id_column)
    embedding_df, loadings_df, explained_variance = compute_pca_embedding(scaled_df, sample_ids, n_components=2)
    clusters_df = assign_clusters_from_pc1(embedding_df, cluster_count=cluster_count)
    cluster_summary_df = build_cluster_summary(clusters_df)
    feature_rankings_df = build_feature_rankings(loadings_df, top_n=top_n_features)
    modality_summary_df = build_modality_block_summary(scaled_df, loadings_df)

    base_output_dir = Path(output_dir) if output_dir else Path(feature_matrix_path).parent / "baseline_ai_analysis"
    ensure_dir(base_output_dir)

    paths = {
        "sample_embedding": base_output_dir / "sample_embedding.tsv",
        "sample_clusters": base_output_dir / "sample_clusters.tsv",
        "cluster_summary": base_output_dir / "cluster_summary.tsv",
        "feature_rankings": base_output_dir / "feature_rankings.tsv",
        "modality_block_summary": base_output_dir / "modality_block_summary.tsv",
        "baseline_analysis_summary": base_output_dir / "baseline_analysis_summary.yaml",
        "baseline_multiomics_insight_report": base_output_dir / "baseline_multiomics_insight_report.html",
    }

    embedding_df.to_csv(paths["sample_embedding"], sep="\t", index=False)
    clusters_df.to_csv(paths["sample_clusters"], sep="\t", index=False)
    cluster_summary_df.to_csv(paths["cluster_summary"], sep="\t", index=False)
    feature_rankings_df.to_csv(paths["feature_rankings"], sep="\t", index=False)
    modality_summary_df.to_csv(paths["modality_block_summary"], sep="\t", index=False)

    summary = {
        "analysis_id": f"{context.get('atlas_name', 'atlas')}_baseline_multiomics_analysis",
        "atlas_name": str(context.get("atlas_name", "")),
        "analysis_context": str(analysis_context_path),
        "samples": int(len(sample_ids)),
        "features": int(scaled_df.shape[1]),
        "cluster_count_requested": int(cluster_count),
        "clusters_observed": int(cluster_summary_df.shape[0]),
        "pc1_explained_variance_fraction": float(explained_variance[0]),
        "pc2_explained_variance_fraction": float(explained_variance[1]),
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {
            "stage": "baseline_ai_multiomics_analysis",
            "purpose": "generate first-pass unsupervised structure, feature rankings, and modality-block summaries for biological insight generation",
        },
    }
    write_yaml(paths["baseline_analysis_summary"], summary)

    report_html = build_html_report(context, cluster_summary_df, modality_summary_df, feature_rankings_df, explained_variance, paths)
    paths["baseline_multiomics_insight_report"].write_text(report_html, encoding="utf-8")

    return summary, embedding_df, clusters_df, feature_rankings_df, modality_summary_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Run baseline AI multi-omics analysis from an AI multi-omics analysis context."
    )
    parser.add_argument("--analysis-context", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--sample-id-column", default="sample_id")
    parser.add_argument("--cluster-count", type=int, default=2)
    parser.add_argument("--top-n-features", type=int, default=50)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        summary, embedding_df, clusters_df, feature_rankings_df, modality_summary_df, paths = run_baseline_multiomics_analysis(
            analysis_context_path=args.analysis_context,
            output_dir=args.output_dir,
            sample_id_column=args.sample_id_column,
            cluster_count=args.cluster_count,
            top_n_features=args.top_n_features,
        )
    except Exception as exc:
        print(f"ERROR: Baseline AI multi-omics analysis failed: {exc}", file=sys.stderr)
        return 1

    print("Baseline AI multi-omics analysis complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Samples: {summary['samples']}")
    print(f"Features: {summary['features']}")
    print(f"Clusters observed: {summary['clusters_observed']}")
    print(f"Report: {paths['baseline_multiomics_insight_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


DEFAULT_CONFIG = Path("configs/public_data_sources/public_dataset_biological_interpretation_request.yaml")


GENE_SETS: Dict[str, List[str]] = {
    "cell_cycle_proliferation": [
        "MKI67", "TOP2A", "CDK1", "CCNB1", "CCNB2", "CDC20", "AURKA", "AURKB",
        "BUB1", "BUB1B", "PCNA", "MCM2", "MCM3", "MCM4", "MCM5", "MCM6", "MCM7"
    ],
    "immune_inflammation": [
        "CD3D", "CD3E", "CD4", "CD8A", "CD8B", "PTPRC", "LST1", "AIF1",
        "CXCL9", "CXCL10", "CXCL11", "CCL2", "CCL3", "CCL4", "CCL5", "NKG7", "GZMB"
    ],
    "extracellular_matrix_invasion": [
        "COL1A1", "COL1A2", "COL3A1", "COL5A1", "COL5A2", "FN1", "VIM",
        "MMP2", "MMP9", "MMP11", "SPARC", "POSTN", "ITGA5", "ITGB1"
    ],
    "breast_luminal_hormone": [
        "ESR1", "PGR", "ERBB2", "GATA3", "FOXA1", "XBP1", "BCL2",
        "TFF1", "TFF3", "AGR2", "KRT8", "KRT18", "KRT19"
    ],
    "basal_epithelial": [
        "KRT5", "KRT6A", "KRT6B", "KRT14", "KRT17", "EGFR", "LAMC2", "CAV1", "CAV2"
    ],
    "dna_damage_repair": [
        "BRCA1", "BRCA2", "RAD51", "RAD50", "ATM", "ATR", "CHEK1", "CHEK2",
        "PARP1", "TP53", "FANCA", "FANCD2"
    ],
    "metabolism_hypoxia": [
        "HIF1A", "VEGFA", "SLC2A1", "LDHA", "ENO1", "PGK1", "ALDOA", "HK2", "CA9", "BNIP3"
    ],
}


def load_config(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml
            loaded = yaml.safe_load(text)
            if not isinstance(loaded, dict):
                raise ValueError("Config did not parse to a dictionary")
            return loaded
        except Exception as exc:
            raise RuntimeError(f"Could not parse config: {path}") from exc


def norm_col(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def find_col(df: pd.DataFrame, candidates: List[str], default_index: int = 0) -> str:
    if df.empty and len(df.columns) == 0:
        raise ValueError("Cannot infer column from an empty dataframe with no columns")
    lookup = {norm_col(c): c for c in df.columns}
    for candidate in candidates:
        key = norm_col(candidate)
        if key in lookup:
            return lookup[key]
    return str(df.columns[min(default_index, len(df.columns) - 1)])


def infer_pc_cols(df: pd.DataFrame) -> Tuple[str, str]:
    numeric = []
    for col in df.columns:
        vals = pd.to_numeric(df[col], errors="coerce")
        if vals.notna().sum() >= 2:
            numeric.append(str(col))

    lookup = {norm_col(c): str(c) for c in df.columns}
    pc1 = lookup.get("pc1") or lookup.get("pca1") or lookup.get("principal_component_1") or lookup.get("component_1")
    pc2 = lookup.get("pc2") or lookup.get("pca2") or lookup.get("principal_component_2") or lookup.get("component_2")

    if pc1 and pc2 and pc1 != pc2:
        return pc1, pc2
    if len(numeric) >= 2:
        return numeric[0], numeric[1]
    raise ValueError("Could not infer PCA coordinate columns.")


def extract_gene_symbol(feature: object) -> str:
    text = str(feature).strip()
    if not text or text.lower() == "nan":
        return ""
    if "|" in text:
        text = text.split("|")[-1]
    if ":" in text:
        text = text.split(":")[-1]
    text = re.sub(r"^gene[_\-]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\.\d+$", "", text)
    return text.upper()


def gene_set_hits(symbol: str) -> str:
    hits = []
    for set_name, genes in GENE_SETS.items():
        if symbol.upper() in genes:
            hits.append(set_name)
    return ";".join(hits)


def build_pca_plot(pca: pd.DataFrame, clusters: pd.DataFrame, png_path: Path, dpi: int) -> dict:
    sample_col_pca = find_col(pca, ["sample_id", "sample", "case_id", "barcode"], 0)
    sample_col_cluster = find_col(clusters, ["sample_id", "sample", "case_id", "barcode"], 0)
    cluster_col = find_col(clusters, ["cluster", "kmeans_cluster", "cluster_id", "label"], 1)
    pc1, pc2 = infer_pc_cols(pca)

    merged = pca.merge(
        clusters[[sample_col_cluster, cluster_col]],
        left_on=sample_col_pca,
        right_on=sample_col_cluster,
        how="left",
    )

    merged[pc1] = pd.to_numeric(merged[pc1], errors="coerce")
    merged[pc2] = pd.to_numeric(merged[pc2], errors="coerce")
    merged[cluster_col] = merged[cluster_col].fillna("unassigned").astype(str)
    merged = merged.dropna(subset=[pc1, pc2])

    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 6))
    for cluster_value in sorted(merged[cluster_col].unique()):
        subset = merged[merged[cluster_col] == cluster_value]
        ax.scatter(
            subset[pc1], subset[pc2], label=f"Cluster {cluster_value}",
            s=60, alpha=0.85, edgecolors="black", linewidths=0.4,
        )
    ax.set_title("TCGA-BRCA PCA Colored by KMeans Cluster")
    ax.set_xlabel(pc1)
    ax.set_ylabel(pc2)
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(png_path, dpi=dpi)
    plt.close(fig)

    return {
        "sample_column_pca": sample_col_pca,
        "sample_column_cluster": sample_col_cluster,
        "cluster_column": cluster_col,
        "pc1_column": pc1,
        "pc2_column": pc2,
        "plotted_sample_count": int(len(merged)),
        "cluster_count": int(merged[cluster_col].nunique()),
        "clusters": sorted(merged[cluster_col].unique().tolist()),
    }


def build_feature_outputs(feature_importance: pd.DataFrame, outputs: dict, top_n: int, gene_set_top_n: int, dpi: int) -> dict:
    feature_col = find_col(feature_importance, ["feature", "feature_id", "gene", "gene_id", "gene_name", "symbol"], 0)
    importance_col = find_col(feature_importance, ["importance", "feature_importance", "score", "gini_importance"], 1)

    df = feature_importance.copy()
    df[importance_col] = pd.to_numeric(df[importance_col], errors="coerce")
    df = df.dropna(subset=[importance_col]).sort_values(importance_col, ascending=False).reset_index(drop=True)
    df["rank"] = range(1, len(df) + 1)
    df["gene_symbol"] = df[feature_col].apply(extract_gene_symbol)
    df["gene_set_hits"] = df["gene_symbol"].apply(gene_set_hits)
    df["interpretation_note"] = df["gene_set_hits"].apply(
        lambda x: "Matched biological scaffold: " + x if x else "No scaffold match yet; data-driven candidate."
    )

    top = df.head(top_n).copy()
    top_path = Path(outputs["top_features_interpretation"])
    top_path.parent.mkdir(parents=True, exist_ok=True)
    top.to_csv(top_path, sep="\t", index=False)

    plot_df = top.sort_values(importance_col, ascending=True)
    fig_height = max(5, 0.25 * len(plot_df) + 2)
    fig, ax = plt.subplots(figsize=(9, fig_height))
    labels = plot_df["gene_symbol"].where(plot_df["gene_symbol"] != "", plot_df[feature_col]).astype(str)
    ax.barh(labels, plot_df[importance_col])
    ax.set_title(f"Top {len(plot_df)} Random Forest Feature Importances")
    ax.set_xlabel(importance_col)
    ax.set_ylabel("Gene / Feature")
    fig.tight_layout()
    fig.savefig(outputs["feature_importance_png"], dpi=dpi)
    plt.close(fig)

    scaffold_rows = []
    subset = df.head(gene_set_top_n)
    for set_name, genes in GENE_SETS.items():
        matched = subset[subset["gene_symbol"].isin(genes)]
        scaffold_rows.append({
            "gene_set": set_name,
            "matched_feature_count": int(len(matched)),
            "matched_genes": ";".join(matched["gene_symbol"].dropna().unique().tolist()),
            "top_rank_if_present": int(matched["rank"].min()) if len(matched) else "",
            "max_importance_if_present": float(matched[importance_col].max()) if len(matched) else "",
        })

    scaffold = pd.DataFrame(scaffold_rows).sort_values(["matched_feature_count", "gene_set"], ascending=[False, True])
    Path(outputs["gene_set_interpretation"]).parent.mkdir(parents=True, exist_ok=True)
    scaffold.to_csv(outputs["gene_set_interpretation"], sep="\t", index=False)

    return {
        "feature_column": feature_col,
        "importance_column": importance_col,
        "input_rows": int(len(feature_importance)),
        "valid_rows": int(len(df)),
        "top_features_written": int(len(top)),
        "gene_sets_evaluated": int(len(scaffold)),
        "gene_sets_with_matches": int((scaffold["matched_feature_count"] > 0).sum()),
    }


def write_report(outputs: dict, summary: dict) -> None:
    report = Path(outputs["report_markdown"])
    report.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# OpenMultiOmics-Cancer-Atlas v0.4.0-a41 Biological Interpretation Report

## Purpose

This milestone adds a biological interpretation layer on top of the finalized `v0.4.0-a40` AI modeling execution outputs.

## Upstream State

- Upstream milestone: `v0.4.0-a40`
- Upstream commit: `716a7ce`
- Dataset: TCGA-BRCA real transcriptomics pilot

## Generated Outputs

- PCA/KMeans cluster plot: `pca_kmeans_clusters.png`
- Feature-importance plot: `top_feature_importance.png`
- Top-feature interpretation table: `top_features_interpretation.tsv`
- Gene-set scaffold table: `gene_set_interpretation.tsv`
- Summary JSON: `biological_interpretation_summary.json`

## PCA/KMeans Summary

- Plotted samples: {summary['pca']['plotted_sample_count']}
- Cluster count: {summary['pca']['cluster_count']}
- Clusters: {summary['pca']['clusters']}

## Feature Interpretation Summary

- Valid feature-importance rows: {summary['feature_importance']['valid_rows']}
- Top features written: {summary['feature_importance']['top_features_written']}
- Gene sets evaluated: {summary['feature_importance']['gene_sets_evaluated']}
- Gene sets with matches: {summary['feature_importance']['gene_sets_with_matches']}

## Interpretation Notes

The gene-set scaffold is intentionally lightweight. It is not yet formal enrichment testing. It provides a transparent first biological annotation layer for model-ranked features and prepares the project for a later clinical/subtype and pathway-enrichment milestone.
"""
    report.write_text(text, encoding="utf-8")


def run(config_path: Path) -> dict:
    config = load_config(config_path)
    inputs = config["inputs"]
    outputs = config["outputs"]
    params = config["parameters"]

    required = [Path(inputs["pca_coordinates"]), Path(inputs["kmeans_clusters"]), Path(inputs["feature_importance"])]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing required a40 input files: " + ", ".join(missing))

    pca = pd.read_csv(inputs["pca_coordinates"], sep="\t")
    clusters = pd.read_csv(inputs["kmeans_clusters"], sep="\t")
    feature_importance = pd.read_csv(inputs["feature_importance"], sep="\t")

    Path(outputs["interpretation_dir"]).mkdir(parents=True, exist_ok=True)
    pca_summary = build_pca_plot(pca, clusters, Path(outputs["pca_cluster_png"]), int(params.get("figure_dpi", 160)))
    feature_summary = build_feature_outputs(
        feature_importance, outputs,
        int(params.get("top_n_features", 30)), int(params.get("gene_set_top_n", 100)), int(params.get("figure_dpi", 160))
    )

    summary = {
        "version": config["version"],
        "bundle_name": config["bundle_name"],
        "project": config["project"],
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "upstream_version": config["upstream_version"],
        "upstream_commit": config["upstream_commit"],
        "pca": pca_summary,
        "feature_importance": feature_summary,
        "outputs": outputs,
        "ready_for_biological_review": True,
        "ready_for_next_clinical_subtype_layer": True,
    }

    Path(outputs["summary_json"]).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_report(outputs, summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = parser.parse_args()
    summary = run(Path(args.config))
    print("v0.4.0-a41 biological interpretation completed.")
    print("Output directory:", summary["outputs"]["interpretation_dir"])
    print("Ready for biological review:", summary["ready_for_biological_review"])


if __name__ == "__main__":
    main()

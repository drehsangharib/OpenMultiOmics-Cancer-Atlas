from pathlib import Path
import json

import pandas as pd

from core.data.build_public_dataset_biological_interpretation import run


def test_build_public_dataset_biological_interpretation(tmp_path):
    input_dir = tmp_path / "ai_modeling_execution"
    output_dir = tmp_path / "biological_interpretation"
    input_dir.mkdir(parents=True)

    pca = pd.DataFrame({
        "sample_id": ["S1", "S2", "S3", "S4"],
        "PC1": [1.0, 1.2, -0.8, -1.1],
        "PC2": [0.3, 0.4, -0.2, -0.5],
    })
    clusters = pd.DataFrame({
        "sample_id": ["S1", "S2", "S3", "S4"],
        "cluster": [0, 0, 1, 1],
    })
    importance = pd.DataFrame({
        "feature": ["TP53", "MKI67", "ESR1", "COL1A1", "CXCL10", "BRCA1", "SLC2A1"],
        "importance": [0.30, 0.25, 0.20, 0.10, 0.08, 0.05, 0.02],
    })

    pca_path = input_dir / "pca_coordinates.tsv"
    cluster_path = input_dir / "kmeans_clusters.tsv"
    importance_path = input_dir / "feature_importance.tsv"
    pca.to_csv(pca_path, sep="\t", index=False)
    clusters.to_csv(cluster_path, sep="\t", index=False)
    importance.to_csv(importance_path, sep="\t", index=False)

    config = {
        "version": "v0.4.0-a41",
        "bundle_name": "test_biological_interpretation_layer",
        "project": "OpenMultiOmics-Cancer-Atlas",
        "upstream_version": "v0.4.0-a40",
        "upstream_commit": "716a7ce",
        "inputs": {
            "pca_coordinates": str(pca_path),
            "kmeans_clusters": str(cluster_path),
            "feature_importance": str(importance_path),
            "modeling_summary": str(input_dir / "modeling_summary.yaml"),
        },
        "outputs": {
            "interpretation_dir": str(output_dir),
            "pca_cluster_png": str(output_dir / "pca_kmeans_clusters.png"),
            "feature_importance_png": str(output_dir / "top_feature_importance.png"),
            "top_features_interpretation": str(output_dir / "top_features_interpretation.tsv"),
            "gene_set_interpretation": str(output_dir / "gene_set_interpretation.tsv"),
            "report_markdown": str(output_dir / "biological_interpretation_report.md"),
            "summary_json": str(output_dir / "biological_interpretation_summary.json"),
        },
        "parameters": {"top_n_features": 5, "gene_set_top_n": 7, "figure_dpi": 80},
    }

    config_path = tmp_path / "request.yaml"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    summary = run(config_path)

    assert summary["version"] == "v0.4.0-a41"
    assert summary["ready_for_biological_review"] is True
    assert summary["pca"]["plotted_sample_count"] == 4
    assert summary["pca"]["cluster_count"] == 2
    assert summary["feature_importance"]["top_features_written"] == 5
    assert summary["feature_importance"]["gene_sets_with_matches"] >= 1

    for name in [
        "pca_kmeans_clusters.png",
        "top_feature_importance.png",
        "top_features_interpretation.tsv",
        "gene_set_interpretation.tsv",
        "biological_interpretation_report.md",
        "biological_interpretation_summary.json",
    ]:
        path = output_dir / name
        assert path.exists()
        assert path.stat().st_size > 0

    top = pd.read_csv(output_dir / "top_features_interpretation.tsv", sep="\t")
    assert "gene_symbol" in top.columns
    assert "gene_set_hits" in top.columns
    assert "interpretation_note" in top.columns

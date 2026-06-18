from pathlib import Path

import pandas as pd
import yaml

from core.agent.run_baseline_multiomics_analysis import (
    build_arg_parser,
    run_baseline_multiomics_analysis,
)


def test_run_baseline_multiomics_analysis(tmp_path: Path):
    matrix_path = tmp_path / "integrated_feature_matrix.tsv"
    context_path = tmp_path / "ai_multiomics_analysis_context.yaml"
    output_dir = tmp_path / "baseline_ai_analysis"

    pd.DataFrame(
        {
            "sample_id": ["S1", "S2", "S3", "S4"],
            "transcriptomics__G1": [1.0, 2.0, 3.0, 4.0],
            "proteomics__P1": [4.0, 3.0, 2.0, 1.0],
            "epigenome__C1": [0.1, 0.2, 0.8, 0.9],
            "metabolomics__M1": [10.0, 20.0, 30.0, 40.0],
        }
    ).to_csv(matrix_path, sep="\t", index=False)

    context = {
        "context_id": "test_context",
        "atlas_name": "test_atlas",
        "inputs": {
            "integrated_feature_matrix": str(matrix_path),
            "multiomics_integration_manifest": "manifest.yaml",
            "feature_block_inventory": "blocks.tsv",
            "integrated_feature_qc_summary": "qc.tsv",
        },
    }
    with context_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(context, handle, sort_keys=False)

    summary, embedding_df, clusters_df, feature_rankings_df, modality_summary_df, paths = run_baseline_multiomics_analysis(
        analysis_context_path=context_path,
        output_dir=output_dir,
        cluster_count=2,
    )

    assert paths["sample_embedding"].exists()
    assert paths["sample_clusters"].exists()
    assert paths["feature_rankings"].exists()
    assert paths["modality_block_summary"].exists()
    assert paths["baseline_analysis_summary"].exists()
    assert paths["baseline_multiomics_insight_report"].exists()
    assert summary["samples"] == 4
    assert summary["features"] == 4
    assert embedding_df.shape[0] == 4
    assert clusters_df.shape[0] == 4
    assert not feature_rankings_df.empty
    assert set(modality_summary_df["modality"]) == {"transcriptomics", "proteomics", "epigenome", "metabolomics"}


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--analysis-context", "context.yaml", "--cluster-count", "3"])
    assert str(args.analysis_context).endswith("context.yaml")
    assert args.cluster_count == 3

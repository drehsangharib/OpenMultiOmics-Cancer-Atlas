from pathlib import Path

import pandas as pd
import yaml

from core.agent.build_biological_insight_seed import (
    build_arg_parser,
    build_biological_insight_seed,
)


def test_build_biological_insight_seed(tmp_path: Path):
    context_path = tmp_path / "ai_multiomics_analysis_context.yaml"
    baseline_dir = tmp_path / "baseline_ai_analysis"
    output_dir = tmp_path / "biological_insight_seed"
    baseline_dir.mkdir(parents=True, exist_ok=True)

    with context_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump({"atlas_name": "test_atlas"}, handle, sort_keys=False)

    pd.DataFrame(
        [
            {"rank": 1, "feature_id": "transcriptomics__GENE1", "PC1_loading": 0.8, "abs_PC1_loading": 0.8},
            {"rank": 2, "feature_id": "proteomics__PROT1", "PC1_loading": -0.7, "abs_PC1_loading": 0.7},
            {"rank": 3, "feature_id": "epigenome__CG0001", "PC1_loading": 0.6, "abs_PC1_loading": 0.6},
            {"rank": 4, "feature_id": "metabolomics__MET1", "PC1_loading": -0.5, "abs_PC1_loading": 0.5},
        ]
    ).to_csv(baseline_dir / "feature_rankings.tsv", sep="\t", index=False)

    pd.DataFrame(
        [
            {"modality": "transcriptomics", "feature_count": 1, "mean_abs_PC1_loading": 0.8, "max_abs_PC1_loading": 0.8},
            {"modality": "proteomics", "feature_count": 1, "mean_abs_PC1_loading": 0.7, "max_abs_PC1_loading": 0.7},
        ]
    ).to_csv(baseline_dir / "modality_block_summary.tsv", sep="\t", index=False)

    pd.DataFrame(
        [
            {"cluster_id": "cluster_1", "sample_count": 2},
            {"cluster_id": "cluster_2", "sample_count": 2},
        ]
    ).to_csv(baseline_dir / "cluster_summary.tsv", sep="\t", index=False)

    summary, annotated_df, modality_df, themes_df, paths = build_biological_insight_seed(
        analysis_context_path=context_path,
        baseline_analysis_dir=baseline_dir,
        output_dir=output_dir,
        top_n_features=4,
    )

    assert paths["ranked_feature_annotations"].exists()
    assert paths["modality_program_summary"].exists()
    assert paths["candidate_biological_themes"].exists()
    assert paths["biological_insight_seed_summary"].exists()
    assert paths["biological_insight_seed_report"].exists()
    assert summary["top_annotated_feature_count"] == 4
    assert "candidate_interpretation_group" in annotated_df.columns
    assert "cross_modality_state_signal" in set(themes_df["theme_name"])
    assert not modality_df.empty


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(
        [
            "--analysis-context", "context.yaml",
            "--baseline-analysis-dir", "baseline",
            "--top-n-features", "10",
        ]
    )
    assert str(args.analysis_context).endswith("context.yaml")
    assert args.top_n_features == 10

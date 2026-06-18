from pathlib import Path

import pandas as pd
import yaml

from core.agent.build_program_annotation_report import (
    build_arg_parser,
    build_program_annotation_report,
)


def test_build_program_annotation_report(tmp_path: Path):
    seed_dir = tmp_path / "biological_insight_seed"
    seed_dir.mkdir(parents=True, exist_ok=True)
    registry_path = tmp_path / "registry.yaml"

    pd.DataFrame(
        [
            {
                "rank": 1,
                "feature_id": "transcriptomics__GENE1",
                "modality": "transcriptomics",
                "raw_feature_id": "GENE1",
                "candidate_interpretation_group": "expression_state_signal",
                "abs_PC1_loading": 0.8,
                "PC1_loading": 0.8,
            },
            {
                "rank": 2,
                "feature_id": "proteomics__PROT1",
                "modality": "proteomics",
                "raw_feature_id": "PROT1",
                "candidate_interpretation_group": "protein_abundance_signal",
                "abs_PC1_loading": 0.7,
                "PC1_loading": -0.7,
            },
        ]
    ).to_csv(seed_dir / "ranked_feature_annotations.tsv", sep="\t", index=False)

    with (seed_dir / "biological_insight_seed_summary.yaml").open("w", encoding="utf-8") as handle:
        yaml.safe_dump({"atlas_name": "test_atlas"}, handle, sort_keys=False)

    registry = {
        "programs": {
            "expression_state_signal": {
                "display_name": "Expression state signal",
                "modality": "transcriptomics",
                "interpretation_layer": "gene_expression_program",
                "description": "test expression program",
                "seed_keywords": ["expression"],
            },
            "protein_abundance_signal": {
                "display_name": "Protein abundance signal",
                "modality": "proteomics",
                "interpretation_layer": "protein_abundance_program",
                "description": "test protein program",
                "seed_keywords": ["protein"],
            },
        }
    }
    with registry_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(registry, handle, sort_keys=False)

    summary, annotations_df, program_summary_df, priority_df, paths = build_program_annotation_report(
        biological_insight_seed_dir=seed_dir,
        program_registry_path=registry_path,
    )

    assert paths["program_annotated_features"].exists()
    assert paths["program_level_summary"].exists()
    assert paths["interpretation_priority_table"].exists()
    assert paths["program_annotation_summary"].exists()
    assert paths["program_annotation_report"].exists()
    assert summary["annotated_feature_count"] == 2
    assert set(annotations_df["program_id"]) == {"expression_state_signal", "protein_abundance_signal"}
    assert not program_summary_df.empty
    assert not priority_df.empty


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--biological-insight-seed-dir", "seed"])
    assert str(args.biological_insight_seed_dir).endswith("seed")

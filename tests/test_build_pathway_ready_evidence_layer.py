from pathlib import Path

import pandas as pd
import yaml

from core.agent.build_pathway_ready_evidence_layer import (
    build_arg_parser,
    build_pathway_ready_evidence_layer,
)


def test_build_pathway_ready_evidence_layer(tmp_path: Path):
    program_dir = tmp_path / "program_annotation"
    program_dir.mkdir(parents=True, exist_ok=True)
    registry_path = tmp_path / "resource_registry.yaml"
    seed_map_path = tmp_path / "seed_map.tsv"

    pd.DataFrame(
        [
            {
                "rank": 1,
                "feature_id": "transcriptomics__GENE1",
                "modality": "transcriptomics",
                "raw_feature_id": "GENE1",
                "program_id": "expression_state_signal",
                "program_display_name": "Expression state signal",
                "interpretation_layer": "gene_expression_program",
                "abs_PC1_loading": 0.8,
            },
            {
                "rank": 2,
                "feature_id": "proteomics__PROT1",
                "modality": "proteomics",
                "raw_feature_id": "PROT1",
                "program_id": "protein_abundance_signal",
                "program_display_name": "Protein abundance signal",
                "interpretation_layer": "protein_abundance_program",
                "abs_PC1_loading": 0.7,
            },
        ]
    ).to_csv(program_dir / "program_annotated_features.tsv", sep="\t", index=False)

    with (program_dir / "program_annotation_summary.yaml").open("w", encoding="utf-8") as handle:
        yaml.safe_dump({"atlas_name": "test_atlas"}, handle, sort_keys=False)

    registry = {
        "resources": {
            "gene_program_seed": {
                "display_name": "Gene seed",
                "entity_type": "gene_or_transcript",
                "supported_modalities": ["transcriptomics"],
                "resource_type": "local_seed_mapping",
                "description": "test registry",
            }
        }
    }
    with registry_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(registry, handle, sort_keys=False)

    pd.DataFrame(
        [
            {
                "entity_id": "GENE1",
                "entity_type": "gene_or_transcript",
                "canonical_label": "GENE1",
                "candidate_program": "expression_state_signal",
                "evidence_label": "test evidence",
                "evidence_source": "test_seed",
            }
        ]
    ).to_csv(seed_map_path, sep="\t", index=False)

    summary, feature_evidence_df, program_summary_df, priority_df, paths = build_pathway_ready_evidence_layer(
        program_annotation_dir=program_dir,
        resource_registry_path=registry_path,
        seed_annotation_map_path=seed_map_path,
    )

    assert paths["feature_evidence_table"].exists()
    assert paths["program_evidence_summary"].exists()
    assert paths["pathway_prioritization_table"].exists()
    assert paths["annotation_resource_inventory"].exists()
    assert paths["pathway_ready_evidence_summary"].exists()
    assert paths["pathway_ready_evidence_report"].exists()
    assert summary["feature_evidence_count"] == 2
    assert summary["mapped_feature_count"] == 1
    assert "mapped_to_seed_scaffold" in set(feature_evidence_df["evidence_status"])
    assert not program_summary_df.empty
    assert not priority_df.empty


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--program-annotation-dir", "program_annotation"])
    assert str(args.program_annotation_dir).endswith("program_annotation")

from pathlib import Path

import pandas as pd
import yaml

from core.agent.build_external_annotation_evidence import (
    build_arg_parser,
    build_external_annotation_evidence,
)


def test_build_external_annotation_evidence(tmp_path: Path):
    pathway_dir = tmp_path / "pathway_ready_evidence"
    pathway_dir.mkdir(parents=True, exist_ok=True)
    connector_registry = tmp_path / "connectors.yaml"
    local_seed = tmp_path / "local_seed.tsv"

    pd.DataFrame(
        [
            {
                "rank": 1,
                "feature_id": "transcriptomics__GENE1",
                "modality": "transcriptomics",
                "raw_feature_id": "GENE1",
                "pathway_ready_entity_id": "GENE1",
                "pathway_ready_program": "expression_state_signal",
                "pathway_ready_evidence_source": "local_seed_scaffold",
                "abs_PC1_loading": 0.8,
            },
            {
                "rank": 2,
                "feature_id": "proteomics__PROT1",
                "modality": "proteomics",
                "raw_feature_id": "PROT1",
                "pathway_ready_entity_id": "PROT1",
                "pathway_ready_program": "protein_abundance_signal",
                "pathway_ready_evidence_source": "local_seed_scaffold",
                "abs_PC1_loading": 0.7,
            },
        ]
    ).to_csv(pathway_dir / "feature_evidence_table.tsv", sep="\t", index=False)

    with (pathway_dir / "pathway_ready_evidence_summary.yaml").open("w", encoding="utf-8") as handle:
        yaml.safe_dump({"atlas_name": "test_atlas"}, handle, sort_keys=False)

    with connector_registry.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            {
                "connectors": {
                    "pathway_database_adapter": {
                        "display_name": "Pathway adapter",
                        "connector_type": "local_or_external_pathway_resource",
                        "status": "scaffold",
                        "supported_entity_types": ["gene_or_transcript"],
                        "description": "test connector",
                    }
                }
            },
            handle,
            sort_keys=False,
        )

    pd.DataFrame(
        [
            {
                "pathway_ready_entity_id": "GENE1",
                "entity_type": "gene_or_transcript",
                "external_resource_id": "LOCAL",
                "external_resource_name": "Local seed",
                "external_term_id": "TERM1",
                "external_term_name": "Expression program",
                "evidence_type": "seed",
                "evidence_strength": 0.9,
            }
        ]
    ).to_csv(local_seed, sep="\t", index=False)

    summary, external_evidence_df, external_term_summary_df, connector_inventory_df, readiness_df, paths = build_external_annotation_evidence(
        pathway_ready_evidence_dir=pathway_dir,
        connector_registry_path=connector_registry,
        local_annotation_seed_path=local_seed,
    )

    assert paths["external_annotation_evidence"].exists()
    assert paths["external_term_summary"].exists()
    assert paths["connector_inventory"].exists()
    assert paths["connector_readiness_summary"].exists()
    assert paths["external_annotation_summary"].exists()
    assert paths["external_annotation_report"].exists()
    assert summary["external_evidence_rows"] == 2
    assert summary["mapped_external_evidence_rows"] == 1
    assert "mapped_to_local_external_seed" in set(external_evidence_df["external_annotation_status"])
    assert not connector_inventory_df.empty
    assert not readiness_df.empty


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--pathway-ready-evidence-dir", "pathway_ready"])
    assert str(args.pathway_ready_evidence_dir).endswith("pathway_ready")

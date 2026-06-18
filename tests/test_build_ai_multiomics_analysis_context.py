from pathlib import Path

import pandas as pd
import yaml

from core.agent.build_ai_multiomics_analysis_context import (
    build_ai_multiomics_analysis_context,
    build_arg_parser,
)


def test_build_ai_multiomics_analysis_context(tmp_path: Path):
    integration_manifest = tmp_path / "multiomics_integration_manifest.yaml"
    feature_matrix = tmp_path / "integrated_feature_matrix.tsv"
    block_inventory = tmp_path / "feature_block_inventory.tsv"
    qc_summary = tmp_path / "integrated_feature_qc_summary.tsv"
    output = tmp_path / "ai_multiomics_analysis_context.yaml"

    with integration_manifest.open("w", encoding="utf-8") as handle:
        yaml.safe_dump({"atlas_name": "test_atlas"}, handle, sort_keys=False)

    pd.DataFrame({"sample_id": ["S1", "S2"], "tx__G1": [1.0, 2.0]}).to_csv(feature_matrix, sep="\t", index=False)
    pd.DataFrame({"modality": ["transcriptomics"], "prefixed_feature_count": [1]}).to_csv(block_inventory, sep="\t", index=False)
    pd.DataFrame(
        [
            {"metric": "modalities", "value": 1},
            {"metric": "samples", "value": 2},
            {"metric": "integrated_features", "value": 1},
            {"metric": "missing_values", "value": 0},
        ]
    ).to_csv(qc_summary, sep="\t", index=False)

    context, output_path = build_ai_multiomics_analysis_context(
        integration_manifest_path=integration_manifest,
        integrated_feature_matrix_path=feature_matrix,
        feature_block_inventory_path=block_inventory,
        integrated_feature_qc_summary_path=qc_summary,
        output_path=output,
    )

    assert output_path.exists()
    assert context["atlas_name"] == "test_atlas"
    assert context["readiness_summary"]["samples"] == 2
    assert context["readiness_summary"]["integrated_features"] == 1
    loaded = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert loaded["analysis_scope"] == "multiomics_integrated_feature_table"


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(
        [
            "--integration-manifest", "a.yaml",
            "--integrated-feature-matrix", "matrix.tsv",
            "--feature-block-inventory", "blocks.tsv",
            "--integrated-feature-qc-summary", "qc.tsv",
        ]
    )
    assert str(args.integration_manifest).endswith("a.yaml")

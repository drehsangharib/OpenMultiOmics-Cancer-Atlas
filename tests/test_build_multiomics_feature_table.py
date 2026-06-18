from pathlib import Path

import pandas as pd
import yaml

from core.integration.build_multiomics_feature_table import (
    build_arg_parser,
    build_integrated_feature_table,
)


def write_integration_fixture(tmp_path: Path):
    out = tmp_path / "integrated" / "test_atlas"
    out.mkdir(parents=True, exist_ok=True)

    alignment = pd.DataFrame(
        {
            "sample_id": ["S1", "S2", "S3"],
            "has_transcriptomics": [1, 1, 1],
            "has_proteomics": [0, 1, 1],
            "present_modality_count": [1, 2, 2],
            "is_complete_case": [0, 1, 1],
        }
    )
    alignment_path = out / "sample_alignment.tsv"
    alignment.to_csv(alignment_path, sep="\t", index=False)

    tx_matrix = tmp_path / "tx.tsv"
    pr_matrix = tmp_path / "pr.tsv"
    pd.DataFrame({"sample_id": ["S1", "S2", "S3"], "G1": [1, 2, 3], "G2": [4, 5, 6]}).to_csv(tx_matrix, sep="\t", index=False)
    pd.DataFrame({"sample_id": ["S2", "S3"], "P1": [10, 20]}).to_csv(pr_matrix, sep="\t", index=False)

    manifest = {
        "integration_id": "test_atlas_multiomics_integration_manifest",
        "atlas_name": "test_atlas",
        "integration_scope": "sample_aligned_feature_stores",
        "modalities": ["transcriptomics", "proteomics"],
        "artifacts": {
            "sample_alignment": str(alignment_path),
            "modality_inventory": str(out / "modality_inventory.tsv"),
            "alignment_qc_summary": str(out / "alignment_qc_summary.tsv"),
        },
        "summary": {"modality_count": 2, "union_samples": 3, "complete_case_samples": 2},
        "feature_stores": [
            {
                "modality": "transcriptomics",
                "feature_store_id": "tx_store",
                "feature_store_manifest": "tx_manifest.yaml",
                "normalized_matrix": str(tx_matrix),
                "sample_metadata": "tx_samples.tsv",
                "feature_metadata": "tx_features.tsv",
                "qc_summary": "tx_qc.tsv",
                "sample_count": 3,
            },
            {
                "modality": "proteomics",
                "feature_store_id": "pr_store",
                "feature_store_manifest": "pr_manifest.yaml",
                "normalized_matrix": str(pr_matrix),
                "sample_metadata": "pr_samples.tsv",
                "feature_metadata": "pr_features.tsv",
                "qc_summary": "pr_qc.tsv",
                "sample_count": 2,
            },
        ],
        "agent_role": {"stage": "test", "purpose": "test"},
    }
    manifest_path = out / "multiomics_integration_manifest.yaml"
    with manifest_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(manifest, handle, sort_keys=False)
    return manifest_path


def test_build_integrated_feature_table_complete_cases(tmp_path: Path):
    manifest_path = write_integration_fixture(tmp_path)
    integrated_df, block_df, qc_df, paths = build_integrated_feature_table(manifest_path)

    assert paths["integrated_feature_matrix"].exists()
    assert paths["feature_block_inventory"].exists()
    assert paths["integrated_feature_qc_summary"].exists()
    assert list(integrated_df["sample_id"]) == ["S2", "S3"]
    assert "transcriptomics__G1" in integrated_df.columns
    assert "proteomics__P1" in integrated_df.columns
    assert block_df.shape[0] == 2
    assert int(qc_df.loc[qc_df["metric"] == "integrated_features", "value"].iloc[0]) == 3


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--integration-manifest", "x.yaml", "--all-union-samples"])
    assert str(args.integration_manifest).endswith("x.yaml")
    assert args.all_union_samples is True

from pathlib import Path

import pandas as pd
import yaml

from core.modalities.process_epigenome_matrix import (
    build_arg_parser,
    process_epigenome_manifest,
)


def write_manifest(path: Path, matrix_path: Path, output_dir: Path):
    manifest = {
        "manifest_id": "test_epigenome_manifest",
        "atlas_name": "gbm",
        "modality": "epigenome",
        "data_type": "dna_methylation_matrix",
        "assay": "methylation_array",
        "species": "human",
        "source_name": "synthetic_test",
        "source_url": "https://example.org/",
        "access_level": "test",
        "input_files": [
            {
                "file_id": "methylation_matrix",
                "path": str(matrix_path),
                "file_format": "tsv",
                "matrix_orientation": "samples_by_features",
                "sample_id_column": "sample_id",
                "feature_id_type": "cpg_probe_id",
            }
        ],
        "sample_metadata": {
            "path": str(output_dir / "missing_sample_metadata.tsv"),
            "sample_id_column": "sample_id",
        },
        "feature_metadata": {
            "path": str(output_dir / "missing_feature_metadata.tsv"),
            "feature_id_column": "cpg_probe_id",
        },
        "processing_plan": {
            "normalization": "beta_value_clipping",
            "missing_value_strategy": "median_feature_imputation",
            "batch_correction": "none",
            "feature_filtering": "remove_high_missingness_features",
            "max_missing_fraction": 0.5,
        },
        "expected_outputs": {
            "feature_store_dir": str(output_dir),
            "normalized_matrix": str(output_dir / "normalized_matrix.tsv"),
            "sample_metadata": str(output_dir / "sample_metadata.tsv"),
            "feature_metadata": str(output_dir / "feature_metadata.tsv"),
            "qc_summary": str(output_dir / "qc_summary.tsv"),
        },
        "agent_role": {
            "stage": "modality_preprocessing",
            "purpose": "prepare epigenomic features for downstream AI multi-omics analysis",
        },
    }

    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(manifest, handle, sort_keys=False)


def test_process_epigenome_manifest(tmp_path: Path):
    matrix_path = tmp_path / "methylation_matrix.tsv"
    output_dir = tmp_path / "feature_store"
    manifest_path = tmp_path / "manifest.yaml"

    matrix = pd.DataFrame(
        {
            "sample_id": ["S1", "S2", "S3"],
            "CG0001": [0.2, 0.5, 0.8],
            "CG0002": [0.1, None, 1.2],
            "HIGH_MISSING": [None, None, 0.4],
            "ZERO_VAR": [0.3, 0.3, 0.3],
            "NON_NUMERIC": ["a", "b", "c"],
        }
    )
    matrix.to_csv(matrix_path, sep="\t", index=False)

    write_manifest(manifest_path, matrix_path, output_dir)

    normalized_df, qc_summary_df, feature_store_manifest, paths = process_epigenome_manifest(
        manifest_path
    )

    assert paths["normalized_matrix"].exists()
    assert paths["sample_metadata"].exists()
    assert paths["feature_metadata"].exists()
    assert paths["qc_summary"].exists()
    assert paths["feature_store_manifest"].exists()

    assert normalized_df.shape[0] == 3
    assert "sample_id" in normalized_df.columns
    assert "CG0001" in normalized_df.columns
    assert "CG0002" in normalized_df.columns
    assert "HIGH_MISSING" not in normalized_df.columns
    assert "ZERO_VAR" not in normalized_df.columns
    assert "NON_NUMERIC" not in normalized_df.columns

    assert normalized_df["CG0002"].max() <= 1.0
    assert normalized_df["CG0002"].min() >= 0.0
    assert "metric" in qc_summary_df.columns
    assert feature_store_manifest["modality"] == "epigenome"


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--manifest", "configs/data_manifests/example_epigenome_manifest.yaml"])

    assert str(args.manifest).replace("\\", "/").endswith(
        "configs/data_manifests/example_epigenome_manifest.yaml"
    )
from pathlib import Path

import pytest
import yaml

from core.data.validate_data_manifest import (
    validate_manifest_data,
    validate_manifest_file,
    validate_manifest_dir,
    build_arg_parser,
)


def good_manifest():
    return {
        "manifest_id": "example_transcriptomics",
        "atlas_name": "brca",
        "modality": "transcriptomics",
        "data_type": "gene_expression_matrix",
        "assay": "RNA-seq",
        "species": "human",
        "source_name": "UCSC Xena",
        "source_url": "https://xena.ucsc.edu/",
        "access_level": "public",
        "input_files": [
            {
                "file_id": "matrix",
                "path": "matrix.tsv",
                "file_format": "tsv",
                "matrix_orientation": "samples_by_features",
                "sample_id_column": "sample_id",
                "feature_id_type": "gene_symbol",
            }
        ],
        "sample_metadata": {
            "path": "samples.tsv",
            "sample_id_column": "sample_id",
        },
        "feature_metadata": {
            "path": "features.tsv",
            "feature_id_column": "gene_symbol",
        },
        "processing_plan": {
            "normalization": "log2_tpm_plus_one",
        },
        "expected_outputs": {
            "feature_store_dir": "outputs/features/transcriptomics/brca",
        },
        "agent_role": {
            "stage": "modality_preprocessing",
            "purpose": "prepare data for AI multi-omics analysis",
        },
    }


def write_yaml(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)


def test_validate_manifest_data_good():
    manifest = validate_manifest_data(good_manifest())

    assert manifest["manifest_id"] == "example_transcriptomics"
    assert manifest["modality"] == "transcriptomics"
    assert len(manifest["input_files"]) == 1


def test_validate_manifest_data_rejects_bad_modality():
    data = good_manifest()
    data["modality"] = "bad_modality"

    with pytest.raises(ValueError):
        validate_manifest_data(data)


def test_validate_manifest_file(tmp_path: Path):
    path = tmp_path / "manifest.yaml"
    write_yaml(path, good_manifest())

    manifest = validate_manifest_file(path)

    assert manifest["atlas_name"] == "brca"


def test_validate_manifest_dir(tmp_path: Path):
    manifest_dir = tmp_path / "manifests"
    write_yaml(manifest_dir / "a.yaml", good_manifest())

    data2 = good_manifest()
    data2["manifest_id"] = "example_proteomics"
    data2["modality"] = "proteomics"
    write_yaml(manifest_dir / "b.yaml", data2)

    summary_output = tmp_path / "summary.tsv"

    summary_df = validate_manifest_dir(manifest_dir, summary_output=summary_output)

    assert summary_output.exists()
    assert summary_df.shape[0] == 2
    assert set(summary_df["modality"]) == {"transcriptomics", "proteomics"}


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--manifest", "configs/data_manifests/example_transcriptomics_manifest.yaml"])

    assert str(args.manifest).replace("\\", "/").endswith(
        "configs/data_manifests/example_transcriptomics_manifest.yaml"
    )
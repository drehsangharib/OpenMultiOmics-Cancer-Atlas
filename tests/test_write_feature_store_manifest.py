from pathlib import Path

import yaml

from core.features.write_feature_store_manifest import (
    build_arg_parser,
    write_feature_store_manifest,
)


def test_write_feature_store_manifest(tmp_path: Path):
    output_path = tmp_path / "feature_store_manifest.yaml"

    manifest = write_feature_store_manifest(
        output_path=output_path,
        feature_store_id="brca_transcriptomics_feature_store",
        atlas_name="brca",
        modality="transcriptomics",
        normalized_matrix="normalized_matrix.tsv",
        sample_metadata="sample_metadata.tsv",
        feature_metadata="feature_metadata.tsv",
        qc_summary="qc_summary.tsv",
        source_manifest="manifest.yaml",
    )

    assert output_path.exists()
    assert manifest["feature_store_id"] == "brca_transcriptomics_feature_store"
    assert manifest["modality"] == "transcriptomics"

    loaded = yaml.safe_load(output_path.read_text(encoding="utf-8"))

    assert loaded["atlas_name"] == "brca"
    assert loaded["artifacts"]["normalized_matrix"] == "normalized_matrix.tsv"


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(
        [
            "--output",
            "feature_store_manifest.yaml",
            "--feature-store-id",
            "x",
            "--atlas-name",
            "brca",
            "--modality",
            "transcriptomics",
            "--normalized-matrix",
            "matrix.tsv",
            "--sample-metadata",
            "samples.tsv",
            "--feature-metadata",
            "features.tsv",
            "--qc-summary",
            "qc.tsv",
            "--source-manifest",
            "manifest.yaml",
        ]
    )

    assert str(args.output).endswith("feature_store_manifest.yaml")

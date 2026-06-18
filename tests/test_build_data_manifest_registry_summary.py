from pathlib import Path

import yaml

from core.data.build_data_manifest_registry_summary import (
    build_data_manifest_registry_summary,
    build_arg_parser,
)


def manifest(modality):
    return {
        "manifest_id": f"example_{modality}",
        "atlas_name": "example_atlas",
        "modality": modality,
        "data_type": "matrix",
        "assay": "assay",
        "species": "human",
        "source_name": "public_source",
        "source_url": "https://example.org/",
        "access_level": "public",
        "input_files": [
            {
                "file_id": "matrix",
                "path": "matrix.tsv",
                "file_format": "tsv",
                "matrix_orientation": "samples_by_features",
                "sample_id_column": "sample_id",
                "feature_id_type": "feature_id",
            }
        ],
        "sample_metadata": {
            "path": "samples.tsv",
            "sample_id_column": "sample_id",
        },
        "processing_plan": {"normalization": "none"},
        "expected_outputs": {"feature_store_dir": "outputs/features/example"},
        "agent_role": {
            "stage": "modality_preprocessing",
            "purpose": "prepare modality features",
        },
    }


def write_yaml(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)


def test_build_data_manifest_registry_summary(tmp_path: Path):
    manifest_dir = tmp_path / "manifests"
    write_yaml(manifest_dir / "transcriptomics.yaml", manifest("transcriptomics"))
    write_yaml(manifest_dir / "proteomics.yaml", manifest("proteomics"))

    summary_output = tmp_path / "summary.tsv"
    report_output = tmp_path / "report.html"

    summary_df, report_html = build_data_manifest_registry_summary(
        manifest_dir=manifest_dir,
        summary_output=summary_output,
        report_output=report_output,
    )

    assert summary_output.exists()
    assert report_output.exists()
    assert summary_df.shape[0] == 2
    assert "Data Manifest Registry Report" in report_html
    assert "transcriptomics" in report_html
    assert "proteomics" in report_html


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--manifest-dir", "configs/data_manifests"])

    assert str(args.manifest_dir).replace("\\", "/").endswith("configs/data_manifests")
from pathlib import Path

import pandas as pd
import yaml

from core.integration.build_multiomics_integration_manifest import (
    build_arg_parser,
    build_multiomics_integration_manifest,
)


def write_feature_store(tmp_path: Path, modality: str, atlas_name: str, samples):
    root = tmp_path / "features" / modality / atlas_name
    root.mkdir(parents=True, exist_ok=True)

    sample_metadata = root / "sample_metadata.tsv"
    normalized_matrix = root / "normalized_matrix.tsv"
    feature_metadata = root / "feature_metadata.tsv"
    qc_summary = root / "qc_summary.tsv"
    manifest_path = root / "feature_store_manifest.yaml"

    pd.DataFrame({"sample_id": samples}).to_csv(sample_metadata, sep="\t", index=False)
    pd.DataFrame({"sample_id": samples, f"{modality}_feature_1": range(len(samples))}).to_csv(normalized_matrix, sep="\t", index=False)
    pd.DataFrame({"feature_id": [f"{modality}_feature_1"], "feature_id_type": ["test"]}).to_csv(feature_metadata, sep="\t", index=False)
    pd.DataFrame([{"metric": "samples", "value": len(samples)}]).to_csv(qc_summary, sep="\t", index=False)

    manifest = {
        "feature_store_id": f"{atlas_name}_{modality}_feature_store",
        "atlas_name": atlas_name,
        "modality": modality,
        "artifacts": {
            "normalized_matrix": str(normalized_matrix),
            "sample_metadata": str(sample_metadata),
            "feature_metadata": str(feature_metadata),
            "qc_summary": str(qc_summary),
        },
        "source_manifest": "source.yaml",
        "created_by": "test",
        "agent_role": {"stage": "test", "purpose": "test"},
    }
    with manifest_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(manifest, handle, sort_keys=False)

    return manifest_path


def test_build_multiomics_integration_manifest(tmp_path: Path):
    atlas_name = "test_atlas"
    transcriptomics = write_feature_store(tmp_path, "transcriptomics", atlas_name, ["S1", "S2", "S3"])
    proteomics = write_feature_store(tmp_path, "proteomics", atlas_name, ["S2", "S3"])

    integration_manifest, alignment_df, modality_inventory_df, qc_summary_df, paths = build_multiomics_integration_manifest(
        atlas_name=atlas_name,
        integrated_root=tmp_path / "integrated",
        manifest_paths=[transcriptomics, proteomics],
    )

    assert paths["multiomics_integration_manifest"].exists()
    assert integration_manifest["atlas_name"] == atlas_name
    assert integration_manifest["summary"]["modality_count"] == 2
    assert integration_manifest["summary"]["union_samples"] == 3
    assert integration_manifest["summary"]["complete_case_samples"] == 2
    assert len(integration_manifest["feature_stores"]) == 2
    loaded = yaml.safe_load(paths["multiomics_integration_manifest"].read_text(encoding="utf-8"))
    assert loaded["integration_scope"] == "sample_aligned_feature_stores"


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--atlas", "brca", "--modalities", "transcriptomics", "proteomics"])
    assert args.atlas == "brca"
    assert args.modalities == ["transcriptomics", "proteomics"]

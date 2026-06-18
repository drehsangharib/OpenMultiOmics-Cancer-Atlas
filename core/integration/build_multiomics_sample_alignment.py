#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_FEATURE_ROOT = Path("outputs/features")
DEFAULT_INTEGRATED_ROOT = Path("outputs/features/integrated")
DEFAULT_MODALITIES = ["transcriptomics", "proteomics", "epigenome", "metabolomics"]


def ensure_dir(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_yaml_mapping(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"YAML file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain a mapping: {path}")
    return data


def find_feature_store_manifest(feature_root, modality, atlas_name):
    path = Path(feature_root) / modality / atlas_name / "feature_store_manifest.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Feature-store manifest not found: {path}")
    return path


def load_feature_store_manifest(path):
    manifest = load_yaml_mapping(path)
    required = ["feature_store_id", "atlas_name", "modality", "artifacts", "source_manifest", "agent_role"]
    for key in required:
        if key not in manifest:
            raise ValueError(f"Missing required feature-store manifest key '{key}' in {path}")
    artifacts = manifest.get("artifacts", {})
    for key in ["normalized_matrix", "sample_metadata", "feature_metadata", "qc_summary"]:
        if key not in artifacts or not str(artifacts[key]).strip():
            raise ValueError(f"Missing artifact '{key}' in {path}")
    return manifest


def read_sample_metadata(sample_metadata_path, sample_id_column="sample_id"):
    sample_metadata_path = Path(sample_metadata_path)
    if not sample_metadata_path.exists():
        raise FileNotFoundError(f"Sample metadata not found: {sample_metadata_path}")
    if sample_metadata_path.suffix.lower() == ".csv":
        df = pd.read_csv(sample_metadata_path)
    else:
        df = pd.read_csv(sample_metadata_path, sep="\t")
    if sample_id_column not in df.columns:
        raise ValueError(f"sample_id column '{sample_id_column}' not found in {sample_metadata_path}")
    out = df.copy()
    out[sample_id_column] = out[sample_id_column].astype(str)
    return out


def build_modality_inventory(feature_store_manifests):
    rows = []
    for modality, manifest_path, manifest in feature_store_manifests:
        artifacts = manifest["artifacts"]
        sample_df = read_sample_metadata(artifacts["sample_metadata"])
        rows.append(
            {
                "modality": modality,
                "feature_store_id": manifest["feature_store_id"],
                "atlas_name": manifest["atlas_name"],
                "feature_store_manifest": str(manifest_path),
                "normalized_matrix": str(artifacts["normalized_matrix"]),
                "sample_metadata": str(artifacts["sample_metadata"]),
                "feature_metadata": str(artifacts["feature_metadata"]),
                "qc_summary": str(artifacts["qc_summary"]),
                "sample_count": int(sample_df.shape[0]),
            }
        )
    return pd.DataFrame(rows)


def build_sample_alignment(feature_store_manifests, sample_id_column="sample_id"):
    modality_sample_sets = {}

    for modality, _, manifest in feature_store_manifests:
        sample_df = read_sample_metadata(manifest["artifacts"]["sample_metadata"], sample_id_column=sample_id_column)
        modality_sample_sets[modality] = set(sample_df[sample_id_column].astype(str))

    if not modality_sample_sets:
        raise ValueError("No feature-store manifests were provided for alignment")

    all_samples = sorted(set().union(*modality_sample_sets.values()))
    shared_samples = set.intersection(*modality_sample_sets.values()) if modality_sample_sets else set()

    rows = []
    for sample_id in all_samples:
        row = {sample_id_column: sample_id}
        present_count = 0
        for modality in sorted(modality_sample_sets):
            is_present = sample_id in modality_sample_sets[modality]
            row[f"has_{modality}"] = int(is_present)
            present_count += int(is_present)
        row["present_modality_count"] = int(present_count)
        row["is_complete_case"] = int(sample_id in shared_samples)
        rows.append(row)

    alignment_df = pd.DataFrame(rows)
    return alignment_df


def build_alignment_qc_summary(alignment_df, modality_inventory_df, sample_id_column="sample_id"):
    modality_columns = [col for col in alignment_df.columns if col.startswith("has_")]
    total_samples = int(alignment_df.shape[0])
    complete_cases = int(alignment_df["is_complete_case"].sum()) if "is_complete_case" in alignment_df.columns else 0

    rows = [
        {"metric": "modalities", "value": int(len(modality_columns))},
        {"metric": "union_samples", "value": total_samples},
        {"metric": "complete_case_samples", "value": complete_cases},
        {"metric": "modality_feature_stores", "value": int(modality_inventory_df.shape[0])},
    ]

    for column in modality_columns:
        rows.append({"metric": f"samples_{column}", "value": int(alignment_df[column].sum())})

    return pd.DataFrame(rows)


def resolve_feature_store_manifests(atlas_name, modalities, feature_root, manifest_paths=None):
    resolved = []

    if manifest_paths:
        for path in manifest_paths:
            manifest_path = Path(path)
            manifest = load_feature_store_manifest(manifest_path)
            modality = str(manifest["modality"])
            resolved.append((modality, manifest_path, manifest))
        return resolved

    for modality in modalities:
        manifest_path = find_feature_store_manifest(feature_root, modality, atlas_name)
        manifest = load_feature_store_manifest(manifest_path)
        resolved.append((modality, manifest_path, manifest))

    return resolved


def build_multiomics_sample_alignment(
    atlas_name,
    modalities=None,
    feature_root=DEFAULT_FEATURE_ROOT,
    integrated_root=DEFAULT_INTEGRATED_ROOT,
    manifest_paths=None,
    sample_id_column="sample_id",
):
    modalities = modalities or DEFAULT_MODALITIES
    feature_store_manifests = resolve_feature_store_manifests(
        atlas_name=atlas_name,
        modalities=modalities,
        feature_root=feature_root,
        manifest_paths=manifest_paths,
    )

    output_dir = ensure_dir(Path(integrated_root) / atlas_name)
    sample_alignment_path = output_dir / "sample_alignment.tsv"
    modality_inventory_path = output_dir / "modality_inventory.tsv"
    alignment_qc_path = output_dir / "alignment_qc_summary.tsv"

    modality_inventory_df = build_modality_inventory(feature_store_manifests)
    alignment_df = build_sample_alignment(feature_store_manifests, sample_id_column=sample_id_column)
    qc_summary_df = build_alignment_qc_summary(alignment_df, modality_inventory_df, sample_id_column=sample_id_column)

    alignment_df.to_csv(sample_alignment_path, sep="\t", index=False)
    modality_inventory_df.to_csv(modality_inventory_path, sep="\t", index=False)
    qc_summary_df.to_csv(alignment_qc_path, sep="\t", index=False)

    paths = {
        "output_dir": output_dir,
        "sample_alignment": sample_alignment_path,
        "modality_inventory": modality_inventory_path,
        "alignment_qc_summary": alignment_qc_path,
    }

    return alignment_df, modality_inventory_df, qc_summary_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Build multi-omics sample alignment from modality feature-store manifests."
    )
    parser.add_argument("--atlas", required=True, help="Atlas name, e.g. brca or multi_cancer")
    parser.add_argument("--modalities", nargs="*", default=DEFAULT_MODALITIES)
    parser.add_argument("--feature-root", type=Path, default=DEFAULT_FEATURE_ROOT)
    parser.add_argument("--integrated-root", type=Path, default=DEFAULT_INTEGRATED_ROOT)
    parser.add_argument("--manifest-paths", nargs="*", default=None)
    parser.add_argument("--sample-id-column", default="sample_id")
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        alignment_df, modality_inventory_df, qc_summary_df, paths = build_multiomics_sample_alignment(
            atlas_name=args.atlas,
            modalities=args.modalities,
            feature_root=args.feature_root,
            integrated_root=args.integrated_root,
            manifest_paths=args.manifest_paths,
            sample_id_column=args.sample_id_column,
        )
    except Exception as exc:
        print(f"ERROR: Multi-omics sample alignment failed: {exc}", file=sys.stderr)
        return 1

    print("Multi-omics sample alignment complete.")
    print(f"Atlas: {args.atlas}")
    print(f"Modality count: {modality_inventory_df.shape[0]}")
    print(f"Union samples: {alignment_df.shape[0]}")
    print(f"Complete-case samples: {int(alignment_df['is_complete_case'].sum())}")
    print(f"Sample alignment: {paths['sample_alignment']}")
    print(f"Modality inventory: {paths['modality_inventory']}")
    print(f"QC summary: {paths['alignment_qc_summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

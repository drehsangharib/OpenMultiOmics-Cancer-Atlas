#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

from core.integration.build_multiomics_sample_alignment import (
    DEFAULT_FEATURE_ROOT,
    DEFAULT_INTEGRATED_ROOT,
    DEFAULT_MODALITIES,
    build_multiomics_sample_alignment,
)


def write_yaml(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)


def read_qc_value(qc_df, metric):
    if qc_df.empty or "metric" not in qc_df.columns or "value" not in qc_df.columns:
        return 0
    hits = qc_df.loc[qc_df["metric"] == metric, "value"]
    if hits.empty:
        return 0
    return int(hits.iloc[0])


def build_integration_manifest_data(
    atlas_name,
    alignment_df,
    modality_inventory_df,
    qc_summary_df,
    paths,
    agent_stage="multiomics_integration_preparation",
    agent_purpose="prepare aligned modality feature stores for downstream AI multi-omics integration and biological insight generation",
):
    modalities = modality_inventory_df["modality"].astype(str).tolist() if not modality_inventory_df.empty else []

    feature_stores = []
    for _, row in modality_inventory_df.iterrows():
        feature_stores.append(
            {
                "modality": str(row["modality"]),
                "feature_store_id": str(row["feature_store_id"]),
                "feature_store_manifest": str(row["feature_store_manifest"]),
                "normalized_matrix": str(row["normalized_matrix"]),
                "sample_metadata": str(row["sample_metadata"]),
                "feature_metadata": str(row["feature_metadata"]),
                "qc_summary": str(row["qc_summary"]),
                "sample_count": int(row["sample_count"]),
            }
        )

    return {
        "integration_id": f"{atlas_name}_multiomics_integration_manifest",
        "atlas_name": str(atlas_name),
        "integration_scope": "sample_aligned_feature_stores",
        "modalities": modalities,
        "artifacts": {
            "sample_alignment": str(paths["sample_alignment"]),
            "modality_inventory": str(paths["modality_inventory"]),
            "alignment_qc_summary": str(paths["alignment_qc_summary"]),
        },
        "summary": {
            "modality_count": int(len(modalities)),
            "union_samples": int(read_qc_value(qc_summary_df, "union_samples")),
            "complete_case_samples": int(read_qc_value(qc_summary_df, "complete_case_samples")),
        },
        "feature_stores": feature_stores,
        "agent_role": {
            "stage": agent_stage,
            "purpose": agent_purpose,
        },
    }


def build_multiomics_integration_manifest(
    atlas_name,
    modalities=None,
    feature_root=DEFAULT_FEATURE_ROOT,
    integrated_root=DEFAULT_INTEGRATED_ROOT,
    manifest_paths=None,
    sample_id_column="sample_id",
):
    alignment_df, modality_inventory_df, qc_summary_df, paths = build_multiomics_sample_alignment(
        atlas_name=atlas_name,
        modalities=modalities or DEFAULT_MODALITIES,
        feature_root=feature_root,
        integrated_root=integrated_root,
        manifest_paths=manifest_paths,
        sample_id_column=sample_id_column,
    )

    integration_manifest = build_integration_manifest_data(
        atlas_name=atlas_name,
        alignment_df=alignment_df,
        modality_inventory_df=modality_inventory_df,
        qc_summary_df=qc_summary_df,
        paths=paths,
    )

    manifest_path = Path(paths["output_dir"]) / "multiomics_integration_manifest.yaml"
    write_yaml(manifest_path, integration_manifest)
    paths["multiomics_integration_manifest"] = manifest_path

    return integration_manifest, alignment_df, modality_inventory_df, qc_summary_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Build a multi-omics integration manifest from aligned modality feature stores."
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
        integration_manifest, alignment_df, modality_inventory_df, qc_summary_df, paths = build_multiomics_integration_manifest(
            atlas_name=args.atlas,
            modalities=args.modalities,
            feature_root=args.feature_root,
            integrated_root=args.integrated_root,
            manifest_paths=args.manifest_paths,
            sample_id_column=args.sample_id_column,
        )
    except Exception as exc:
        print(f"ERROR: Multi-omics integration manifest build failed: {exc}", file=sys.stderr)
        return 1

    print("Multi-omics integration manifest complete.")
    print(f"Atlas: {args.atlas}")
    print(f"Modality count: {integration_manifest['summary']['modality_count']}")
    print(f"Union samples: {integration_manifest['summary']['union_samples']}")
    print(f"Complete-case samples: {integration_manifest['summary']['complete_case_samples']}")
    print(f"Integration manifest: {paths['multiomics_integration_manifest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

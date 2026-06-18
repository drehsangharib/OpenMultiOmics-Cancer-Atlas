#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

import yaml


DEFAULT_CREATED_BY = "OpenMultiOmics-Cancer-Atlas feature-store writer"


def ensure_parent(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def build_feature_store_manifest(
    feature_store_id,
    atlas_name,
    modality,
    normalized_matrix,
    sample_metadata,
    feature_metadata,
    qc_summary,
    source_manifest,
    created_by=DEFAULT_CREATED_BY,
    agent_stage="feature_store_generation",
    agent_purpose="provide standardized modality features for downstream AI multi-omics analysis",
):
    return {
        "feature_store_id": str(feature_store_id),
        "atlas_name": str(atlas_name),
        "modality": str(modality),
        "artifacts": {
            "normalized_matrix": str(normalized_matrix),
            "sample_metadata": str(sample_metadata),
            "feature_metadata": str(feature_metadata),
            "qc_summary": str(qc_summary),
        },
        "source_manifest": str(source_manifest),
        "created_by": str(created_by),
        "agent_role": {
            "stage": str(agent_stage),
            "purpose": str(agent_purpose),
        },
    }


def write_feature_store_manifest(
    output_path,
    feature_store_id,
    atlas_name,
    modality,
    normalized_matrix,
    sample_metadata,
    feature_metadata,
    qc_summary,
    source_manifest,
    created_by=DEFAULT_CREATED_BY,
    agent_stage="feature_store_generation",
    agent_purpose="provide standardized modality features for downstream AI multi-omics analysis",
):
    output_path = ensure_parent(output_path)

    manifest = build_feature_store_manifest(
        feature_store_id=feature_store_id,
        atlas_name=atlas_name,
        modality=modality,
        normalized_matrix=normalized_matrix,
        sample_metadata=sample_metadata,
        feature_metadata=feature_metadata,
        qc_summary=qc_summary,
        source_manifest=source_manifest,
        created_by=created_by,
        agent_stage=agent_stage,
        agent_purpose=agent_purpose,
    )

    with output_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(manifest, handle, sort_keys=False)

    return manifest


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Write a standardized feature-store manifest."
    )

    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--feature-store-id", required=True)
    parser.add_argument("--atlas-name", required=True)
    parser.add_argument("--modality", required=True)
    parser.add_argument("--normalized-matrix", required=True)
    parser.add_argument("--sample-metadata", required=True)
    parser.add_argument("--feature-metadata", required=True)
    parser.add_argument("--qc-summary", required=True)
    parser.add_argument("--source-manifest", required=True)

    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        write_feature_store_manifest(
            output_path=args.output,
            feature_store_id=args.feature_store_id,
            atlas_name=args.atlas_name,
            modality=args.modality,
            normalized_matrix=args.normalized_matrix,
            sample_metadata=args.sample_metadata,
            feature_metadata=args.feature_metadata,
            qc_summary=args.qc_summary,
            source_manifest=args.source_manifest,
        )
    except Exception as exc:
        print(f"ERROR: Failed to write feature-store manifest: {exc}", file=sys.stderr)
        return 1

    print("Feature-store manifest complete.")
    print(f"Output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

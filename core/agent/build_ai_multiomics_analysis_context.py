#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml


def load_yaml_mapping(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"YAML file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain a mapping: {path}")
    return data


def read_table(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Table not found: {path}")
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_csv(path, sep="\t")


def read_qc_value(qc_df, metric):
    if qc_df.empty or "metric" not in qc_df.columns or "value" not in qc_df.columns:
        return 0
    hits = qc_df.loc[qc_df["metric"] == metric, "value"]
    if hits.empty:
        return 0
    return int(hits.iloc[0])


def build_ai_multiomics_analysis_context(
    integration_manifest_path,
    integrated_feature_matrix_path,
    feature_block_inventory_path,
    integrated_feature_qc_summary_path,
    output_path=None,
):
    integration_manifest_path = Path(integration_manifest_path)
    integrated_feature_matrix_path = Path(integrated_feature_matrix_path)
    feature_block_inventory_path = Path(feature_block_inventory_path)
    integrated_feature_qc_summary_path = Path(integrated_feature_qc_summary_path)

    integration_manifest = load_yaml_mapping(integration_manifest_path)
    feature_matrix_df = read_table(integrated_feature_matrix_path)
    feature_block_df = read_table(feature_block_inventory_path)
    qc_df = read_table(integrated_feature_qc_summary_path)

    output_path = Path(output_path) if output_path else integrated_feature_matrix_path.parent / "ai_multiomics_analysis_context.yaml"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    context = {
        "context_id": f"{integration_manifest.get('atlas_name', 'atlas')}_ai_multiomics_analysis_context",
        "atlas_name": str(integration_manifest.get("atlas_name", "")),
        "north_star": "AI-driven raw-data-to-biological-insight platform for transcriptome, proteome, epigenome, metabolome, and multi-omics integration",
        "analysis_scope": "multiomics_integrated_feature_table",
        "inputs": {
            "multiomics_integration_manifest": str(integration_manifest_path),
            "integrated_feature_matrix": str(integrated_feature_matrix_path),
            "feature_block_inventory": str(feature_block_inventory_path),
            "integrated_feature_qc_summary": str(integrated_feature_qc_summary_path),
        },
        "readiness_summary": {
            "modalities": int(read_qc_value(qc_df, "modalities")),
            "samples": int(read_qc_value(qc_df, "samples")),
            "integrated_features": int(read_qc_value(qc_df, "integrated_features")),
            "missing_values": int(read_qc_value(qc_df, "missing_values")),
            "feature_blocks": int(feature_block_df.shape[0]),
            "matrix_rows": int(feature_matrix_df.shape[0]),
            "matrix_columns": int(feature_matrix_df.shape[1]),
        },
        "recommended_agent_tasks": [
            "confirm modality coverage and sample overlap",
            "screen integrated feature matrix for missingness and scale compatibility",
            "run unsupervised sample clustering as a first biological-state discovery step",
            "rank modality blocks by contribution after downstream modeling is added",
            "generate biological interpretation reports from selected features and pathways",
        ],
        "agent_role": {
            "stage": "ai_multiomics_analysis_preparation",
            "purpose": "provide a structured context object for downstream AI multi-omics analysis and biological insight generation",
        },
    }

    with output_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(context, handle, sort_keys=False)

    return context, output_path


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Build an AI multi-omics analysis context YAML from integrated feature-table outputs."
    )
    parser.add_argument("--integration-manifest", required=True, type=Path)
    parser.add_argument("--integrated-feature-matrix", required=True, type=Path)
    parser.add_argument("--feature-block-inventory", required=True, type=Path)
    parser.add_argument("--integrated-feature-qc-summary", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        context, output_path = build_ai_multiomics_analysis_context(
            integration_manifest_path=args.integration_manifest,
            integrated_feature_matrix_path=args.integrated_feature_matrix,
            feature_block_inventory_path=args.feature_block_inventory,
            integrated_feature_qc_summary_path=args.integrated_feature_qc_summary,
            output_path=args.output,
        )
    except Exception as exc:
        print(f"ERROR: AI multi-omics analysis context build failed: {exc}", file=sys.stderr)
        return 1

    print("AI multi-omics analysis context complete.")
    print(f"Atlas: {context['atlas_name']}")
    print(f"Samples: {context['readiness_summary']['samples']}")
    print(f"Integrated features: {context['readiness_summary']['integrated_features']}")
    print(f"Output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

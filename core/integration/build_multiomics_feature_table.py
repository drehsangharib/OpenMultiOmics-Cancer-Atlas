#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_OUTPUT_NAMES = {
    "integrated_feature_matrix": "integrated_feature_matrix.tsv",
    "feature_block_inventory": "feature_block_inventory.tsv",
    "integrated_feature_qc_summary": "integrated_feature_qc_summary.tsv",
}


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


def ensure_dir(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_output_dir_from_manifest(integration_manifest_path, integration_manifest):
    artifacts = integration_manifest.get("artifacts", {})
    sample_alignment = artifacts.get("sample_alignment", "")
    if sample_alignment:
        return Path(sample_alignment).parent
    return Path(integration_manifest_path).parent


def select_samples(sample_alignment_df, sample_id_column="sample_id", complete_cases_only=True):
    if sample_id_column not in sample_alignment_df.columns:
        raise ValueError(f"sample_id column '{sample_id_column}' missing from sample alignment table")
    if complete_cases_only and "is_complete_case" in sample_alignment_df.columns:
        selected = sample_alignment_df.loc[sample_alignment_df["is_complete_case"].astype(int) == 1, sample_id_column]
    else:
        selected = sample_alignment_df[sample_id_column]
    return pd.DataFrame({sample_id_column: selected.astype(str).tolist()})


def load_and_prefix_modality_matrix(feature_store, sample_id_column="sample_id"):
    modality = str(feature_store["modality"])
    matrix_path = feature_store["normalized_matrix"]
    matrix_df = read_table(matrix_path)
    if sample_id_column not in matrix_df.columns:
        raise ValueError(f"sample_id column '{sample_id_column}' missing from {matrix_path}")

    matrix_df = matrix_df.copy()
    matrix_df[sample_id_column] = matrix_df[sample_id_column].astype(str)
    feature_columns = [column for column in matrix_df.columns if column != sample_id_column]
    renamed = {column: f"{modality}__{column}" for column in feature_columns}
    matrix_df = matrix_df.rename(columns=renamed)

    block = {
        "modality": modality,
        "feature_store_id": str(feature_store.get("feature_store_id", "")),
        "normalized_matrix": str(matrix_path),
        "input_feature_count": int(len(feature_columns)),
        "prefixed_feature_count": int(len(feature_columns)),
        "feature_prefix": f"{modality}__",
    }
    return matrix_df, block


def build_integrated_feature_table(
    integration_manifest_path,
    output_dir=None,
    sample_id_column="sample_id",
    complete_cases_only=True,
):
    integration_manifest_path = Path(integration_manifest_path)
    integration_manifest = load_yaml_mapping(integration_manifest_path)

    artifacts = integration_manifest.get("artifacts", {})
    sample_alignment_path = artifacts.get("sample_alignment")
    if not sample_alignment_path:
        raise ValueError("integration manifest missing artifacts.sample_alignment")

    feature_stores = integration_manifest.get("feature_stores", [])
    if not feature_stores:
        raise ValueError("integration manifest has no feature_stores entries")

    sample_alignment_df = read_table(sample_alignment_path)
    integrated_df = select_samples(
        sample_alignment_df,
        sample_id_column=sample_id_column,
        complete_cases_only=complete_cases_only,
    )

    feature_blocks = []
    for feature_store in feature_stores:
        modality_df, block = load_and_prefix_modality_matrix(feature_store, sample_id_column=sample_id_column)
        integrated_df = integrated_df.merge(modality_df, on=sample_id_column, how="left")
        block["samples_in_matrix"] = int(modality_df.shape[0])
        feature_blocks.append(block)

    output_dir = ensure_dir(output_dir or get_output_dir_from_manifest(integration_manifest_path, integration_manifest))
    integrated_feature_matrix_path = output_dir / DEFAULT_OUTPUT_NAMES["integrated_feature_matrix"]
    feature_block_inventory_path = output_dir / DEFAULT_OUTPUT_NAMES["feature_block_inventory"]
    qc_summary_path = output_dir / DEFAULT_OUTPUT_NAMES["integrated_feature_qc_summary"]

    feature_block_inventory_df = pd.DataFrame(feature_blocks)
    feature_columns = [column for column in integrated_df.columns if column != sample_id_column]
    missing_values = int(integrated_df[feature_columns].isna().sum().sum()) if feature_columns else 0

    qc_summary_df = pd.DataFrame(
        [
            {"metric": "modalities", "value": int(len(feature_blocks))},
            {"metric": "samples", "value": int(integrated_df.shape[0])},
            {"metric": "integrated_features", "value": int(len(feature_columns))},
            {"metric": "missing_values", "value": int(missing_values)},
            {"metric": "complete_cases_only", "value": int(bool(complete_cases_only))},
        ]
    )

    integrated_df.to_csv(integrated_feature_matrix_path, sep="\t", index=False)
    feature_block_inventory_df.to_csv(feature_block_inventory_path, sep="\t", index=False)
    qc_summary_df.to_csv(qc_summary_path, sep="\t", index=False)

    paths = {
        "integrated_feature_matrix": integrated_feature_matrix_path,
        "feature_block_inventory": feature_block_inventory_path,
        "integrated_feature_qc_summary": qc_summary_path,
    }

    return integrated_df, feature_block_inventory_df, qc_summary_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Build an integration-ready multi-omics feature table from a multi-omics integration manifest."
    )
    parser.add_argument("--integration-manifest", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--sample-id-column", default="sample_id")
    parser.add_argument("--all-union-samples", action="store_true", help="Use union samples instead of complete-case samples.")
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        integrated_df, feature_block_inventory_df, qc_summary_df, paths = build_integrated_feature_table(
            integration_manifest_path=args.integration_manifest,
            output_dir=args.output_dir,
            sample_id_column=args.sample_id_column,
            complete_cases_only=not args.all_union_samples,
        )
    except Exception as exc:
        print(f"ERROR: Integrated feature table build failed: {exc}", file=sys.stderr)
        return 1

    print("Integrated multi-omics feature table complete.")
    print(f"Samples: {integrated_df.shape[0]}")
    print(f"Feature blocks: {feature_block_inventory_df.shape[0]}")
    print(f"Integrated features: {max(integrated_df.shape[1] - 1, 0)}")
    print(f"Integrated feature matrix: {paths['integrated_feature_matrix']}")
    print(f"Feature block inventory: {paths['feature_block_inventory']}")
    print(f"QC summary: {paths['integrated_feature_qc_summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

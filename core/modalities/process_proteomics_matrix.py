#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

import pandas as pd

from core.data.validate_data_manifest import validate_manifest_file
from core.features.write_feature_store_manifest import write_feature_store_manifest


def ensure_dir(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_matrix(input_file):
    path = Path(input_file["path"])
    if not path.exists():
        raise FileNotFoundError(f"Proteomics matrix not found: {path}")
    file_format = str(input_file.get("file_format", "tsv")).lower()
    if file_format == "tsv":
        return pd.read_csv(path, sep="\t")
    if file_format == "csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported matrix file_format: {file_format}")


def orient_matrix(df, input_file):
    orientation = input_file["matrix_orientation"]
    sample_id_column = input_file["sample_id_column"]
    if orientation == "samples_by_features":
        if sample_id_column not in df.columns:
            raise ValueError(f"sample_id_column '{sample_id_column}' not found in matrix")
        return df.copy()
    if orientation == "features_by_samples":
        feature_id_column = df.columns[0]
        transposed = df.set_index(feature_id_column).T.reset_index()
        return transposed.rename(columns={"index": sample_id_column})
    raise ValueError(f"Unsupported matrix_orientation: {orientation}")


def numeric_feature_matrix(df, sample_id_column):
    sample_ids = df[sample_id_column].astype(str)
    feature_df = df.drop(columns=[sample_id_column]).apply(pd.to_numeric, errors="coerce")
    feature_df.insert(0, sample_id_column, sample_ids)
    return feature_df


def remove_high_missingness_features(df, sample_id_column, max_missing_fraction):
    keep = []
    removed = []
    for column in df.columns:
        if column == sample_id_column:
            continue
        if float(df[column].isna().mean()) <= max_missing_fraction:
            keep.append(column)
        else:
            removed.append(column)
    return df[[sample_id_column] + keep].copy(), removed


def impute_half_minimum(df, sample_id_column):
    out = df.copy()
    for column in out.columns:
        if column == sample_id_column:
            continue
        non_missing = out[column].dropna()
        if non_missing.empty:
            fill_value = 0.0
        else:
            minimum = float(non_missing.min())
            fill_value = minimum / 2.0 if minimum > 0 else minimum
        out[column] = out[column].fillna(fill_value)
    return out


def median_center(df, sample_id_column):
    out = df.copy()
    for column in out.columns:
        if column == sample_id_column:
            continue
        median_value = out[column].median()
        if pd.isna(median_value):
            median_value = 0.0
        out[column] = out[column] - median_value
    return out


def remove_zero_variance_features(df, sample_id_column):
    keep = []
    removed = []
    for column in df.columns:
        if column == sample_id_column:
            continue
        if df[column].nunique(dropna=False) > 1:
            keep.append(column)
        else:
            removed.append(column)
    return df[[sample_id_column] + keep].copy(), removed


def build_sample_metadata(df, sample_id_column, manifest):
    sample_metadata_path = Path(str(manifest.get("sample_metadata", {}).get("path", "")))
    if sample_metadata_path.exists():
        if sample_metadata_path.suffix.lower() == ".csv":
            return pd.read_csv(sample_metadata_path)
        return pd.read_csv(sample_metadata_path, sep="\t")
    return pd.DataFrame({sample_id_column: df[sample_id_column].astype(str)})


def build_feature_metadata(df, sample_id_column, manifest):
    feature_metadata_path = Path(str((manifest.get("feature_metadata", {}) or {}).get("path", "")))
    if feature_metadata_path.exists():
        if feature_metadata_path.suffix.lower() == ".csv":
            return pd.read_csv(feature_metadata_path)
        return pd.read_csv(feature_metadata_path, sep="\t")
    feature_columns = [column for column in df.columns if column != sample_id_column]
    return pd.DataFrame({"feature_id": feature_columns, "feature_id_type": manifest["input_files"][0]["feature_id_type"]})


def build_qc_summary(raw_df, numeric_df, filtered_df, normalized_df, sample_id_column, high_missingness_removed, zero_variance_removed):
    missing_values = int(numeric_df.drop(columns=[sample_id_column]).isna().sum().sum())
    return pd.DataFrame([
        {"metric": "samples", "value": int(normalized_df.shape[0])},
        {"metric": "raw_features", "value": int(max(raw_df.shape[1] - 1, 0))},
        {"metric": "numeric_features", "value": int(max(numeric_df.shape[1] - 1, 0))},
        {"metric": "features_after_missingness_filter", "value": int(max(filtered_df.shape[1] - 1, 0))},
        {"metric": "normalized_features", "value": int(max(normalized_df.shape[1] - 1, 0))},
        {"metric": "removed_high_missingness_features", "value": int(len(high_missingness_removed))},
        {"metric": "removed_zero_variance_features", "value": int(len(zero_variance_removed))},
        {"metric": "missing_numeric_values_before_imputation", "value": missing_values},
    ])


def resolve_output_paths(manifest):
    atlas_name = manifest["atlas_name"]
    expected_outputs = manifest.get("expected_outputs", {})
    feature_store_dir = Path(expected_outputs.get("feature_store_dir", f"outputs/features/proteomics/{atlas_name}"))
    ensure_dir(feature_store_dir)
    return {
        "feature_store_dir": feature_store_dir,
        "normalized_matrix": Path(expected_outputs.get("normalized_matrix", feature_store_dir / "normalized_matrix.tsv")),
        "sample_metadata": Path(expected_outputs.get("sample_metadata", feature_store_dir / "sample_metadata.tsv")),
        "feature_metadata": Path(expected_outputs.get("feature_metadata", feature_store_dir / "feature_metadata.tsv")),
        "qc_summary": Path(expected_outputs.get("qc_summary", feature_store_dir / "qc_summary.tsv")),
        "feature_store_manifest": feature_store_dir / "feature_store_manifest.yaml",
    }


def process_proteomics_manifest(manifest_path):
    manifest_path = Path(manifest_path)
    manifest = validate_manifest_file(manifest_path)
    if manifest["modality"] != "proteomics":
        raise ValueError(f"Manifest modality must be proteomics, got: {manifest['modality']}")
    input_file = manifest["input_files"][0]
    sample_id_column = input_file["sample_id_column"]
    processing_plan = manifest.get("processing_plan", {})
    raw_df = read_matrix(input_file)
    oriented_df = orient_matrix(raw_df, input_file)
    numeric_df = numeric_feature_matrix(oriented_df, sample_id_column)
    max_missing_fraction = float(processing_plan.get("max_missing_fraction", 0.5))
    filtered_df, high_missingness_removed = remove_high_missingness_features(numeric_df, sample_id_column, max_missing_fraction)
    imputed_df = impute_half_minimum(filtered_df, sample_id_column)
    normalized_df = median_center(imputed_df, sample_id_column)
    normalized_df, zero_variance_removed = remove_zero_variance_features(normalized_df, sample_id_column)
    sample_metadata_df = build_sample_metadata(normalized_df, sample_id_column, manifest)
    feature_metadata_df = build_feature_metadata(normalized_df, sample_id_column, manifest)
    qc_summary_df = build_qc_summary(raw_df, numeric_df, filtered_df, normalized_df, sample_id_column, high_missingness_removed, zero_variance_removed)
    paths = resolve_output_paths(manifest)
    for key in ["normalized_matrix", "sample_metadata", "feature_metadata", "qc_summary"]:
        paths[key].parent.mkdir(parents=True, exist_ok=True)
    normalized_df.to_csv(paths["normalized_matrix"], sep="\t", index=False)
    sample_metadata_df.to_csv(paths["sample_metadata"], sep="\t", index=False)
    feature_metadata_df.to_csv(paths["feature_metadata"], sep="\t", index=False)
    qc_summary_df.to_csv(paths["qc_summary"], sep="\t", index=False)
    feature_store_manifest = write_feature_store_manifest(
        output_path=paths["feature_store_manifest"],
        feature_store_id=f"{manifest['atlas_name']}_proteomics_feature_store",
        atlas_name=manifest["atlas_name"],
        modality="proteomics",
        normalized_matrix=paths["normalized_matrix"],
        sample_metadata=paths["sample_metadata"],
        feature_metadata=paths["feature_metadata"],
        qc_summary=paths["qc_summary"],
        source_manifest=manifest_path,
        agent_stage="modality_preprocessing",
        agent_purpose="provide proteomic features for downstream AI multi-omics analysis",
    )
    return normalized_df, qc_summary_df, feature_store_manifest, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Process a proteomics matrix from a validated data manifest into a feature store.")
    parser.add_argument("--manifest", required=True, type=Path, help="Proteomics data manifest YAML.")
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        normalized_df, _, _, paths = process_proteomics_manifest(args.manifest)
    except Exception as exc:
        print(f"ERROR: Proteomics processing failed: {exc}", file=sys.stderr)
        return 1
    print("Proteomics feature-store processing complete.")
    print(f"Samples: {normalized_df.shape[0]}")
    print(f"Features: {max(normalized_df.shape[1] - 1, 0)}")
    print(f"Normalized matrix: {paths['normalized_matrix']}")
    print(f"QC summary: {paths['qc_summary']}")
    print(f"Feature-store manifest: {paths['feature_store_manifest']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

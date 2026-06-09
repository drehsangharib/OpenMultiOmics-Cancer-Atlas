#!/usr/bin/env python3

"""
GDC Project Modality Matrix

Project:
    OpenMultiOmics-Cancer-Atlas

Purpose:
    Convert a GDC file-count summary into a project-level modality matrix.

Input:
    outputs/dataset_inventory/gdc_file_counts_by_project.tsv

Output:
    outputs/dataset_inventory/gdc_project_modality_matrix.tsv

Example:
    python -m core.search.gdc_project_modality_matrix
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


DEFAULT_FILE_COUNTS = Path("outputs/dataset_inventory/gdc_file_counts_by_project.tsv")
DEFAULT_OUTPUT = Path("outputs/dataset_inventory/gdc_project_modality_matrix.tsv")


MODALITY_COLUMNS = [
    "transcriptomics",
    "methylation",
    "snv",
    "cnv",
    "structural_variation",
    "clinical",
    "biospecimen",
    "proteomics",
    "slide_images",
    "sequencing_reads",
]


OUTPUT_COLUMNS = [
    "project_id",
    "has_transcriptomics",
    "has_methylation",
    "has_snv",
    "has_cnv",
    "has_structural_variation",
    "has_clinical",
    "has_biospecimen",
    "has_proteomics",
    "has_slide_images",
    "has_sequencing_reads",
    "transcriptomics_file_count",
    "methylation_file_count",
    "snv_file_count",
    "cnv_file_count",
    "structural_variation_file_count",
    "clinical_file_count",
    "biospecimen_file_count",
    "proteomics_file_count",
    "slide_image_file_count",
    "sequencing_read_file_count",
    "open_file_count",
    "controlled_file_count",
    "total_file_count",
    "dominant_data_category",
    "dominant_data_category_file_count",
    "source_database",
    "atlas_scope",
    "public_data_use",
]


REQUIRED_INPUT_COLUMNS = [
    "project_id",
    "data_category",
    "data_type",
    "experimental_strategy",
    "workflow_type",
    "data_format",
    "access",
    "file_count",
]


def normalize_text(value: object) -> str:
    """
    Normalize values for robust rule-based matching.
    """
    if pd.isna(value):
        return ""
    return str(value).strip()


def normalize_lower(value: object) -> str:
    """
    Normalize values to lowercase strings.
    """
    return normalize_text(value).lower()


def parse_file_count(value: object) -> int:
    """
    Convert file_count values to integer counts.

    Invalid or missing values become zero.
    """
    try:
        return int(value)
    except Exception:
        return 0


def validate_file_counts_input(df: pd.DataFrame) -> None:
    """
    Validate that the input file-count DataFrame has required columns.
    """
    missing = [col for col in REQUIRED_INPUT_COLUMNS if col not in df.columns]

    if missing:
        raise ValueError(
            "Missing required columns in file-count input: " + ", ".join(missing)
        )


def classify_modalities_for_row(row: pd.Series) -> Dict[str, bool]:
    """
    Classify one GDC file-count row into broad atlas modalities.

    This is intentionally transparent and rule-based. Future versions can refine
    this mapping with more detailed data_type and experimental_strategy rules.
    """
    data_category = normalize_lower(row.get("data_category", ""))
    data_type = normalize_lower(row.get("data_type", ""))
    experimental_strategy = normalize_lower(row.get("experimental_strategy", ""))

    is_transcriptomics = data_category == "transcriptome profiling"

    is_methylation = data_category == "dna methylation"

    is_snv = data_category == "simple nucleotide variation"

    is_cnv = data_category == "copy number variation"

    is_structural_variation = data_category in {
        "structural variation",
        "somatic structural variation",
    }

    is_clinical = data_category == "clinical"

    is_biospecimen = data_category == "biospecimen"

    is_proteomics = data_category == "proteome profiling"

    is_slide_images = data_type == "slide image"

    is_sequencing_reads = data_category == "sequencing reads"

    # Secondary safety checks using experimental strategy.
    if experimental_strategy in {"rna-seq", "mirna-seq"}:
        is_transcriptomics = True

    if experimental_strategy in {"methylation array"}:
        is_methylation = True

    if experimental_strategy in {"wxs", "wgs"} and "mutation" in data_type:
        is_snv = True

    return {
        "transcriptomics": is_transcriptomics,
        "methylation": is_methylation,
        "snv": is_snv,
        "cnv": is_cnv,
        "structural_variation": is_structural_variation,
        "clinical": is_clinical,
        "biospecimen": is_biospecimen,
        "proteomics": is_proteomics,
        "slide_images": is_slide_images,
        "sequencing_reads": is_sequencing_reads,
    }


def add_modality_flags(file_counts_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add boolean modality classification columns to the long file-count table.
    """
    validate_file_counts_input(file_counts_df)

    df = file_counts_df.copy()

    for modality in MODALITY_COLUMNS:
        df[f"is_{modality}"] = False

    for idx, row in df.iterrows():
        flags = classify_modalities_for_row(row)

        for modality, flag in flags.items():
            df.at[idx, f"is_{modality}"] = bool(flag)

    df["file_count"] = df["file_count"].apply(parse_file_count)

    return df


def compute_modality_count(
    project_df: pd.DataFrame,
    modality: str,
) -> int:
    """
    Sum file_count for rows assigned to one modality.
    """
    flag_col = f"is_{modality}"

    if flag_col not in project_df.columns:
        return 0

    return int(project_df.loc[project_df[flag_col], "file_count"].sum())


def compute_access_count(
    project_df: pd.DataFrame,
    access_value: str,
) -> int:
    """
    Sum file_count for rows with a specific access level.
    """
    access_norm = project_df["access"].apply(normalize_lower)
    return int(project_df.loc[access_norm == access_value.lower(), "file_count"].sum())


def compute_dominant_data_category(project_df: pd.DataFrame) -> Dict[str, object]:
    """
    Compute the most abundant data_category for one project.
    """
    if project_df.empty:
        return {
            "dominant_data_category": "",
            "dominant_data_category_file_count": 0,
        }

    category_counts = (
        project_df.groupby("data_category")["file_count"]
        .sum()
        .sort_values(ascending=False)
    )

    if category_counts.empty:
        return {
            "dominant_data_category": "",
            "dominant_data_category_file_count": 0,
        }

    return {
        "dominant_data_category": str(category_counts.index[0]),
        "dominant_data_category_file_count": int(category_counts.iloc[0]),
    }


def summarize_project_modalities(flagged_df: pd.DataFrame) -> pd.DataFrame:
    """
    Collapse long file-count metadata into one row per project.
    """
    if flagged_df.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    rows: List[Dict[str, object]] = []

    for project_id, project_df in flagged_df.groupby("project_id", dropna=False):
        modality_counts = {
            modality: compute_modality_count(project_df, modality)
            for modality in MODALITY_COLUMNS
        }

        total_file_count = int(project_df["file_count"].sum())
        open_file_count = compute_access_count(project_df, "open")
        controlled_file_count = compute_access_count(project_df, "controlled")
        dominant = compute_dominant_data_category(project_df)

        row: Dict[str, object] = {
            "project_id": str(project_id),
            "has_transcriptomics": modality_counts["transcriptomics"] > 0,
            "has_methylation": modality_counts["methylation"] > 0,
            "has_snv": modality_counts["snv"] > 0,
            "has_cnv": modality_counts["cnv"] > 0,
            "has_structural_variation": modality_counts["structural_variation"] > 0,
            "has_clinical": modality_counts["clinical"] > 0,
            "has_biospecimen": modality_counts["biospecimen"] > 0,
            "has_proteomics": modality_counts["proteomics"] > 0,
            "has_slide_images": modality_counts["slide_images"] > 0,
            "has_sequencing_reads": modality_counts["sequencing_reads"] > 0,
            "transcriptomics_file_count": modality_counts["transcriptomics"],
            "methylation_file_count": modality_counts["methylation"],
            "snv_file_count": modality_counts["snv"],
            "cnv_file_count": modality_counts["cnv"],
            "structural_variation_file_count": modality_counts["structural_variation"],
            "clinical_file_count": modality_counts["clinical"],
            "biospecimen_file_count": modality_counts["biospecimen"],
            "proteomics_file_count": modality_counts["proteomics"],
            "slide_image_file_count": modality_counts["slide_images"],
            "sequencing_read_file_count": modality_counts["sequencing_reads"],
            "open_file_count": open_file_count,
            "controlled_file_count": controlled_file_count,
            "total_file_count": total_file_count,
            "dominant_data_category": dominant["dominant_data_category"],
            "dominant_data_category_file_count": dominant[
                "dominant_data_category_file_count"
            ],
            "source_database": "GDC",
            "atlas_scope": "pan_cancer_public_reference",
            "public_data_use": "project_modality_matrix",
        }

        rows.append(row)

    out = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)

    if not out.empty:
        out = out.sort_values(
            by=["project_id"],
            ascending=True,
            kind="stable",
        ).reset_index(drop=True)

    return out


def build_project_modality_matrix(file_counts_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a project-level modality matrix from long file-count metadata.
    """
    flagged_df = add_modality_flags(file_counts_df)
    matrix_df = summarize_project_modalities(flagged_df)
    return matrix_df


def read_file_counts(input_path: Path) -> pd.DataFrame:
    """
    Read a GDC file-count TSV.
    """
    if not input_path.exists():
        raise FileNotFoundError(
            f"File-count input not found: {input_path}. "
            "Run `python -m core.search.gdc_file_counts_by_project` first."
        )

    df = pd.read_csv(input_path, sep="\t")
    validate_file_counts_input(df)
    return df


def write_matrix(matrix_df: pd.DataFrame, output_path: Path) -> None:
    """
    Write project modality matrix TSV.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    matrix_df.to_csv(output_path, sep="\t", index=False)


def build_gdc_project_modality_matrix(
    input_path: Path = DEFAULT_FILE_COUNTS,
    output_path: Path = DEFAULT_OUTPUT,
) -> pd.DataFrame:
    """
    Read file counts, build project modality matrix, and write output.
    """
    file_counts_df = read_file_counts(input_path)
    matrix_df = build_project_modality_matrix(file_counts_df)
    write_matrix(matrix_df, output_path)
    return matrix_df


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a GDC project-level modality matrix from file counts."
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_FILE_COUNTS,
        help=f"Input GDC file-count TSV. Default: {DEFAULT_FILE_COUNTS}",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output modality matrix TSV. Default: {DEFAULT_OUTPUT}",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        matrix_df = build_gdc_project_modality_matrix(
            input_path=args.input,
            output_path=args.output,
        )
    except Exception as exc:
        print(f"ERROR: Failed to build GDC project modality matrix: {exc}", file=sys.stderr)
        return 1

    print("GDC project modality matrix complete.")
    print(f"Rows: {len(matrix_df)}")
    print(f"Output: {args.output}")

    if not matrix_df.empty:
        print("Projects with modality availability:")
        for modality in [
            "transcriptomics",
            "methylation",
            "snv",
            "cnv",
            "structural_variation",
            "clinical",
            "biospecimen",
            "proteomics",
            "slide_images",
            "sequencing_reads",
        ]:
            col = f"has_{modality}"
            count = int(matrix_df[col].sum())
            print(f"  {modality}: {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
#!/usr/bin/env python3

"""
GDC Project Priority Ranker

Project:
    OpenMultiOmics-Cancer-Atlas

Purpose:
    Join GDC project-level metadata with the GDC project modality matrix and
    produce a ranked project prioritization table for public cancer multi-omics
    atlas construction.

Inputs:
    outputs/dataset_inventory/gdc_project_inventory.tsv
    outputs/dataset_inventory/gdc_project_modality_matrix.tsv

Output:
    outputs/ranked_datasets/gdc_project_priority_ranking.tsv

Example:
    python -m core.scoring.gdc_project_priority_ranker
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


DEFAULT_PROJECT_INVENTORY = Path("outputs/dataset_inventory/gdc_project_inventory.tsv")
DEFAULT_MODALITY_MATRIX = Path("outputs/dataset_inventory/gdc_project_modality_matrix.tsv")
DEFAULT_OUTPUT = Path("outputs/ranked_datasets/gdc_project_priority_ranking.tsv")


PROJECT_REQUIRED_COLUMNS = [
    "project_id",
    "project_name",
    "program_name",
    "primary_site",
    "disease_type",
    "case_count",
    "file_count",
]


MODALITY_REQUIRED_COLUMNS = [
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
]


OUTPUT_COLUMNS = [
    "rank",
    "project_id",
    "project_name",
    "program_name",
    "primary_site",
    "disease_type",
    "case_count",
    "file_count",
    "total_file_count",
    "open_file_count",
    "controlled_file_count",
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
    "multiomics_modality_count",
    "multiomics_score",
    "clinical_utility_score",
    "open_data_score",
    "case_count_score",
    "proteogenomics_bonus",
    "priority_score",
    "priority_label",
    "priority_rationale",
    "source_database",
    "atlas_scope",
    "public_data_use",
]


MODALITY_FLAG_COLUMNS = [
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
]


def parse_int(value: object) -> int:
    """
    Convert values to integer, returning zero for missing or invalid values.
    """
    try:
        if pd.isna(value):
            return 0
        return int(float(value))
    except Exception:
        return 0


def parse_bool(value: object) -> bool:
    """
    Convert common bool-like values into Python booleans.
    """
    if isinstance(value, bool):
        return value

    if pd.isna(value):
        return False

    text = str(value).strip().lower()

    if text in {"true", "1", "yes", "y"}:
        return True

    if text in {"false", "0", "no", "n", ""}:
        return False

    return False


def validate_columns(df: pd.DataFrame, required_columns: List[str], name: str) -> None:
    """
    Validate required columns in a DataFrame.
    """
    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        raise ValueError(
            f"Missing required columns in {name}: " + ", ".join(missing)
        )


def read_tsv(path: Path, required_columns: List[str], name: str) -> pd.DataFrame:
    """
    Read and validate a TSV file.
    """
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    df = pd.read_csv(path, sep="\t")
    validate_columns(df, required_columns, name=name)

    return df


def clean_project_inventory(project_df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean project metadata fields and numeric counts.
    """
    out = project_df.copy()

    for col in ["project_id", "project_name", "program_name", "primary_site", "disease_type"]:
        out[col] = out[col].fillna("").astype(str)

    out["case_count"] = out["case_count"].apply(parse_int)
    out["file_count"] = out["file_count"].apply(parse_int)

    return out


def clean_modality_matrix(modality_df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean modality flags and count columns.
    """
    out = modality_df.copy()
    out["project_id"] = out["project_id"].fillna("").astype(str)

    for col in MODALITY_FLAG_COLUMNS:
        out[col] = out[col].apply(parse_bool)

    count_cols = [
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
    ]

    for col in count_cols:
        out[col] = out[col].apply(parse_int)

    return out


def compute_case_count_score(case_count: int) -> int:
    """
    Score projects by cohort size.
    """
    if case_count >= 1000:
        return 5
    if case_count >= 500:
        return 4
    if case_count >= 200:
        return 3
    if case_count >= 50:
        return 2
    if case_count > 0:
        return 1
    return 0


def compute_open_data_score(open_file_count: int, total_file_count: int) -> int:
    """
    Score projects by open file availability and open-data fraction.
    """
    if total_file_count <= 0:
        return 0

    open_fraction = open_file_count / total_file_count

    score = 0

    if open_file_count >= 5000:
        score += 3
    elif open_file_count >= 1000:
        score += 2
    elif open_file_count > 0:
        score += 1

    if open_fraction >= 0.75:
        score += 2
    elif open_fraction >= 0.50:
        score += 1

    return score


def compute_multiomics_score(row: pd.Series) -> int:
    """
    Score broad multi-omics data availability.

    Weighted to prioritize molecular omics plus clinical context.
    """
    score = 0

    if parse_bool(row.get("has_transcriptomics", False)):
        score += 3

    if parse_bool(row.get("has_methylation", False)):
        score += 2

    if parse_bool(row.get("has_snv", False)):
        score += 2

    if parse_bool(row.get("has_cnv", False)):
        score += 2

    if parse_bool(row.get("has_structural_variation", False)):
        score += 1

    if parse_bool(row.get("has_clinical", False)):
        score += 2

    if parse_bool(row.get("has_biospecimen", False)):
        score += 1

    if parse_bool(row.get("has_proteomics", False)):
        score += 3

    if parse_bool(row.get("has_slide_images", False)):
        score += 1

    if parse_bool(row.get("has_sequencing_reads", False)):
        score += 1

    return score


def compute_clinical_utility_score(row: pd.Series) -> int:
    """
    Score clinical/biospecimen utility.
    """
    score = 0

    if parse_bool(row.get("has_clinical", False)):
        score += 3

    if parse_bool(row.get("has_biospecimen", False)):
        score += 2

    if parse_bool(row.get("has_slide_images", False)):
        score += 1

    if parse_int(row.get("clinical_file_count", 0)) >= 100:
        score += 1

    return score


def compute_proteogenomics_bonus(row: pd.Series) -> int:
    """
    Bonus for projects useful for proteogenomics-style analysis.
    """
    has_proteomics = parse_bool(row.get("has_proteomics", False))
    has_transcriptomics = parse_bool(row.get("has_transcriptomics", False))
    has_snv = parse_bool(row.get("has_snv", False))
    has_cnv = parse_bool(row.get("has_cnv", False))

    if has_proteomics and has_transcriptomics and (has_snv or has_cnv):
        return 3

    if has_proteomics and has_transcriptomics:
        return 2

    if has_proteomics:
        return 1

    return 0


def compute_multiomics_modality_count(row: pd.Series) -> int:
    """
    Count how many broad modality flags are available.
    """
    return int(sum(parse_bool(row.get(col, False)) for col in MODALITY_FLAG_COLUMNS))


def assign_priority_label(priority_score: int) -> str:
    """
    Convert numeric priority scores into human-readable labels.
    """
    if priority_score >= 30:
        return "excellent"
    if priority_score >= 24:
        return "high"
    if priority_score >= 16:
        return "medium"
    if priority_score >= 8:
        return "low"
    return "very_low"


def build_priority_rationale(row: pd.Series) -> str:
    """
    Build a short transparent rationale for each project score.
    """
    reasons: List[str] = []

    if parse_bool(row.get("has_transcriptomics", False)):
        reasons.append("transcriptomics")

    if parse_bool(row.get("has_methylation", False)):
        reasons.append("methylation")

    if parse_bool(row.get("has_snv", False)):
        reasons.append("SNV")

    if parse_bool(row.get("has_cnv", False)):
        reasons.append("CNV")

    if parse_bool(row.get("has_proteomics", False)):
        reasons.append("proteomics")

    if parse_bool(row.get("has_clinical", False)):
        reasons.append("clinical")

    if parse_bool(row.get("has_biospecimen", False)):
        reasons.append("biospecimen")

    case_count = parse_int(row.get("case_count", 0))
    if case_count >= 500:
        reasons.append(f"large cohort n={case_count}")

    open_file_count = parse_int(row.get("open_file_count", 0))
    if open_file_count >= 1000:
        reasons.append(f"many open files={open_file_count}")

    if not reasons:
        return "limited public modality coverage"

    return "; ".join(reasons)


def score_joined_projects(joined_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute priority scores for joined project metadata + modality matrix.
    """
    out = joined_df.copy()

    out["multiomics_modality_count"] = out.apply(compute_multiomics_modality_count, axis=1)
    out["multiomics_score"] = out.apply(compute_multiomics_score, axis=1)
    out["clinical_utility_score"] = out.apply(compute_clinical_utility_score, axis=1)
    out["open_data_score"] = out.apply(
        lambda row: compute_open_data_score(
            parse_int(row.get("open_file_count", 0)),
            parse_int(row.get("total_file_count", 0)),
        ),
        axis=1,
    )
    out["case_count_score"] = out["case_count"].apply(compute_case_count_score)
    out["proteogenomics_bonus"] = out.apply(compute_proteogenomics_bonus, axis=1)

    out["priority_score"] = (
        out["multiomics_score"]
        + out["clinical_utility_score"]
        + out["open_data_score"]
        + out["case_count_score"]
        + out["proteogenomics_bonus"]
    )

    out["priority_label"] = out["priority_score"].apply(assign_priority_label)
    out["priority_rationale"] = out.apply(build_priority_rationale, axis=1)

    out["source_database"] = "GDC"
    out["atlas_scope"] = "pan_cancer_public_reference"
    out["public_data_use"] = "project_priority_ranking"

    out = out.sort_values(
        by=[
            "priority_score",
            "multiomics_modality_count",
            "case_count",
            "open_file_count",
            "project_id",
        ],
        ascending=[False, False, False, False, True],
        kind="stable",
    ).reset_index(drop=True)

    out["rank"] = range(1, len(out) + 1)

    return out[OUTPUT_COLUMNS]


def join_project_and_modality_tables(
    project_df: pd.DataFrame,
    modality_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Join project inventory and modality matrix by project_id.
    """
    project_clean = clean_project_inventory(project_df)
    modality_clean = clean_modality_matrix(modality_df)

    joined = project_clean.merge(
        modality_clean,
        on="project_id",
        how="inner",
        validate="one_to_one",
    )

    return joined


def build_gdc_project_priority_ranking_from_dataframes(
    project_df: pd.DataFrame,
    modality_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build project priority ranking from in-memory DataFrames.
    """
    validate_columns(project_df, PROJECT_REQUIRED_COLUMNS, name="project inventory")
    validate_columns(modality_df, MODALITY_REQUIRED_COLUMNS, name="modality matrix")

    joined = join_project_and_modality_tables(project_df, modality_df)
    ranked = score_joined_projects(joined)

    return ranked


def build_gdc_project_priority_ranking(
    project_inventory_path: Path = DEFAULT_PROJECT_INVENTORY,
    modality_matrix_path: Path = DEFAULT_MODALITY_MATRIX,
    output_path: Path = DEFAULT_OUTPUT,
) -> pd.DataFrame:
    """
    Read input TSVs, build ranking, and write output.
    """
    project_df = read_tsv(
        project_inventory_path,
        required_columns=PROJECT_REQUIRED_COLUMNS,
        name="project inventory",
    )
    modality_df = read_tsv(
        modality_matrix_path,
        required_columns=MODALITY_REQUIRED_COLUMNS,
        name="modality matrix",
    )

    ranking_df = build_gdc_project_priority_ranking_from_dataframes(
        project_df=project_df,
        modality_df=modality_df,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ranking_df.to_csv(output_path, sep="\t", index=False)

    return ranking_df


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rank GDC projects by public multi-omics atlas priority."
    )

    parser.add_argument(
        "--project-inventory",
        type=Path,
        default=DEFAULT_PROJECT_INVENTORY,
        help=f"Input GDC project inventory TSV. Default: {DEFAULT_PROJECT_INVENTORY}",
    )

    parser.add_argument(
        "--modality-matrix",
        type=Path,
        default=DEFAULT_MODALITY_MATRIX,
        help=f"Input GDC project modality matrix TSV. Default: {DEFAULT_MODALITY_MATRIX}",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output ranking TSV. Default: {DEFAULT_OUTPUT}",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        ranking_df = build_gdc_project_priority_ranking(
            project_inventory_path=args.project_inventory,
            modality_matrix_path=args.modality_matrix,
            output_path=args.output,
        )
    except Exception as exc:
        print(f"ERROR: Failed to build GDC project priority ranking: {exc}", file=sys.stderr)
        return 1

    print("GDC project priority ranking complete.")
    print(f"Rows: {len(ranking_df)}")
    print(f"Output: {args.output}")

    if not ranking_df.empty:
        label_counts = ranking_df["priority_label"].value_counts().to_dict()
        print("Priority labels:")
        for label, count in label_counts.items():
            print(f"  {label}: {count}")

        print("Top 10 projects:")
        top = ranking_df.head(10)
        for _, row in top.iterrows():
            print(
                f"  #{row['rank']} {row['project_id']} "
                f"score={row['priority_score']} label={row['priority_label']}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
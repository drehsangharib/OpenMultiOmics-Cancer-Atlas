#!/usr/bin/env python3

"""
GDC Project Subset Builder

Project:
    OpenMultiOmics-Cancer-Atlas

Purpose:
    Build cancer-specific or query-specific GDC project subsets from locally
    generated public GDC metadata outputs.

Inputs:
    outputs/dataset_inventory/gdc_project_inventory.tsv
    outputs/dataset_inventory/gdc_project_modality_matrix.tsv
    outputs/ranked_datasets/gdc_project_priority_ranking.tsv

Output:
    outputs/dataset_inventory/gdc_project_subset.tsv

Examples:
    python -m core.search.gdc_project_subset --primary-site Brain

    python -m core.search.gdc_project_subset --program TCGA

    python -m core.search.gdc_project_subset --program TCGA --priority-label excellent

    python -m core.search.gdc_project_subset --has-modality transcriptomics --has-modality proteomics

    python -m core.search.gdc_project_subset --primary-site Brain --has-modality transcriptomics --min-case-count 100
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd


DEFAULT_PROJECT_INVENTORY = Path("outputs/dataset_inventory/gdc_project_inventory.tsv")
DEFAULT_MODALITY_MATRIX = Path("outputs/dataset_inventory/gdc_project_modality_matrix.tsv")
DEFAULT_PRIORITY_RANKING = Path("outputs/ranked_datasets/gdc_project_priority_ranking.tsv")
DEFAULT_OUTPUT = Path("outputs/dataset_inventory/gdc_project_subset.tsv")


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
    "total_file_count",
    "open_file_count",
    "controlled_file_count",
]


RANKING_REQUIRED_COLUMNS = [
    "rank",
    "project_id",
    "priority_score",
    "priority_label",
    "multiomics_modality_count",
    "priority_rationale",
]


BOOLEAN_MODALITY_COLUMNS = [
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


MODALITY_NAME_TO_COLUMN = {
    "transcriptomics": "has_transcriptomics",
    "rna": "has_transcriptomics",
    "rna_seq": "has_transcriptomics",
    "rnaseq": "has_transcriptomics",
    "methylation": "has_methylation",
    "dna_methylation": "has_methylation",
    "snv": "has_snv",
    "mutation": "has_snv",
    "mutations": "has_snv",
    "cnv": "has_cnv",
    "copy_number": "has_cnv",
    "copy_number_variation": "has_cnv",
    "structural_variation": "has_structural_variation",
    "sv": "has_structural_variation",
    "clinical": "has_clinical",
    "biospecimen": "has_biospecimen",
    "proteomics": "has_proteomics",
    "protein": "has_proteomics",
    "slide_images": "has_slide_images",
    "slides": "has_slide_images",
    "images": "has_slide_images",
    "sequencing_reads": "has_sequencing_reads",
    "reads": "has_sequencing_reads",
}


OUTPUT_COLUMNS = [
    "rank",
    "project_id",
    "project_name",
    "program_name",
    "primary_site",
    "disease_type",
    "case_count",
    "file_count",
    "priority_score",
    "priority_label",
    "multiomics_modality_count",
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
    "total_file_count",
    "open_file_count",
    "controlled_file_count",
    "priority_rationale",
    "subset_query",
    "source_database",
    "atlas_scope",
    "public_data_use",
]


def parse_int(value: object) -> int:
    """
    Convert values to integer. Invalid or missing values become zero.
    """
    try:
        if pd.isna(value):
            return 0
        return int(float(value))
    except Exception:
        return 0


def parse_bool(value: object) -> bool:
    """
    Convert common bool-like values to Python booleans.
    """
    if isinstance(value, bool):
        return value

    if pd.isna(value):
        return False

    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y"}


def normalize_text(value: object) -> str:
    """
    Normalize values to stripped strings.
    """
    if pd.isna(value):
        return ""
    return str(value).strip()


def normalize_lower(value: object) -> str:
    """
    Normalize values to lowercase strings.
    """
    return normalize_text(value).lower()


def validate_columns(df: pd.DataFrame, required_columns: List[str], name: str) -> None:
    """
    Validate required columns in a DataFrame.
    """
    missing = [column for column in required_columns if column not in df.columns]

    if missing:
        raise ValueError(f"Missing required columns in {name}: " + ", ".join(missing))


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
    Clean project inventory fields.
    """
    out = project_df.copy()

    for column in [
        "project_id",
        "project_name",
        "program_name",
        "primary_site",
        "disease_type",
    ]:
        out[column] = out[column].fillna("").astype(str)

    out["case_count"] = out["case_count"].apply(parse_int)
    out["file_count"] = out["file_count"].apply(parse_int)

    return out


def clean_modality_matrix(modality_df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean modality matrix fields.
    """
    out = modality_df.copy()
    out["project_id"] = out["project_id"].fillna("").astype(str)

    for column in BOOLEAN_MODALITY_COLUMNS:
        out[column] = out[column].apply(parse_bool)

    for column in ["total_file_count", "open_file_count", "controlled_file_count"]:
        out[column] = out[column].apply(parse_int)

    return out


def clean_priority_ranking(ranking_df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean priority ranking fields.
    """
    out = ranking_df.copy()

    out["project_id"] = out["project_id"].fillna("").astype(str)
    out["rank"] = out["rank"].apply(parse_int)
    out["priority_score"] = out["priority_score"].apply(parse_int)
    out["priority_label"] = out["priority_label"].fillna("").astype(str)
    out["multiomics_modality_count"] = out["multiomics_modality_count"].apply(parse_int)
    out["priority_rationale"] = out["priority_rationale"].fillna("").astype(str)

    return out


def join_gdc_project_tables(
    project_df: pd.DataFrame,
    modality_df: pd.DataFrame,
    ranking_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Join project inventory, modality matrix, and priority ranking.
    """
    project_clean = clean_project_inventory(project_df)
    modality_clean = clean_modality_matrix(modality_df)
    ranking_clean = clean_priority_ranking(ranking_df)

    joined = project_clean.merge(
        modality_clean,
        on="project_id",
        how="inner",
        validate="one_to_one",
    )

    joined = joined.merge(
        ranking_clean[
            [
                "project_id",
                "rank",
                "priority_score",
                "priority_label",
                "multiomics_modality_count",
                "priority_rationale",
            ]
        ],
        on="project_id",
        how="inner",
        validate="one_to_one",
    )

    joined["source_database"] = "GDC"
    joined["atlas_scope"] = "pan_cancer_public_reference"
    joined["public_data_use"] = "project_subset"

    return joined


def contains_any(value: object, query_terms: Optional[Iterable[str]]) -> bool:
    """
    Return True if value contains any query term, case-insensitively.

    If query_terms is None or empty, return True.
    """
    if not query_terms:
        return True

    text = normalize_lower(value)

    for term in query_terms:
        if normalize_lower(term) in text:
            return True

    return False


def equals_any(value: object, query_terms: Optional[Iterable[str]]) -> bool:
    """
    Return True if value exactly equals any query term, case-insensitively.

    This is stricter than contains_any and is useful for exact primary-site or
    disease-type filters.
    """
    if not query_terms:
        return True

    text = normalize_lower(value)

    for term in query_terms:
        if text == normalize_lower(term):
            return True

    return False


def normalize_modality_name(modality: str) -> str:
    """
    Normalize user-provided modality names.
    """
    return normalize_lower(modality).replace("-", "_").replace(" ", "_")


def modality_to_column(modality: str) -> str:
    """
    Convert a user-provided modality name to a modality matrix column.
    """
    normalized = normalize_modality_name(modality)

    if normalized not in MODALITY_NAME_TO_COLUMN:
        valid = ", ".join(sorted(MODALITY_NAME_TO_COLUMN.keys()))
        raise ValueError(f"Unknown modality '{modality}'. Valid options: {valid}")

    return MODALITY_NAME_TO_COLUMN[normalized]


def build_subset_query_description(
    project_ids: Optional[List[str]] = None,
    programs: Optional[List[str]] = None,
    primary_sites: Optional[List[str]] = None,
    primary_sites_exact: Optional[List[str]] = None,
    disease_types: Optional[List[str]] = None,
    disease_types_exact: Optional[List[str]] = None,
    priority_labels: Optional[List[str]] = None,
    required_modalities: Optional[List[str]] = None,
    min_case_count: Optional[int] = None,
    min_priority_score: Optional[int] = None,
    min_modality_count: Optional[int] = None,
    top_n: Optional[int] = None,
) -> str:
    """
    Build a compact query description for provenance.
    """
    parts: List[str] = []

    if project_ids:
        parts.append("project_id=" + ",".join(project_ids))

    if programs:
        parts.append("program=" + ",".join(programs))

    if primary_sites:
        parts.append("primary_site=" + ",".join(primary_sites))

    if primary_sites_exact:
        parts.append("primary_site_exact=" + ",".join(primary_sites_exact))

    if disease_types:
        parts.append("disease_type=" + ",".join(disease_types))

    if disease_types_exact:
        parts.append("disease_type_exact=" + ",".join(disease_types_exact))

    if priority_labels:
        parts.append("priority_label=" + ",".join(priority_labels))

    if required_modalities:
        parts.append("has_modality=" + ",".join(required_modalities))

    if min_case_count is not None:
        parts.append(f"min_case_count={min_case_count}")

    if min_priority_score is not None:
        parts.append(f"min_priority_score={min_priority_score}")

    if min_modality_count is not None:
        parts.append(f"min_modality_count={min_modality_count}")

    if top_n is not None:
        parts.append(f"top_n={top_n}")

    if not parts:
        return "all_projects"

    return "; ".join(parts)


def filter_project_subset(
    joined_df: pd.DataFrame,
    project_ids: Optional[List[str]] = None,
    programs: Optional[List[str]] = None,
    primary_sites: Optional[List[str]] = None,
    primary_sites_exact: Optional[List[str]] = None,
    disease_types: Optional[List[str]] = None,
    disease_types_exact: Optional[List[str]] = None,
    priority_labels: Optional[List[str]] = None,
    required_modalities: Optional[List[str]] = None,
    min_case_count: Optional[int] = None,
    min_priority_score: Optional[int] = None,
    min_modality_count: Optional[int] = None,
    top_n: Optional[int] = None,
) -> pd.DataFrame:
    """
    Apply project subset filters.
    """
    out = joined_df.copy()

    if project_ids:
        wanted = {normalize_lower(project_id) for project_id in project_ids}
        out = out[out["project_id"].apply(normalize_lower).isin(wanted)]

    if programs:
        out = out[out["program_name"].apply(lambda value: contains_any(value, programs))]

    if primary_sites:
        out = out[out["primary_site"].apply(lambda value: contains_any(value, primary_sites))]

    if primary_sites_exact:
        out = out[out["primary_site"].apply(lambda value: equals_any(value, primary_sites_exact))]

    if disease_types:
        out = out[out["disease_type"].apply(lambda value: contains_any(value, disease_types))]

    if disease_types_exact:
        out = out[out["disease_type"].apply(lambda value: equals_any(value, disease_types_exact))]

    if priority_labels:
        wanted_labels = {normalize_lower(label) for label in priority_labels}
        out = out[out["priority_label"].apply(normalize_lower).isin(wanted_labels)]

    if required_modalities:
        for modality in required_modalities:
            column = modality_to_column(modality)
            out = out[out[column].apply(parse_bool)]

    if min_case_count is not None:
        out = out[out["case_count"] >= min_case_count]

    if min_priority_score is not None:
        out = out[out["priority_score"] >= min_priority_score]

    if min_modality_count is not None:
        out = out[out["multiomics_modality_count"] >= min_modality_count]

    out = out.sort_values(
        by=["priority_score", "multiomics_modality_count", "case_count", "rank"],
        ascending=[False, False, False, True],
        kind="stable",
    ).reset_index(drop=True)

    if top_n is not None:
        out = out.head(top_n).reset_index(drop=True)

    query_description = build_subset_query_description(
        project_ids=project_ids,
        programs=programs,
        primary_sites=primary_sites,
        primary_sites_exact=primary_sites_exact,
        disease_types=disease_types,
        disease_types_exact=disease_types_exact,
        priority_labels=priority_labels,
        required_modalities=required_modalities,
        min_case_count=min_case_count,
        min_priority_score=min_priority_score,
        min_modality_count=min_modality_count,
        top_n=top_n,
    )

    out["subset_query"] = query_description

    return out


def build_gdc_project_subset_from_dataframes(
    project_df: pd.DataFrame,
    modality_df: pd.DataFrame,
    ranking_df: pd.DataFrame,
    project_ids: Optional[List[str]] = None,
    programs: Optional[List[str]] = None,
    primary_sites: Optional[List[str]] = None,
    primary_sites_exact: Optional[List[str]] = None,
    disease_types: Optional[List[str]] = None,
    disease_types_exact: Optional[List[str]] = None,
    priority_labels: Optional[List[str]] = None,
    required_modalities: Optional[List[str]] = None,
    min_case_count: Optional[int] = None,
    min_priority_score: Optional[int] = None,
    min_modality_count: Optional[int] = None,
    top_n: Optional[int] = None,
) -> pd.DataFrame:
    """
    Build subset from in-memory DataFrames.
    """
    validate_columns(project_df, PROJECT_REQUIRED_COLUMNS, "project inventory")
    validate_columns(modality_df, MODALITY_REQUIRED_COLUMNS, "modality matrix")
    validate_columns(ranking_df, RANKING_REQUIRED_COLUMNS, "priority ranking")

    joined = join_gdc_project_tables(
        project_df=project_df,
        modality_df=modality_df,
        ranking_df=ranking_df,
    )

    subset = filter_project_subset(
        joined_df=joined,
        project_ids=project_ids,
        programs=programs,
        primary_sites=primary_sites,
        primary_sites_exact=primary_sites_exact,
        disease_types=disease_types,
        disease_types_exact=disease_types_exact,
        priority_labels=priority_labels,
        required_modalities=required_modalities,
        min_case_count=min_case_count,
        min_priority_score=min_priority_score,
        min_modality_count=min_modality_count,
        top_n=top_n,
    )

    available_columns = [column for column in OUTPUT_COLUMNS if column in subset.columns]
    return subset.loc[:, available_columns]


def build_gdc_project_subset(
    project_inventory_path: Path = DEFAULT_PROJECT_INVENTORY,
    modality_matrix_path: Path = DEFAULT_MODALITY_MATRIX,
    priority_ranking_path: Path = DEFAULT_PRIORITY_RANKING,
    output_path: Path = DEFAULT_OUTPUT,
    project_ids: Optional[List[str]] = None,
    programs: Optional[List[str]] = None,
    primary_sites: Optional[List[str]] = None,
    primary_sites_exact: Optional[List[str]] = None,
    disease_types: Optional[List[str]] = None,
    disease_types_exact: Optional[List[str]] = None,
    priority_labels: Optional[List[str]] = None,
    required_modalities: Optional[List[str]] = None,
    min_case_count: Optional[int] = None,
    min_priority_score: Optional[int] = None,
    min_modality_count: Optional[int] = None,
    top_n: Optional[int] = None,
) -> pd.DataFrame:
    """
    Read local GDC outputs, build subset, and write output.
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
    ranking_df = read_tsv(
        priority_ranking_path,
        required_columns=RANKING_REQUIRED_COLUMNS,
        name="priority ranking",
    )

    subset = build_gdc_project_subset_from_dataframes(
        project_df=project_df,
        modality_df=modality_df,
        ranking_df=ranking_df,
        project_ids=project_ids,
        programs=programs,
        primary_sites=primary_sites,
        primary_sites_exact=primary_sites_exact,
        disease_types=disease_types,
        disease_types_exact=disease_types_exact,
        priority_labels=priority_labels,
        required_modalities=required_modalities,
        min_case_count=min_case_count,
        min_priority_score=min_priority_score,
        min_modality_count=min_modality_count,
        top_n=top_n,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    subset.to_csv(output_path, sep="\t", index=False)

    return subset


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build filtered GDC project subsets for cancer atlas modules."
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
        "--priority-ranking",
        type=Path,
        default=DEFAULT_PRIORITY_RANKING,
        help=f"Input GDC priority ranking TSV. Default: {DEFAULT_PRIORITY_RANKING}",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output subset TSV. Default: {DEFAULT_OUTPUT}",
    )

    parser.add_argument(
        "--project-id",
        action="append",
        default=None,
        help="Exact GDC project ID to include. Can be repeated.",
    )

    parser.add_argument(
        "--program",
        action="append",
        default=None,
        help="Program name query, e.g. TCGA, TARGET, CPTAC. Can be repeated.",
    )

    parser.add_argument(
        "--primary-site",
        action="append",
        default=None,
        help="Primary site text query, e.g. Brain, Breast, Lung. Can be repeated.",
    )

    parser.add_argument(
        "--primary-site-exact",
        action="append",
        default=None,
        help="Exact primary site match, e.g. Brain. Can be repeated.",
    )

    parser.add_argument(
        "--disease-type",
        action="append",
        default=None,
        help="Disease type text query, e.g. Gliomas, Adenocarcinomas. Can be repeated.",
    )

    parser.add_argument(
        "--disease-type-exact",
        action="append",
        default=None,
        help="Exact disease type match, e.g. Gliomas. Can be repeated.",
    )

    parser.add_argument(
        "--priority-label",
        action="append",
        default=None,
        help="Priority label filter, e.g. excellent, high, medium. Can be repeated.",
    )

    parser.add_argument(
        "--has-modality",
        action="append",
        default=None,
        help=(
            "Require modality availability. Can be repeated. Examples: "
            "transcriptomics, methylation, snv, cnv, clinical, proteomics."
        ),
    )

    parser.add_argument(
        "--min-case-count",
        type=int,
        default=None,
        help="Minimum case count.",
    )

    parser.add_argument(
        "--min-priority-score",
        type=int,
        default=None,
        help="Minimum priority score.",
    )

    parser.add_argument(
        "--min-modality-count",
        type=int,
        default=None,
        help="Minimum number of available broad modalities.",
    )

    parser.add_argument(
        "--top-n",
        type=int,
        default=None,
        help="Return only the top N projects after filtering.",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        subset = build_gdc_project_subset(
            project_inventory_path=args.project_inventory,
            modality_matrix_path=args.modality_matrix,
            priority_ranking_path=args.priority_ranking,
            output_path=args.output,
            project_ids=args.project_id,
            programs=args.program,
            primary_sites=args.primary_site,
            primary_sites_exact=args.primary_site_exact,
            disease_types=args.disease_type,
            disease_types_exact=args.disease_type_exact,
            priority_labels=args.priority_label,
            required_modalities=args.has_modality,
            min_case_count=args.min_case_count,
            min_priority_score=args.min_priority_score,
            min_modality_count=args.min_modality_count,
            top_n=args.top_n,
        )
    except Exception as exc:
        print(f"ERROR: Failed to build GDC project subset: {exc}", file=sys.stderr)
        return 1

    print("GDC project subset complete.")
    print(f"Rows: {len(subset)}")
    print(f"Output: {args.output}")

    if not subset.empty:
        print("Top subset projects:")
        preview_cols = [
            "project_id",
            "program_name",
            "primary_site",
            "case_count",
            "priority_score",
            "priority_label",
        ]

        for _, row in subset.head(10).iterrows():
            preview = " | ".join(
                f"{column}={row[column]}" for column in preview_cols if column in row
            )
            print(f"  {preview}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

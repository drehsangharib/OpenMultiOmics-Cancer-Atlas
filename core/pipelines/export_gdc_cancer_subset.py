#!/usr/bin/env python3

"""
Export GDC Cancer Project Subset

Project:
    OpenMultiOmics-Cancer-Atlas

Purpose:
    Export cancer-specific or query-specific GDC project subsets into organized
    output folders for downstream atlas modules.

Inputs:
    outputs/dataset_inventory/gdc_project_inventory.tsv
    outputs/dataset_inventory/gdc_project_modality_matrix.tsv
    outputs/ranked_datasets/gdc_project_priority_ranking.tsv

Outputs:
    outputs/subsets/<subset_name>/gdc_project_subset.tsv
    outputs/subsets/<subset_name>/gdc_project_subset_summary.md

Examples:
    python -m core.pipelines.export_gdc_cancer_subset --subset-name brain_exact --primary-site-exact Brain

    python -m core.pipelines.export_gdc_cancer_subset --subset-name tcga_excellent --program TCGA --priority-label excellent

    python -m core.pipelines.export_gdc_cancer_subset --subset-name proteogenomics_top10 --has-modality transcriptomics --has-modality proteomics --priority-label excellent --top-n 10
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from core.search.gdc_project_subset import (
    DEFAULT_MODALITY_MATRIX,
    DEFAULT_PRIORITY_RANKING,
    DEFAULT_PROJECT_INVENTORY,
    build_gdc_project_subset,
)


DEFAULT_SUBSETS_DIR = Path("outputs/subsets")
DEFAULT_SUBSET_FILENAME = "gdc_project_subset.tsv"
DEFAULT_SUMMARY_FILENAME = "gdc_project_subset_summary.md"


MODALITY_COLUMNS = [
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


MODALITY_DISPLAY_NAMES = {
    "has_transcriptomics": "Transcriptomics",
    "has_methylation": "DNA methylation",
    "has_snv": "SNV",
    "has_cnv": "CNV",
    "has_structural_variation": "Structural variation",
    "has_clinical": "Clinical",
    "has_biospecimen": "Biospecimen",
    "has_proteomics": "Proteomics",
    "has_slide_images": "Slide images",
    "has_sequencing_reads": "Sequencing reads",
}


def sanitize_subset_name(name: str) -> str:
    """
    Convert a user-provided subset name into a safe folder name.
    """
    if name is None:
        return "gdc_subset"

    text = str(name).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text)
    text = text.strip("_")

    if not text:
        return "gdc_subset"

    return text


def build_subset_output_paths(
    subset_name: str,
    subsets_dir: Path = DEFAULT_SUBSETS_DIR,
) -> Dict[str, Path]:
    """
    Build output folder and file paths for one subset export.
    """
    safe_name = sanitize_subset_name(subset_name)
    subset_dir = subsets_dir / safe_name

    return {
        "subset_dir": subset_dir,
        "subset_tsv": subset_dir / DEFAULT_SUBSET_FILENAME,
        "summary_md": subset_dir / DEFAULT_SUMMARY_FILENAME,
    }


def value_counts_dict(df: pd.DataFrame, column: str) -> Dict[str, int]:
    """
    Return sorted value-count dictionary for a column.
    """
    if df.empty or column not in df.columns:
        return {}

    counts = df[column].fillna("").astype(str).value_counts().to_dict()
    return {str(key): int(value) for key, value in counts.items()}


def modality_counts(df: pd.DataFrame) -> Dict[str, int]:
    """
    Count available modalities in a subset.
    """
    counts: Dict[str, int] = {}

    for column in MODALITY_COLUMNS:
        if column in df.columns:
            label = MODALITY_DISPLAY_NAMES.get(column, column)
            counts[label] = int(df[column].astype(bool).sum())

    return counts


def format_count_section(title: str, counts: Dict[str, int]) -> str:
    """
    Format a markdown bullet list from a count dictionary.
    """
    lines = [f"## {title}", ""]

    if not counts:
        lines.append("_No records available._")
        lines.append("")
        return "\n".join(lines)

    for key, value in counts.items():
        lines.append(f"- {key}: {value}")

    lines.append("")
    return "\n".join(lines)


def format_top_projects_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    """
    Format top subset projects as a markdown table.
    """
    if df.empty:
        return "## Top projects\n\n_No projects available._\n"

    columns = [
        "rank",
        "project_id",
        "program_name",
        "primary_site",
        "case_count",
        "priority_score",
        "priority_label",
        "multiomics_modality_count",
    ]

    display_columns = [column for column in columns if column in df.columns]
    display_df = df.loc[:, display_columns].head(max_rows).copy()

    lines = ["## Top projects", ""]
    lines.append("| " + " | ".join(display_columns) + " |")
    lines.append("| " + " | ".join(["---"] * len(display_columns)) + " |")

    for _, row in display_df.iterrows():
        values = [str(row[column]).replace("\n", " ") for column in display_columns]
        lines.append("| " + " | ".join(values) + " |")

    lines.append("")
    return "\n".join(lines)


def build_subset_summary_markdown(
    subset_df: pd.DataFrame,
    subset_name: str,
    subset_query: str,
) -> str:
    """
    Build markdown summary for a GDC project subset.
    """
    safe_name = sanitize_subset_name(subset_name)
    project_count = int(len(subset_df))

    total_cases = int(subset_df["case_count"].sum()) if "case_count" in subset_df.columns else 0
    total_files = int(subset_df["file_count"].sum()) if "file_count" in subset_df.columns else 0

    priority_counts = value_counts_dict(subset_df, "priority_label")
    program_counts = value_counts_dict(subset_df, "program_name")
    modality_count_values = modality_counts(subset_df)

    lines = [
        f"# GDC Project Subset Summary: {safe_name}",
        "",
        "## Overview",
        "",
        f"- Subset name: `{safe_name}`",
        f"- Project count: {project_count}",
        f"- Total cases: {total_cases}",
        f"- Total files: {total_files}",
        f"- Subset query: `{subset_query}`",
        "",
        format_count_section("Priority labels", priority_counts),
        format_count_section("Programs", program_counts),
        format_count_section("Modality availability", modality_count_values),
        format_top_projects_table(subset_df),
        "## Notes",
        "",
        "- This subset is generated from local public GDC metadata summary tables.",
        "- Controlled-access file availability may be counted in metadata, but controlled-access files are not downloaded.",
        "- Generated subset outputs should remain local unless intentionally curated.",
        "",
    ]

    return "\n".join(lines)


def write_subset_summary(
    subset_df: pd.DataFrame,
    subset_name: str,
    summary_path: Path,
) -> str:
    """
    Write markdown summary for a subset and return the markdown string.
    """
    if subset_df.empty:
        subset_query = "empty_subset"
    elif "subset_query" in subset_df.columns:
        subset_query = str(subset_df["subset_query"].iloc[0])
    else:
        subset_query = "unknown_query"

    markdown = build_subset_summary_markdown(
        subset_df=subset_df,
        subset_name=subset_name,
        subset_query=subset_query,
    )

    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(markdown, encoding="utf-8")

    return markdown


def export_gdc_cancer_subset(
    subset_name: str,
    project_inventory_path: Path = DEFAULT_PROJECT_INVENTORY,
    modality_matrix_path: Path = DEFAULT_MODALITY_MATRIX,
    priority_ranking_path: Path = DEFAULT_PRIORITY_RANKING,
    subsets_dir: Path = DEFAULT_SUBSETS_DIR,
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
) -> Dict[str, Path]:
    """
    Export a GDC project subset to an organized folder.
    """
    paths = build_subset_output_paths(
        subset_name=subset_name,
        subsets_dir=subsets_dir,
    )

    paths["subset_dir"].mkdir(parents=True, exist_ok=True)

    subset_df = build_gdc_project_subset(
        project_inventory_path=project_inventory_path,
        modality_matrix_path=modality_matrix_path,
        priority_ranking_path=priority_ranking_path,
        output_path=paths["subset_tsv"],
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

    write_subset_summary(
        subset_df=subset_df,
        subset_name=subset_name,
        summary_path=paths["summary_md"],
    )

    return paths


def build_arg_parser() -> argparse.ArgumentParser:
    """
    Build CLI parser.
    """
    parser = argparse.ArgumentParser(
        description="Export a cancer-specific or query-specific GDC project subset."
    )

    parser.add_argument(
        "--subset-name",
        required=True,
        help="Name for the subset output folder, e.g. brain_exact or tcga_excellent.",
    )

    parser.add_argument(
        "--subsets-dir",
        type=Path,
        default=DEFAULT_SUBSETS_DIR,
        help=f"Base output directory for subsets. Default: {DEFAULT_SUBSETS_DIR}",
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
        help="Disease type text query, e.g. Gliomas. Can be repeated.",
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
    """
    CLI entrypoint.
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        paths = export_gdc_cancer_subset(
            subset_name=args.subset_name,
            project_inventory_path=args.project_inventory,
            modality_matrix_path=args.modality_matrix,
            priority_ranking_path=args.priority_ranking,
            subsets_dir=args.subsets_dir,
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
        print(f"ERROR: Failed to export GDC cancer subset: {exc}", file=sys.stderr)
        return 1

    print("GDC cancer subset export complete.")
    print(f"Subset directory: {paths['subset_dir']}")
    print(f"Subset TSV: {paths['subset_tsv']}")
    print(f"Summary markdown: {paths['summary_md']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
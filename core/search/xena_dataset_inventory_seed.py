#!/usr/bin/env python3

"""
UCSC Xena Dataset Inventory Seed

Project:
    OpenMultiOmics-Cancer-Atlas

Purpose:
    Create a curated seed inventory of high-value UCSC Xena dataset categories
    relevant to cancer multi-omics atlas construction.

This is not a live Xena crawler. It is a stable seed registry that identifies
the first dataset categories and matrix families that should be targeted by
future Xena dataset crawling and integration modules.

Output:
    outputs/dataset_inventory/xena_dataset_inventory_seed.tsv

Example:
    python -m core.search.xena_dataset_inventory_seed
"""

import argparse
import sys
from pathlib import Path

import pandas as pd


DEFAULT_OUTPUT = Path("outputs/dataset_inventory/xena_dataset_inventory_seed.tsv")


XENA_DATASET_SEED_COLUMNS = [
    "dataset_seed_id",
    "dataset_seed_name",
    "hub_id",
    "hub_url",
    "resource_family",
    "cancer_scope",
    "data_category",
    "omics_modality",
    "matrix_type",
    "sample_scope",
    "use_case",
    "recommended_for_first_integration",
    "priority_for_atlas",
    "integration_stage",
    "notes",
]


def get_xena_dataset_seed_records():
    """
    Return curated UCSC Xena dataset seed records.
    """
    return [
        {
            "dataset_seed_id": "gdc_xena_tcga_expression",
            "dataset_seed_name": "GDC Xena TCGA harmonized gene expression matrices",
            "hub_id": "gdc_xena",
            "hub_url": "https://gdc.xenahubs.net",
            "resource_family": "GDC; TCGA",
            "cancer_scope": "TCGA cancer cohorts",
            "data_category": "gene expression",
            "omics_modality": "transcriptomics",
            "matrix_type": "sample-by-gene expression matrix",
            "sample_scope": "tumor samples; cohort-level matrices",
            "use_case": "cross-check GDC-ranked projects and enable expression-first atlas modules",
            "recommended_for_first_integration": True,
            "priority_for_atlas": 5,
            "integration_stage": "planned_next",
            "notes": "High-value first target because the project already has GDC project metadata and rankings.",
        },
        {
            "dataset_seed_id": "gdc_xena_tcga_clinical",
            "dataset_seed_name": "GDC Xena TCGA clinical and phenotype matrices",
            "hub_id": "gdc_xena",
            "hub_url": "https://gdc.xenahubs.net",
            "resource_family": "GDC; TCGA",
            "cancer_scope": "TCGA cancer cohorts",
            "data_category": "clinical phenotype",
            "omics_modality": "clinical",
            "matrix_type": "sample-by-feature phenotype table",
            "sample_scope": "patients and samples",
            "use_case": "link molecular matrices to clinical and phenotype variables",
            "recommended_for_first_integration": True,
            "priority_for_atlas": 5,
            "integration_stage": "planned_next",
            "notes": "Essential companion layer for every molecular atlas module.",
        },
        {
            "dataset_seed_id": "tcga_xena_expression",
            "dataset_seed_name": "TCGA Xena legacy gene expression matrices",
            "hub_id": "tcga_xena",
            "hub_url": "https://tcga.xenahubs.net",
            "resource_family": "TCGA",
            "cancer_scope": "TCGA cancer cohorts",
            "data_category": "gene expression",
            "omics_modality": "transcriptomics",
            "matrix_type": "sample-by-gene expression matrix",
            "sample_scope": "tumor samples",
            "use_case": "TCGA-focused expression atlas and comparison against GDC harmonized data",
            "recommended_for_first_integration": True,
            "priority_for_atlas": 5,
            "integration_stage": "planned_next",
            "notes": "Useful for TCGA cohort-level expression modules.",
        },
        {
            "dataset_seed_id": "tcga_xena_copy_number",
            "dataset_seed_name": "TCGA Xena copy-number matrices",
            "hub_id": "tcga_xena",
            "hub_url": "https://tcga.xenahubs.net",
            "resource_family": "TCGA",
            "cancer_scope": "TCGA cancer cohorts",
            "data_category": "copy number",
            "omics_modality": "cnv",
            "matrix_type": "sample-by-gene or sample-by-segment copy-number matrix",
            "sample_scope": "tumor samples",
            "use_case": "copy-number alteration modules and multi-omics integration",
            "recommended_for_first_integration": True,
            "priority_for_atlas": 5,
            "integration_stage": "planned_next",
            "notes": "Important for CNV-aware cancer atlas modules.",
        },
        {
            "dataset_seed_id": "tcga_xena_methylation",
            "dataset_seed_name": "TCGA Xena DNA methylation matrices",
            "hub_id": "tcga_xena",
            "hub_url": "https://tcga.xenahubs.net",
            "resource_family": "TCGA",
            "cancer_scope": "TCGA cancer cohorts",
            "data_category": "DNA methylation",
            "omics_modality": "methylation",
            "matrix_type": "sample-by-probe methylation matrix",
            "sample_scope": "tumor samples",
            "use_case": "epigenomic atlas modules and expression-methylation integration",
            "recommended_for_first_integration": True,
            "priority_for_atlas": 5,
            "integration_stage": "planned_next",
            "notes": "High-value for epigenomics-aware atlas construction.",
        },
        {
            "dataset_seed_id": "tcga_xena_mutation",
            "dataset_seed_name": "TCGA Xena mutation feature matrices",
            "hub_id": "tcga_xena",
            "hub_url": "https://tcga.xenahubs.net",
            "resource_family": "TCGA",
            "cancer_scope": "TCGA cancer cohorts",
            "data_category": "somatic mutation",
            "omics_modality": "snv",
            "matrix_type": "sample-by-gene mutation or mutation feature matrix",
            "sample_scope": "tumor samples",
            "use_case": "mutation-stratified expression and clinical analyses",
            "recommended_for_first_integration": True,
            "priority_for_atlas": 5,
            "integration_stage": "planned_next",
            "notes": "Useful for genotype-expression and survival stratification modules.",
        },
        {
            "dataset_seed_id": "pancanatlas_subtypes",
            "dataset_seed_name": "Pan-Cancer Atlas subtype and annotation matrices",
            "hub_id": "pancanatlas",
            "hub_url": "https://pancanatlas.xenahubs.net",
            "resource_family": "TCGA Pan-Cancer Atlas",
            "cancer_scope": "pan-cancer",
            "data_category": "subtype annotation",
            "omics_modality": "clinical_annotation",
            "matrix_type": "sample-by-annotation table",
            "sample_scope": "pan-cancer TCGA samples",
            "use_case": "pan-cancer subtype-aware reports and cohort stratification",
            "recommended_for_first_integration": True,
            "priority_for_atlas": 5,
            "integration_stage": "planned_next",
            "notes": "Important for cross-cancer summary modules.",
        },
        {
            "dataset_seed_id": "pancanatlas_expression",
            "dataset_seed_name": "Pan-Cancer Atlas expression matrices",
            "hub_id": "pancanatlas",
            "hub_url": "https://pancanatlas.xenahubs.net",
            "resource_family": "TCGA Pan-Cancer Atlas",
            "cancer_scope": "pan-cancer",
            "data_category": "gene expression",
            "omics_modality": "transcriptomics",
            "matrix_type": "sample-by-gene expression matrix",
            "sample_scope": "pan-cancer TCGA samples",
            "use_case": "pan-cancer expression atlas and cross-cancer comparisons",
            "recommended_for_first_integration": True,
            "priority_for_atlas": 5,
            "integration_stage": "planned_next",
            "notes": "Useful for broad pan-cancer expression views.",
        },
        {
            "dataset_seed_id": "toil_tcga_gtex_expression",
            "dataset_seed_name": "Toil TCGA/GTEx uniformly recomputed RNA-seq matrices",
            "hub_id": "toil_xena",
            "hub_url": "https://toil.xenahubs.net",
            "resource_family": "TCGA; GTEx; TARGET",
            "cancer_scope": "tumor-normal comparison",
            "data_category": "gene expression",
            "omics_modality": "transcriptomics",
            "matrix_type": "sample-by-gene RNA-seq matrix",
            "sample_scope": "tumor and normal samples",
            "use_case": "tumor-versus-normal expression comparisons across tissue types",
            "recommended_for_first_integration": True,
            "priority_for_atlas": 5,
            "integration_stage": "planned_next",
            "notes": "High-value for tumor-normal expression analysis modules.",
        },
        {
            "dataset_seed_id": "ucsc_public_ccle_expression",
            "dataset_seed_name": "UCSC Public Hub CCLE expression matrices",
            "hub_id": "ucsc_public",
            "hub_url": "https://ucscpublic.xenahubs.net",
            "resource_family": "CCLE",
            "cancer_scope": "cancer cell lines",
            "data_category": "gene expression",
            "omics_modality": "transcriptomics",
            "matrix_type": "cell-line-by-gene expression matrix",
            "sample_scope": "cancer cell lines",
            "use_case": "link tumor atlas signals to model systems and cell-line resources",
            "recommended_for_first_integration": False,
            "priority_for_atlas": 4,
            "integration_stage": "planned",
            "notes": "Useful for later DepMap/CCLE integration.",
        },
        {
            "dataset_seed_id": "ucsc_public_phenotype",
            "dataset_seed_name": "UCSC Public Hub phenotype matrices",
            "hub_id": "ucsc_public",
            "hub_url": "https://ucscpublic.xenahubs.net",
            "resource_family": "mixed public resources",
            "cancer_scope": "broad public cancer and biomedical cohorts",
            "data_category": "phenotype",
            "omics_modality": "clinical",
            "matrix_type": "sample-by-feature phenotype table",
            "sample_scope": "mixed samples",
            "use_case": "phenotype harmonization across public matrix resources",
            "recommended_for_first_integration": False,
            "priority_for_atlas": 4,
            "integration_stage": "planned",
            "notes": "Useful after the core GDC/TCGA/Toil/PanCancer targets are stable.",
        },
        {
            "dataset_seed_id": "icgc_xena_expression",
            "dataset_seed_name": "ICGC Xena expression matrices",
            "hub_id": "icgc_xena",
            "hub_url": "https://icgc.xenahubs.net",
            "resource_family": "ICGC",
            "cancer_scope": "international cancer cohorts",
            "data_category": "gene expression",
            "omics_modality": "transcriptomics",
            "matrix_type": "sample-by-gene expression matrix",
            "sample_scope": "cancer samples",
            "use_case": "international cancer cohort expression expansion",
            "recommended_for_first_integration": False,
            "priority_for_atlas": 4,
            "integration_stage": "planned",
            "notes": "Useful after initial Xena/GDC/TCGA integration.",
        },
        {
            "dataset_seed_id": "pcawg_xena_wgs_features",
            "dataset_seed_name": "PCAWG Xena whole-genome feature matrices",
            "hub_id": "pcawg_xena",
            "hub_url": "https://pcawg.xenahubs.net",
            "resource_family": "PCAWG",
            "cancer_scope": "whole-genome pan-cancer",
            "data_category": "whole-genome feature",
            "omics_modality": "genomics",
            "matrix_type": "sample-by-feature WGS-derived matrix",
            "sample_scope": "pan-cancer WGS samples",
            "use_case": "whole-genome pan-cancer atlas expansion",
            "recommended_for_first_integration": False,
            "priority_for_atlas": 4,
            "integration_stage": "planned",
            "notes": "Useful later for WGS-focused pan-cancer modules.",
        },
        {
            "dataset_seed_id": "atacseq_xena_accessibility",
            "dataset_seed_name": "ATAC-seq Xena chromatin accessibility matrices",
            "hub_id": "atacseq_xena",
            "hub_url": "https://atacseq.xenahubs.net",
            "resource_family": "public ATAC-seq resources",
            "cancer_scope": "regulatory genomics",
            "data_category": "chromatin accessibility",
            "omics_modality": "chromatin_accessibility",
            "matrix_type": "sample-by-peak accessibility matrix",
            "sample_scope": "public ATAC-seq samples",
            "use_case": "regulatory atlas expansion",
            "recommended_for_first_integration": False,
            "priority_for_atlas": 3,
            "integration_stage": "planned_later",
            "notes": "Useful after transcriptomic/genomic core integration.",
        },
        {
            "dataset_seed_id": "treehouse_xena_expression",
            "dataset_seed_name": "Treehouse Xena pediatric and rare cancer expression matrices",
            "hub_id": "treehouse_xena",
            "hub_url": "https://xena.treehouse.gi.ucsc.edu:443",
            "resource_family": "Treehouse",
            "cancer_scope": "pediatric and rare cancer",
            "data_category": "gene expression",
            "omics_modality": "transcriptomics",
            "matrix_type": "sample-by-gene expression matrix",
            "sample_scope": "pediatric and rare cancer samples",
            "use_case": "pediatric and rare cancer atlas expansion",
            "recommended_for_first_integration": False,
            "priority_for_atlas": 3,
            "integration_stage": "planned_later",
            "notes": "Potential pediatric/rare-cancer expansion source.",
        },
    ]


def build_xena_dataset_seed_dataframe(records=None):
    """
    Build curated Xena dataset seed DataFrame.
    """
    if records is None:
        records = get_xena_dataset_seed_records()

    df = pd.DataFrame(records)

    for column in XENA_DATASET_SEED_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    df = df.loc[:, XENA_DATASET_SEED_COLUMNS].copy()
    df = df.sort_values(
        by=["priority_for_atlas", "recommended_for_first_integration", "dataset_seed_id"],
        ascending=[False, False, True],
        kind="stable",
    ).reset_index(drop=True)

    return df


def filter_xena_dataset_seed_inventory(
    df,
    hub_id=None,
    omics_modality=None,
    data_category=None,
    recommended_only=False,
    min_priority=None,
):
    """
    Filter curated Xena dataset seed inventory.
    """
    out = df.copy()

    if hub_id:
        query = str(hub_id).strip().lower()
        out = out[
            out["hub_id"].astype(str).str.lower().str.contains(query, regex=False)
        ]

    if omics_modality:
        query = str(omics_modality).strip().lower()
        out = out[
            out["omics_modality"].astype(str).str.lower().str.contains(query, regex=False)
        ]

    if data_category:
        query = str(data_category).strip().lower()
        out = out[
            out["data_category"].astype(str).str.lower().str.contains(query, regex=False)
        ]

    if recommended_only:
        out = out[out["recommended_for_first_integration"].astype(bool)]

    if min_priority is not None:
        out = out[out["priority_for_atlas"].astype(int) >= int(min_priority)]

    return out.reset_index(drop=True)


def write_xena_dataset_seed_inventory(
    output_path=DEFAULT_OUTPUT,
    hub_id=None,
    omics_modality=None,
    data_category=None,
    recommended_only=False,
    min_priority=None,
):
    """
    Write curated Xena dataset seed inventory to TSV.
    """
    df = build_xena_dataset_seed_dataframe()
    df = filter_xena_dataset_seed_inventory(
        df=df,
        hub_id=hub_id,
        omics_modality=omics_modality,
        data_category=data_category,
        recommended_only=recommended_only,
        min_priority=min_priority,
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, sep="\t", index=False)

    return df


def build_arg_parser():
    """
    Build CLI parser.
    """
    parser = argparse.ArgumentParser(
        description="Write curated UCSC Xena dataset seed inventory."
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output Xena dataset seed inventory TSV. Default: {DEFAULT_OUTPUT}",
    )

    parser.add_argument("--hub-id", default=None, help="Optional hub ID text filter.")
    parser.add_argument(
        "--omics-modality",
        default=None,
        help="Optional omics modality text filter.",
    )
    parser.add_argument(
        "--data-category",
        default=None,
        help="Optional data category text filter.",
    )
    parser.add_argument(
        "--recommended-only",
        action="store_true",
        help="Keep only dataset seeds recommended for first integration wave.",
    )
    parser.add_argument(
        "--min-priority",
        type=int,
        default=None,
        help="Keep only dataset seeds with priority_for_atlas >= this value.",
    )

    return parser


def main(argv=None):
    """
    CLI entrypoint.
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        df = write_xena_dataset_seed_inventory(
            output_path=args.output,
            hub_id=args.hub_id,
            omics_modality=args.omics_modality,
            data_category=args.data_category,
            recommended_only=args.recommended_only,
            min_priority=args.min_priority,
        )
    except Exception as exc:
        print(f"ERROR: Failed to write Xena dataset seed inventory: {exc}", file=sys.stderr)
        return 1

    print("UCSC Xena dataset seed inventory complete.")
    print(f"Rows: {len(df)}")
    print(f"Output: {args.output}")

    if not df.empty:
        print("Top Xena dataset seeds:")
        for _, row in df.head(12).iterrows():
            print(
                f"  {row['dataset_seed_id']} | "
                f"hub={row['hub_id']} | "
                f"modality={row['omics_modality']} | "
                f"priority={row['priority_for_atlas']} | "
                f"stage={row['integration_stage']}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
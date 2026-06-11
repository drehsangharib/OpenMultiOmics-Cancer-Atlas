#!/usr/bin/env python3

"""
UCSC Xena Hub Inventory

Create a curated inventory of UCSC Xena public data hubs relevant to
cancer multi-omics atlas construction.

Output:
    outputs/dataset_inventory/xena_hub_inventory.tsv

Example:
    python -m core.search.xena_hub_inventory
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

import pandas as pd


DEFAULT_OUTPUT = Path("outputs/dataset_inventory/xena_hub_inventory.tsv")


XENA_HUB_COLUMNS = [
    "hub_id",
    "hub_name",
    "hub_url",
    "source_scope",
    "primary_resources",
    "omics_scope",
    "cancer_relevance",
    "access_type",
    "recommended_for_first_integration",
    "priority_for_atlas",
    "integration_stage",
    "notes",
]


XENA_HUB_RECORDS = [{'hub_id': 'ucsc_public', 'hub_name': 'UCSC Public Hub', 'hub_url': 'https://ucscpublic.xenahubs.net', 'source_scope': 'broad public genomics and cancer resources', 'primary_resources': 'TCGA; TARGET; GTEx; CCLE; other public resources', 'omics_scope': 'transcriptomics; phenotype; copy number; methylation; mutation; pan-cancer matrices', 'cancer_relevance': 'broad public cancer and normal-tissue comparison hub', 'access_type': 'open public matrices', 'recommended_for_first_integration': True, 'priority_for_atlas': 5, 'integration_stage': 'planned_next', 'notes': 'Strong first Xena target because of broad public coverage and ready-to-use matrices.'}, {'hub_id': 'gdc_xena', 'hub_name': 'GDC Xena Hub', 'hub_url': 'https://gdc.xenahubs.net', 'source_scope': 'GDC-derived public matrices', 'primary_resources': 'GDC; TCGA harmonized data', 'omics_scope': 'transcriptomics; phenotype; copy number; mutation; methylation where available', 'cancer_relevance': 'Useful cross-check and matrix access layer for current GDC pipeline', 'access_type': 'open public matrices', 'recommended_for_first_integration': True, 'priority_for_atlas': 5, 'integration_stage': 'planned_next', 'notes': 'Best companion to the existing GDC metadata pipeline.'}, {'hub_id': 'tcga_xena', 'hub_name': 'TCGA Xena Hub', 'hub_url': 'https://tcga.xenahubs.net', 'source_scope': 'TCGA legacy cancer cohorts', 'primary_resources': 'TCGA', 'omics_scope': 'transcriptomics; copy number; methylation; mutation; clinical phenotype', 'cancer_relevance': 'High-value TCGA matrix source for cancer-specific atlas modules', 'access_type': 'open public matrices', 'recommended_for_first_integration': True, 'priority_for_atlas': 5, 'integration_stage': 'planned_next', 'notes': 'Useful for TCGA cohort-level matrices and comparison with GDC project ranking.'}, {'hub_id': 'pancanatlas', 'hub_name': 'Pan-Cancer Atlas Hub', 'hub_url': 'https://pancanatlas.xenahubs.net', 'source_scope': 'TCGA Pan-Cancer Atlas', 'primary_resources': 'TCGA Pan-Cancer Atlas', 'omics_scope': 'pan-cancer expression; copy number; mutation; clinical; subtype annotations', 'cancer_relevance': 'Strong source for pan-cancer atlas views and cross-cancer comparisons', 'access_type': 'open public matrices', 'recommended_for_first_integration': True, 'priority_for_atlas': 5, 'integration_stage': 'planned_next', 'notes': 'Important for pan-cancer summary modules.'}, {'hub_id': 'toil_xena', 'hub_name': 'UCSC Toil RNA-seq Recompute Hub', 'hub_url': 'https://toil.xenahubs.net', 'source_scope': 'uniformly recomputed RNA-seq compendium', 'primary_resources': 'TCGA; GTEx; TARGET and related public RNA-seq resources', 'omics_scope': 'transcriptomics; tumor-normal expression comparison', 'cancer_relevance': 'High-value tumor-normal RNA-seq comparison resource', 'access_type': 'open public matrices', 'recommended_for_first_integration': True, 'priority_for_atlas': 5, 'integration_stage': 'planned_next', 'notes': 'Useful for tumor-vs-normal expression modules.'}, {'hub_id': 'icgc_xena', 'hub_name': 'ICGC Xena Hub', 'hub_url': 'https://icgc.xenahubs.net', 'source_scope': 'ICGC public cancer resources', 'primary_resources': 'ICGC', 'omics_scope': 'genomics; transcriptomics; clinical phenotype where available', 'cancer_relevance': 'International cancer genomics complement to GDC and TCGA', 'access_type': 'open public matrices where available', 'recommended_for_first_integration': False, 'priority_for_atlas': 4, 'integration_stage': 'planned', 'notes': 'Useful after core Xena/GDC/TCGA hub integration.'}, {'hub_id': 'pcawg_xena', 'hub_name': 'PCAWG Xena Hub', 'hub_url': 'https://pcawg.xenahubs.net', 'source_scope': 'Pan-Cancer Analysis of Whole Genomes', 'primary_resources': 'PCAWG', 'omics_scope': 'whole-genome-derived cancer features; phenotype; pan-cancer annotations', 'cancer_relevance': 'Important for whole-genome pan-cancer modules', 'access_type': 'open public matrices where available', 'recommended_for_first_integration': False, 'priority_for_atlas': 4, 'integration_stage': 'planned', 'notes': 'Useful later for WGS-focused pan-cancer atlas layers.'}, {'hub_id': 'atacseq_xena', 'hub_name': 'ATAC-seq Xena Hub', 'hub_url': 'https://atacseq.xenahubs.net', 'source_scope': 'public chromatin accessibility resources', 'primary_resources': 'ATAC-seq datasets', 'omics_scope': 'chromatin accessibility; regulatory genomics', 'cancer_relevance': 'Useful for regulatory atlas expansion', 'access_type': 'open public matrices', 'recommended_for_first_integration': False, 'priority_for_atlas': 3, 'integration_stage': 'planned_later', 'notes': 'Useful later after transcriptomic/genomic core inventory is stable.'}, {'hub_id': 'treehouse_xena', 'hub_name': 'Treehouse Xena Hub', 'hub_url': 'https://xena.treehouse.gi.ucsc.edu:443', 'source_scope': 'Treehouse pediatric cancer and public RNA-seq resources', 'primary_resources': 'Treehouse', 'omics_scope': 'transcriptomics; phenotype', 'cancer_relevance': 'Useful for pediatric and rare cancer expression modules', 'access_type': 'open public matrices where available', 'recommended_for_first_integration': False, 'priority_for_atlas': 3, 'integration_stage': 'planned_later', 'notes': 'Potential pediatric/rare-cancer expansion source.'}]


@dataclass(frozen=True)
class XenaHub:
    hub_id: str
    hub_name: str
    hub_url: str
    source_scope: str
    primary_resources: str
    omics_scope: str
    cancer_relevance: str
    access_type: str
    recommended_for_first_integration: bool
    priority_for_atlas: int
    integration_stage: str
    notes: str

    def to_record(self) -> dict:
        return asdict(self)


def get_xena_hub_records() -> List[dict]:
    return [dict(record) for record in XENA_HUB_RECORDS]


def get_xena_hubs() -> List[XenaHub]:
    return [XenaHub(**record) for record in get_xena_hub_records()]


def build_xena_hub_inventory_dataframe(
    hubs: Optional[List[XenaHub]] = None,
) -> pd.DataFrame:
    if hubs is None:
        hubs = get_xena_hubs()

    records = []
    for hub in hubs:
        if isinstance(hub, XenaHub):
            records.append(hub.to_record())
        else:
            records.append(dict(hub))

    df = pd.DataFrame(records)

    for column in XENA_HUB_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    df = df.loc[:, XENA_HUB_COLUMNS].copy()
    df = df.sort_values(
        by=["priority_for_atlas", "recommended_for_first_integration", "hub_id"],
        ascending=[False, False, True],
        kind="stable",
    ).reset_index(drop=True)

    return df


def filter_xena_hub_inventory(
    df: pd.DataFrame,
    hub_id: Optional[str] = None,
    omics_scope: Optional[str] = None,
    recommended_only: bool = False,
    min_priority: Optional[int] = None,
) -> pd.DataFrame:
    out = df.copy()

    if hub_id:
        query = str(hub_id).strip().lower()
        out = out[
            out["hub_id"].astype(str).str.lower().str.contains(query, regex=False)
        ]

    if omics_scope:
        query = str(omics_scope).strip().lower()
        out = out[
            out["omics_scope"].astype(str).str.lower().str.contains(query, regex=False)
        ]

    if recommended_only:
        out = out[out["recommended_for_first_integration"].astype(bool)]

    if min_priority is not None:
        out = out[out["priority_for_atlas"].astype(int) >= int(min_priority)]

    return out.reset_index(drop=True)


def write_xena_hub_inventory(
    output_path: Path = DEFAULT_OUTPUT,
    hub_id: Optional[str] = None,
    omics_scope: Optional[str] = None,
    recommended_only: bool = False,
    min_priority: Optional[int] = None,
) -> pd.DataFrame:
    df = build_xena_hub_inventory_dataframe()
    df = filter_xena_hub_inventory(
        df=df,
        hub_id=hub_id,
        omics_scope=omics_scope,
        recommended_only=recommended_only,
        min_priority=min_priority,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, sep="\t", index=False)

    return df


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write curated UCSC Xena hub inventory."
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output Xena hub inventory TSV.",
    )
    parser.add_argument("--hub-id", default=None, help="Optional hub ID text filter.")
    parser.add_argument(
        "--omics-scope",
        default=None,
        help="Optional omics scope text filter.",
    )
    parser.add_argument(
        "--recommended-only",
        action="store_true",
        help="Keep only hubs recommended for first integration wave.",
    )
    parser.add_argument(
        "--min-priority",
        type=int,
        default=None,
        help="Keep only hubs with priority_for_atlas >= this value.",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        df = write_xena_hub_inventory(
            output_path=args.output,
            hub_id=args.hub_id,
            omics_scope=args.omics_scope,
            recommended_only=args.recommended_only,
            min_priority=args.min_priority,
        )
    except Exception as exc:
        print("ERROR: Failed to write Xena hub inventory: " + str(exc), file=sys.stderr)
        return 1

    print("UCSC Xena hub inventory complete.")
    print("Rows: " + str(len(df)))
    print("Output: " + str(args.output))

    if not df.empty:
        print("Top Xena hubs:")
        for _, row in df.head(10).iterrows():
            print(
                "  {hub_id} | priority={priority} | stage={stage} | name={name}".format(
                    hub_id=row["hub_id"],
                    priority=row["priority_for_atlas"],
                    stage=row["integration_stage"],
                    name=row["hub_name"],
                )
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

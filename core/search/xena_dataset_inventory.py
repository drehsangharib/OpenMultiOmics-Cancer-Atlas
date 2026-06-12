#!/usr/bin/env python3

"""
UCSC Xena Dataset Inventory

Project:
    OpenMultiOmics-Cancer-Atlas

Purpose:
    Query selected UCSC Xena hubs and build a metadata-only dataset inventory.

This module does not download large molecular matrices. It only retrieves
dataset identifiers/names from Xena hubs and infers broad metadata fields for
atlas discovery and prioritization.

Output:
    outputs/dataset_inventory/xena_dataset_inventory.tsv

Examples:
    python -m core.search.xena_dataset_inventory --hub-id gdc_xena
    python -m core.search.xena_dataset_inventory --hub-id tcga_xena
    python -m core.search.xena_dataset_inventory --recommended-only
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

import pandas as pd

from core.search.xena_hub_inventory import (
    build_xena_hub_inventory_dataframe,
)


DEFAULT_OUTPUT = Path("outputs/dataset_inventory/xena_dataset_inventory.tsv")


XENA_DATASET_COLUMNS = [
    "hub_id",
    "hub_name",
    "hub_url",
    "dataset_id",
    "dataset_name",
    "dataset_label",
    "data_category",
    "omics_modality",
    "matrix_type",
    "resource_family",
    "cancer_scope",
    "sample_scope",
    "priority_for_atlas",
    "integration_stage",
    "source_database",
    "notes",
]


def normalize_text(value: object) -> str:
    """
    Normalize values to stripped strings.
    """
    if value is None:
        return ""
    return str(value).strip()


def normalize_lower(value: object) -> str:
    """
    Normalize values to lowercase strings.
    """
    return normalize_text(value).lower()


def parse_xena_dataset_response(payload: Any) -> List[str]:
    """
    Parse a Xena datasets response into dataset identifier strings.

    Xena hubs usually return a list of dataset names for the ["datasets"] query.
    This parser also handles simple dictionaries defensively.
    """
    datasets: List[str] = []

    if payload is None:
        return datasets

    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, str):
                datasets.append(item)
            elif isinstance(item, dict):
                candidate = (
                    item.get("name")
                    or item.get("dataset")
                    or item.get("id")
                    or item.get("label")
                )
                if candidate:
                    datasets.append(str(candidate))
        return datasets

    if isinstance(payload, dict):
        for key in ["datasets", "data", "items", "results"]:
            value = payload.get(key)
            if isinstance(value, list):
                return parse_xena_dataset_response(value)

        for value in payload.values():
            if isinstance(value, str):
                datasets.append(value)

    return datasets


def query_xena_hub_datasets(
    hub_url: str,
    timeout: int = 60,
) -> List[str]:
    """
    Query a Xena hub for dataset identifiers.

    Xena hubs expose query access through the /data/ endpoint. Different hubs
    and server versions can be sensitive to query shape, so this function tries
    several metadata-only dataset-list queries.

    This function does not download molecular matrix data.
    """
    endpoint = hub_url.rstrip("/") + "/data/"

    queries = [
        # Direct relational query shown in Xena server API documentation style.
        '{:select [:name] :from [:dataset]}',

        # Full dataset table fallback.
        '{:select [:*] :from [:dataset]}',

        # xenaPython-style Scheme query over the dataset table.
        '(map :name (query {:select [:name] :from [:dataset]}))',

        # xenaPython allDatasets-style query with common non-assay types excluded.
        '((fn [exclude] '
        '  (map :name '
        '    (query {:select [:name] '
        '            :from [:dataset] '
        '            :where [:not [:in :type exclude]]}))) '
        ' ["probeMap" "probemap" "genePredExt"])',
    ]

    errors = []

    for query in queries:
        request = urllib.request.Request(
            endpoint,
            data=query.encode("utf-8"),
            headers={"Content-Type": "text/plain"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                text = response.read().decode("utf-8")
        except Exception as exc:
            errors.append(f"{query}: {exc}")
            continue

        try:
            payload = json.loads(text)
        except Exception as exc:
            errors.append(f"{query}: non-JSON response: {text[:200]} | {exc}")
            continue

        datasets = parse_xena_dataset_response(payload)
        datasets = [dataset for dataset in datasets if normalize_text(dataset)]
        datasets = [
            dataset
            for dataset in datasets
            if normalize_lower(dataset) not in {"datasets", "name", "dataset"}
        ]

        if datasets:
            return datasets

        errors.append(f"{query}: empty dataset result; raw={str(payload)[:200]}")

    raise RuntimeError("All Xena dataset-list queries failed: " + " ; ".join(errors))



def infer_data_category(dataset_text: str) -> str:
    """
    Infer broad data category from dataset identifier/name text.
    """
    text = normalize_lower(dataset_text)

    if any(token in text for token in ["probemap", "probe_map", "genemap", "gene_map"]):
        return "annotation map"

    if any(token in text for token in ["clinical", "phenotype", "survival", "clinicalmatrix"]):
        return "clinical phenotype"

    if any(token in text for token in ["immune", "immunesig", "immunesigs"]):
        return "immune signature"

    if any(token in text for token in ["ssgsea", "gsva", "geneset", "genesets", "gene_set"]):
        return "pathway activity"

    if any(token in text for token in ["drugtarget", "drug_target", "geneprogram", "gene_program"]):
        return "pathway or target signature"

    if "stemness" in text and any(token in text for token in ["rna", "rnaseq", "rnaexp"]):
        return "transcriptomic signature"

    if "stemness" in text and any(token in text for token in ["dna", "meth", "methyl", "dnameth"]):
        return "methylation signature"

    if any(token in text for token in ["hrd", "homologous_recombination", "genomic_instability"]):
        return "genomic instability"

    if any(token in text for token in ["mirna", "mi-rna", "micro_rna", "mirs"]):
        return "miRNA expression"

    if any(
        token in text
        for token in [
            "hiseq",
            "rnaseq",
            "rna-seq",
            "rsem",
            "tpm",
            "fpkm",
            "htseq",
            "gene expression",
            "geneexp",
            "rnaexp",
            "expression",
        ]
    ):
        return "gene expression"

    if any(token in text for token in ["methyl", "methy", "dnameth"]):
        return "DNA methylation"

    if any(
        token in text
        for token in [
            "copy",
            "cnv",
            "cna",
            "gistic",
            "segment",
            "snp_6",
            "snp6",
            "genome_wide_snp",
        ]
    ):
        return "copy number"

    if any(
        token in text
        for token in [
            "mutation",
            "mut",
            "maf",
            "snv",
            "variant",
            "mc3",
            "nonsilent",
            "non_silent",
        ]
    ):
        return "somatic mutation"

    if any(token in text for token in ["protein", "proteome", "rppa", "phospho"]):
        return "protein abundance"

    if any(token in text for token in ["atac", "peak", "chromatin"]):
        return "chromatin accessibility"

    if any(token in text for token in ["subtype", "cluster", "icluster", "annotation"]):
        return "subtype annotation"

    return "unknown"


def infer_omics_modality(dataset_text: str) -> str:
    """
    Infer broad omics modality from dataset identifier/name text.
    """
    category = infer_data_category(dataset_text)

    if category in {"clinical phenotype", "subtype annotation"}:
        return "clinical_annotation"

    if category in {"gene expression", "miRNA expression", "transcriptomic signature"}:
        return "transcriptomics"

    if category in {"DNA methylation", "methylation signature"}:
        return "methylation"

    if category == "copy number":
        return "cnv"

    if category == "somatic mutation":
        return "snv"

    if category == "protein abundance":
        return "proteomics"

    if category == "chromatin accessibility":
        return "chromatin_accessibility"

    if category in {"immune signature", "pathway activity", "pathway or target signature"}:
        return "functional_signature"

    if category == "genomic instability":
        return "genomic_signature"

    if category == "annotation map":
        return "annotation_map"

    return "unknown"


def infer_matrix_type(dataset_text: str) -> str:
    """
    Infer likely matrix type from dataset identifier/name text.
    """
    modality = infer_omics_modality(dataset_text)
    category = infer_data_category(dataset_text)
    text = normalize_lower(dataset_text)

    if modality == "transcriptomics":
        if category == "miRNA expression":
            return "sample-by-miRNA expression matrix"
        if category == "transcriptomic signature":
            return "sample-by-signature score matrix"
        return "sample-by-gene expression matrix"

    if modality == "clinical_annotation":
        return "sample-by-feature annotation table"

    if modality == "methylation":
        if category == "methylation signature":
            return "sample-by-signature score matrix"
        return "sample-by-probe methylation matrix"

    if modality == "cnv":
        if "segment" in text:
            return "sample-by-segment copy-number matrix"
        return "sample-by-gene copy-number matrix"

    if modality == "snv":
        return "sample-by-gene mutation feature matrix"

    if modality == "proteomics":
        return "sample-by-protein abundance matrix"

    if modality == "chromatin_accessibility":
        return "sample-by-peak accessibility matrix"

    if modality == "functional_signature":
        return "sample-by-signature score matrix"

    if modality == "genomic_signature":
        return "sample-by-genomic-signature score matrix"

    if modality == "annotation_map":
        return "feature annotation map"

    return "unknown"

def infer_resource_family(hub_id: str, hub_row: Dict[str, Any], dataset_text: str) -> str:
    """
    Infer resource family using hub metadata and dataset text.
    """
    text = normalize_lower(dataset_text)

    if "tcga" in text:
        return "TCGA"

    if "gdc" in text:
        return "GDC"

    if "gtex" in text:
        return "GTEx"

    if "target" in text:
        return "TARGET"

    if "ccle" in text:
        return "CCLE"

    if "pcawg" in text:
        return "PCAWG"

    if "icgc" in text:
        return "ICGC"

    if "treehouse" in text:
        return "Treehouse"

    primary_resources = normalize_text(hub_row.get("primary_resources", ""))
    if primary_resources:
        return primary_resources

    return hub_id


def infer_cancer_scope(hub_id: str, hub_row: Dict[str, Any], dataset_text: str) -> str:
    """
    Infer cancer scope from hub metadata and dataset text.
    """
    text = normalize_lower(dataset_text)

    if "pancan" in text or "pan-cancer" in text or hub_id == "pancanatlas":
        return "pan-cancer"

    if "gtex" in text:
        return "tumor-normal comparison"

    if "ccle" in text:
        return "cancer cell lines"

    if hub_id == "treehouse_xena":
        return "pediatric and rare cancer"

    if hub_id == "pcawg_xena":
        return "whole-genome pan-cancer"

    if "tcga" in text or hub_id in {"gdc_xena", "tcga_xena"}:
        return "TCGA cancer cohorts"

    scope = normalize_text(hub_row.get("source_scope", ""))
    if scope:
        return scope

    return "unknown"


def infer_sample_scope(dataset_text: str) -> str:
    """
    Infer sample scope from dataset text.
    """
    text = normalize_lower(dataset_text)

    if any(token in text for token in ["gtex", "normal"]):
        return "tumor and normal samples"

    if any(token in text for token in ["ccle", "cellline", "cell_line"]):
        return "cancer cell lines"

    if any(token in text for token in ["clinical", "phenotype", "survival", "samplemap"]):
        return "patients and samples"

    return "samples"


def infer_dataset_priority(
    hub_priority: int,
    omics_modality: str,
    data_category: str,
) -> int:
    """
    Infer dataset priority using hub priority and modality/category.
    """
    priority = int(hub_priority)

    if omics_modality in {
        "transcriptomics",
        "clinical_annotation",
        "methylation",
        "cnv",
        "snv",
    }:
        priority += 1

    if data_category == "unknown":
        priority -= 1

    return max(1, min(5, priority))


def build_dataset_label(dataset_id: str) -> str:
    """
    Build readable dataset label from dataset ID.
    """
    label = dataset_id.replace("/", " / ")
    label = label.replace("_", " ")
    label = label.replace("-", " ")
    label = " ".join(label.split())
    return label[:180]


def build_xena_dataset_record(
    hub_row: Dict[str, Any],
    dataset_id: str,
) -> Dict[str, Any]:
    """
    Build one normalized dataset inventory record.
    """
    hub_id = normalize_text(hub_row.get("hub_id", ""))
    hub_priority = int(hub_row.get("priority_for_atlas", 3))

    data_category = infer_data_category(dataset_id)
    omics_modality = infer_omics_modality(dataset_id)
    matrix_type = infer_matrix_type(dataset_id)
    priority = infer_dataset_priority(
        hub_priority=hub_priority,
        omics_modality=omics_modality,
        data_category=data_category,
    )

    return {
        "hub_id": hub_id,
        "hub_name": normalize_text(hub_row.get("hub_name", "")),
        "hub_url": normalize_text(hub_row.get("hub_url", "")),
        "dataset_id": normalize_text(dataset_id),
        "dataset_name": normalize_text(dataset_id),
        "dataset_label": build_dataset_label(dataset_id),
        "data_category": data_category,
        "omics_modality": omics_modality,
        "matrix_type": matrix_type,
        "resource_family": infer_resource_family(hub_id, hub_row, dataset_id),
        "cancer_scope": infer_cancer_scope(hub_id, hub_row, dataset_id),
        "sample_scope": infer_sample_scope(dataset_id),
        "priority_for_atlas": priority,
        "integration_stage": "live_inventory",
        "source_database": "UCSC Xena",
        "notes": "Metadata-only inventory; matrix data not downloaded.",
    }


def select_hubs(
    hub_inventory_df: pd.DataFrame,
    hub_ids: Optional[Iterable[str]] = None,
    recommended_only: bool = False,
    min_priority: Optional[int] = None,
) -> pd.DataFrame:
    """
    Select hubs to query from the curated Xena hub inventory.
    """
    out = hub_inventory_df.copy()

    if hub_ids:
        wanted = {normalize_lower(hub_id) for hub_id in hub_ids}
        out = out[out["hub_id"].astype(str).str.lower().isin(wanted)]

    if recommended_only:
        out = out[out["recommended_for_first_integration"].astype(bool)]

    if min_priority is not None:
        out = out[out["priority_for_atlas"].astype(int) >= int(min_priority)]

    return out.reset_index(drop=True)


def build_xena_dataset_inventory_dataframe(
    hub_inventory_df: Optional[pd.DataFrame] = None,
    hub_ids: Optional[Iterable[str]] = None,
    recommended_only: bool = False,
    min_priority: Optional[int] = None,
    timeout: int = 60,
    sleep_seconds: float = 0.0,
    allow_failures: bool = True,
    query_func: Callable[[str, int], List[str]] = query_xena_hub_datasets,
) -> pd.DataFrame:
    """
    Query selected Xena hubs and build dataset inventory DataFrame.
    """
    if hub_inventory_df is None:
        hub_inventory_df = build_xena_hub_inventory_dataframe()

    selected_hubs = select_hubs(
        hub_inventory_df=hub_inventory_df,
        hub_ids=hub_ids,
        recommended_only=recommended_only,
        min_priority=min_priority,
    )

    records: List[Dict[str, Any]] = []

    for _, hub_row_series in selected_hubs.iterrows():
        hub_row = hub_row_series.to_dict()
        hub_url = normalize_text(hub_row.get("hub_url", ""))
        hub_id = normalize_text(hub_row.get("hub_id", ""))

        try:
            dataset_ids = query_func(hub_url, timeout)
        except Exception as exc:
            if not allow_failures:
                raise
            records.append(
                {
                    "hub_id": hub_id,
                    "hub_name": normalize_text(hub_row.get("hub_name", "")),
                    "hub_url": hub_url,
                    "dataset_id": "",
                    "dataset_name": "",
                    "dataset_label": "",
                    "data_category": "query_error",
                    "omics_modality": "unknown",
                    "matrix_type": "unknown",
                    "resource_family": normalize_text(hub_row.get("primary_resources", "")),
                    "cancer_scope": normalize_text(hub_row.get("source_scope", "")),
                    "sample_scope": "unknown",
                    "priority_for_atlas": int(hub_row.get("priority_for_atlas", 1)),
                    "integration_stage": "query_error",
                    "source_database": "UCSC Xena",
                    "notes": f"Hub query failed: {exc}",
                }
            )
            continue

        for dataset_id in sorted(set(dataset_ids)):
            if not normalize_text(dataset_id):
                continue
            records.append(
                build_xena_dataset_record(
                    hub_row=hub_row,
                    dataset_id=dataset_id,
                )
            )

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    df = pd.DataFrame(records)

    for column in XENA_DATASET_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    df = df.loc[:, XENA_DATASET_COLUMNS].copy()

    if not df.empty:
        df = df.sort_values(
            by=["priority_for_atlas", "hub_id", "omics_modality", "dataset_id"],
            ascending=[False, True, True, True],
            kind="stable",
        ).reset_index(drop=True)

    return df


def write_xena_dataset_inventory(
    output_path: Path = DEFAULT_OUTPUT,
    hub_ids: Optional[Iterable[str]] = None,
    recommended_only: bool = False,
    min_priority: Optional[int] = None,
    timeout: int = 60,
    sleep_seconds: float = 0.0,
    allow_failures: bool = True,
) -> pd.DataFrame:
    """
    Write live Xena dataset inventory to TSV.
    """
    df = build_xena_dataset_inventory_dataframe(
        hub_ids=hub_ids,
        recommended_only=recommended_only,
        min_priority=min_priority,
        timeout=timeout,
        sleep_seconds=sleep_seconds,
        allow_failures=allow_failures,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, sep="\t", index=False)

    return df


def build_arg_parser() -> argparse.ArgumentParser:
    """
    Build CLI parser.
    """
    parser = argparse.ArgumentParser(
        description="Build metadata-only UCSC Xena dataset inventory."
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output Xena dataset inventory TSV. Default: {DEFAULT_OUTPUT}",
    )

    parser.add_argument(
        "--hub-id",
        action="append",
        default=None,
        help="Hub ID to query. Can be repeated, e.g. --hub-id gdc_xena.",
    )

    parser.add_argument(
        "--recommended-only",
        action="store_true",
        help="Query only hubs recommended for first integration.",
    )

    parser.add_argument(
        "--min-priority",
        type=int,
        default=None,
        help="Query only hubs with priority_for_atlas >= this value.",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="HTTP timeout in seconds.",
    )

    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.0,
        help="Optional sleep between hub queries.",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail immediately if a hub query fails.",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    CLI entrypoint.
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        df = write_xena_dataset_inventory(
            output_path=args.output,
            hub_ids=args.hub_id,
            recommended_only=args.recommended_only,
            min_priority=args.min_priority,
            timeout=args.timeout,
            sleep_seconds=args.sleep_seconds,
            allow_failures=not args.strict,
        )
    except (urllib.error.URLError, TimeoutError, Exception) as exc:
        print(f"ERROR: Failed to build Xena dataset inventory: {exc}", file=sys.stderr)
        return 1

    print("UCSC Xena dataset inventory complete.")
    print(f"Rows: {len(df)}")
    print(f"Output: {args.output}")

    if not df.empty:
        print("Top Xena datasets:")
        preview = df.head(15)
        for _, row in preview.iterrows():
            print(
                f"  {row['hub_id']} | "
                f"modality={row['omics_modality']} | "
                f"category={row['data_category']} | "
                f"dataset={row['dataset_id']}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
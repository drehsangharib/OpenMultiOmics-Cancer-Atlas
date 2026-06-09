#!/usr/bin/env python3

"""
GDC File Counts by Project

Project:
    OpenMultiOmics-Cancer-Atlas

Purpose:
    Query public GDC file metadata and summarize file availability by project,
    data category, data type, experimental strategy, workflow type, data format,
    and access level.

Notes:
    - This module uses public metadata from the GDC files endpoint.
    - It does not download controlled-access data.
    - Generated outputs are written to outputs/dataset_inventory/ and should not
      be committed unless intentionally curated.

Examples:
    python -m core.search.gdc_file_counts_by_project --project-id TCGA-GBM
    python -m core.search.gdc_file_counts_by_project --project-id TCGA-GBM --project-id TCGA-LUAD
    python -m core.search.gdc_file_counts_by_project --project-limit 5
    python -m core.search.gdc_file_counts_by_project
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
import requests


GDC_API_BASE_URL = "https://api.gdc.cancer.gov"
GDC_FILES_ENDPOINT = f"{GDC_API_BASE_URL}/files"

DEFAULT_PROJECT_INVENTORY = Path("outputs/dataset_inventory/gdc_project_inventory.tsv")
DEFAULT_OUTPUT = Path("outputs/dataset_inventory/gdc_file_counts_by_project.tsv")

DEFAULT_FIELDS = [
    "file_id",
    "data_category",
    "data_type",
    "experimental_strategy",
    "analysis.workflow_type",
    "data_format",
    "access",
    "cases.project.project_id",
]

FILE_LEVEL_COLUMNS = [
    "project_id",
    "data_category",
    "data_type",
    "experimental_strategy",
    "workflow_type",
    "data_format",
    "access",
]

OUTPUT_COLUMNS = [
    "project_id",
    "data_category",
    "data_type",
    "experimental_strategy",
    "workflow_type",
    "data_format",
    "access",
    "file_count",
    "source_database",
    "source_endpoint",
    "atlas_scope",
    "public_data_use",
]


def safe_get_nested(record: Dict[str, Any], path: str, default: Any = None) -> Any:
    """
    Safely retrieve nested dictionary values using dot-separated paths.
    """
    current: Any = record

    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default

    return current


def normalize_value(value: Any) -> str:
    """
    Convert GDC values into TSV-safe strings.
    """
    if value is None:
        return ""

    if isinstance(value, (list, tuple, set)):
        if not value:
            return ""
        return "; ".join(str(v) for v in value)

    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)

    return str(value)


def make_project_filter(project_id: str) -> Dict[str, Any]:
    """
    Build a GDC API filter for one project ID.
    """
    return {
        "op": "=",
        "content": {
            "field": "cases.project.project_id",
            "value": project_id,
        },
    }


def extract_project_id_from_file_hit(hit: Dict[str, Any], fallback: str = "") -> str:
    """
    Extract project_id from a GDC files endpoint hit.

    GDC file records can contain a list of cases, each with project metadata.
    This function is tolerant to minor response shape differences.
    """
    cases = hit.get("cases", [])

    if isinstance(cases, list) and cases:
        first_case = cases[0]
        project_id = safe_get_nested(first_case, "project.project_id", fallback)
        return normalize_value(project_id)

    if isinstance(cases, dict):
        project_id = safe_get_nested(cases, "project.project_id", fallback)
        return normalize_value(project_id)

    return fallback


def parse_gdc_file_hit(
    hit: Dict[str, Any],
    project_id_fallback: str = "",
) -> Dict[str, str]:
    """
    Flatten one GDC file metadata record into a row.
    """
    project_id = extract_project_id_from_file_hit(hit, fallback=project_id_fallback)

    row = {
        "project_id": normalize_value(project_id),
        "data_category": normalize_value(hit.get("data_category", "")),
        "data_type": normalize_value(hit.get("data_type", "")),
        "experimental_strategy": normalize_value(hit.get("experimental_strategy", "")),
        "workflow_type": normalize_value(
            safe_get_nested(hit, "analysis.workflow_type", "")
        ),
        "data_format": normalize_value(hit.get("data_format", "")),
        "access": normalize_value(hit.get("access", "")),
    }

    return row


def parse_gdc_files_response(
    payload: Dict[str, Any],
    project_id_fallback: str = "",
) -> pd.DataFrame:
    """
    Parse a GDC files endpoint JSON response into a flat file-level DataFrame.
    """
    hits = payload.get("data", {}).get("hits", [])
    rows = [
        parse_gdc_file_hit(hit, project_id_fallback=project_id_fallback)
        for hit in hits
    ]

    return pd.DataFrame(rows, columns=FILE_LEVEL_COLUMNS)


def get_pagination_total(payload: Dict[str, Any]) -> int:
    """
    Retrieve total number of records from GDC pagination metadata.
    """
    total = payload.get("data", {}).get("pagination", {}).get("total", 0)

    try:
        return int(total)
    except Exception:
        return 0


def fetch_files_for_project(
    project_id: str,
    endpoint: str = GDC_FILES_ENDPOINT,
    fields: Optional[Iterable[str]] = None,
    page_size: int = 2000,
    timeout: int = 60,
    sleep_seconds: float = 0.0,
) -> pd.DataFrame:
    """
    Fetch file metadata for one GDC project, with pagination.
    """
    if fields is None:
        fields = DEFAULT_FIELDS

    all_pages: List[pd.DataFrame] = []
    offset = 0
    total: Optional[int] = None

    filters = make_project_filter(project_id)

    while total is None or offset < total:
        params = {
            "filters": json.dumps(filters),
            "fields": ",".join(fields),
            "format": "JSON",
            "size": str(page_size),
            "from": str(offset),
        }

        response = requests.get(endpoint, params=params, timeout=timeout)
        response.raise_for_status()

        payload = response.json()

        if total is None:
            total = get_pagination_total(payload)

        page_df = parse_gdc_files_response(
            payload,
            project_id_fallback=project_id,
        )

        if not page_df.empty:
            all_pages.append(page_df)

        offset += page_size

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

        if total == 0:
            break

    if not all_pages:
        return pd.DataFrame(columns=FILE_LEVEL_COLUMNS)

    return pd.concat(all_pages, ignore_index=True)


def summarize_file_counts(file_df: pd.DataFrame) -> pd.DataFrame:
    """
    Summarize file metadata counts by project and file descriptors.
    """
    if file_df.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    group_cols = [
        "project_id",
        "data_category",
        "data_type",
        "experimental_strategy",
        "workflow_type",
        "data_format",
        "access",
    ]

    normalized = file_df.copy()

    for col in group_cols:
        if col not in normalized.columns:
            normalized[col] = ""
        normalized[col] = normalized[col].fillna("").astype(str)

    summary = (
        normalized.groupby(group_cols, dropna=False)
        .size()
        .reset_index(name="file_count")
        .sort_values(
            by=[
                "project_id",
                "data_category",
                "data_type",
                "experimental_strategy",
                "workflow_type",
                "data_format",
                "access",
            ],
            ascending=True,
            kind="stable",
        )
        .reset_index(drop=True)
    )

    summary["source_database"] = "GDC"
    summary["source_endpoint"] = GDC_FILES_ENDPOINT
    summary["atlas_scope"] = "pan_cancer_public_reference"
    summary["public_data_use"] = "file_availability_summary"

    return summary[OUTPUT_COLUMNS]


def read_project_ids_from_inventory(
    project_inventory_path: Path = DEFAULT_PROJECT_INVENTORY,
    project_limit: Optional[int] = None,
) -> List[str]:
    """
    Read project IDs from a local GDC project inventory TSV.
    """
    if not project_inventory_path.exists():
        raise FileNotFoundError(
            f"Project inventory not found: {project_inventory_path}. "
            "Run `python -m core.search.gdc_project_inventory` first, "
            "or pass one or more --project-id values."
        )

    df = pd.read_csv(project_inventory_path, sep="\t")

    if "project_id" not in df.columns:
        raise ValueError(f"Missing project_id column in {project_inventory_path}")

    project_ids = [str(x) for x in df["project_id"].dropna().unique().tolist()]
    project_ids = sorted(project_ids)

    if project_limit is not None:
        project_ids = project_ids[:project_limit]

    return project_ids


def fetch_and_summarize_projects(
    project_ids: List[str],
    endpoint: str = GDC_FILES_ENDPOINT,
    page_size: int = 2000,
    timeout: int = 60,
    sleep_seconds: float = 0.0,
) -> pd.DataFrame:
    """
    Fetch and summarize file counts for multiple projects.
    """
    all_summaries: List[pd.DataFrame] = []

    for index, project_id in enumerate(project_ids, start=1):
        print(f"[{index}/{len(project_ids)}] Fetching files for {project_id}...")

        file_df = fetch_files_for_project(
            project_id=project_id,
            endpoint=endpoint,
            page_size=page_size,
            timeout=timeout,
            sleep_seconds=sleep_seconds,
        )

        summary_df = summarize_file_counts(file_df)

        if not summary_df.empty:
            all_summaries.append(summary_df)

        print(f"    files: {len(file_df)}; summary rows: {len(summary_df)}")

    if not all_summaries:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    out = pd.concat(all_summaries, ignore_index=True)
    out = out.sort_values(
        by=[
            "project_id",
            "data_category",
            "data_type",
            "experimental_strategy",
            "workflow_type",
            "data_format",
            "access",
        ],
        ascending=True,
        kind="stable",
    ).reset_index(drop=True)

    return out[OUTPUT_COLUMNS]


def write_summary(summary_df: pd.DataFrame, output_path: Path) -> None:
    """
    Write summary TSV and create parent directories if needed.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(output_path, sep="\t", index=False)


def build_gdc_file_counts_by_project(
    output_path: Path = DEFAULT_OUTPUT,
    project_inventory_path: Path = DEFAULT_PROJECT_INVENTORY,
    project_ids: Optional[List[str]] = None,
    project_limit: Optional[int] = None,
    endpoint: str = GDC_FILES_ENDPOINT,
    page_size: int = 2000,
    timeout: int = 60,
    sleep_seconds: float = 0.0,
) -> pd.DataFrame:
    """
    Build a GDC file availability summary by project.
    """
    if project_ids is None or len(project_ids) == 0:
        project_ids = read_project_ids_from_inventory(
            project_inventory_path=project_inventory_path,
            project_limit=project_limit,
        )

    summary_df = fetch_and_summarize_projects(
        project_ids=project_ids,
        endpoint=endpoint,
        page_size=page_size,
        timeout=timeout,
        sleep_seconds=sleep_seconds,
    )

    write_summary(summary_df, output_path)
    return summary_df


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Summarize GDC file availability by project and data type."
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output TSV path. Default: {DEFAULT_OUTPUT}",
    )

    parser.add_argument(
        "--project-inventory",
        type=Path,
        default=DEFAULT_PROJECT_INVENTORY,
        help=f"Local GDC project inventory TSV. Default: {DEFAULT_PROJECT_INVENTORY}",
    )

    parser.add_argument(
        "--project-id",
        action="append",
        default=None,
        help="GDC project ID to query. Can be provided multiple times.",
    )

    parser.add_argument(
        "--project-limit",
        type=int,
        default=None,
        help="Optional limit on number of projects read from inventory.",
    )

    parser.add_argument(
        "--endpoint",
        type=str,
        default=GDC_FILES_ENDPOINT,
        help=f"GDC files endpoint. Default: {GDC_FILES_ENDPOINT}",
    )

    parser.add_argument(
        "--page-size",
        type=int,
        default=2000,
        help="Number of file records per API page.",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="HTTP request timeout in seconds.",
    )

    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.0,
        help="Optional pause between API requests.",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        summary_df = build_gdc_file_counts_by_project(
            output_path=args.output,
            project_inventory_path=args.project_inventory,
            project_ids=args.project_id,
            project_limit=args.project_limit,
            endpoint=args.endpoint,
            page_size=args.page_size,
            timeout=args.timeout,
            sleep_seconds=args.sleep_seconds,
        )
    except requests.RequestException as exc:
        print(f"ERROR: GDC request failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: Failed to build GDC file counts by project: {exc}", file=sys.stderr)
        return 1

    print("GDC file counts by project complete.")
    print(f"Rows: {len(summary_df)}")
    print(f"Output: {args.output}")

    if not summary_df.empty:
        project_count = summary_df["project_id"].nunique()
        print(f"Projects summarized: {project_count}")

        top_categories = (
            summary_df.groupby("data_category")["file_count"]
            .sum()
            .sort_values(ascending=False)
            .head(10)
            .to_dict()
        )

        print("Top data categories:")
        for category, count in top_categories.items():
            print(f"  {category}: {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
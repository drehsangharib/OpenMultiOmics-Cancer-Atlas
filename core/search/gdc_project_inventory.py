#!/usr/bin/env python3

"""
GDC Project Inventory Fetcher

Project:
    OpenMultiOmics-Cancer-Atlas

Purpose:
    Fetch public project-level metadata from the NCI Genomic Data Commons (GDC)
    and write a local pan-cancer project inventory table.

Notes:
    - This module uses only public GDC metadata.
    - Generated outputs are written to outputs/dataset_inventory/ and should not
      be committed unless intentionally curated.
    - Unit tests should not require network access.

Example:
    python -m core.search.gdc_project_inventory
    python -m core.search.gdc_project_inventory --output outputs/dataset_inventory/gdc_project_inventory.tsv
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
import requests


GDC_API_BASE_URL = "https://api.gdc.cancer.gov"
GDC_PROJECTS_ENDPOINT = f"{GDC_API_BASE_URL}/projects"

DEFAULT_OUTPUT = Path("outputs/dataset_inventory/gdc_project_inventory.tsv")

DEFAULT_FIELDS = [
    "project_id",
    "name",
    "primary_site",
    "disease_type",
    "program.name",
    "summary.case_count",
    "summary.file_count",
]


def safe_get_nested(record: Dict[str, Any], path: str, default: Any = None) -> Any:
    """
    Safely retrieve nested dictionary values using dot-separated paths.

    Example:
        safe_get_nested(record, "summary.case_count")
    """
    current: Any = record

    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default

    return current


def normalize_list_or_value(value: Any) -> str:
    """
    Convert lists, tuples, sets, dicts, and scalar values into TSV-safe strings.
    """
    if value is None:
        return ""

    if isinstance(value, (list, tuple, set)):
        return "; ".join(str(v) for v in value)

    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)

    return str(value)


def parse_gdc_project_hit(hit: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert one GDC project API hit into a flat row.

    The GDC API may return nested structures such as:
        program: {name: "TCGA"}
        summary: {case_count: ..., file_count: ...}

    This function is intentionally tolerant so that minor API response
    changes do not immediately break the inventory builder.
    """
    project_id = hit.get("project_id", "")
    name = hit.get("name", "")
    primary_site = hit.get("primary_site", "")
    disease_type = hit.get("disease_type", "")

    program_name = safe_get_nested(hit, "program.name", "")
    case_count = safe_get_nested(hit, "summary.case_count", "")
    file_count = safe_get_nested(hit, "summary.file_count", "")

    row = {
        "project_id": normalize_list_or_value(project_id),
        "project_name": normalize_list_or_value(name),
        "program_name": normalize_list_or_value(program_name),
        "primary_site": normalize_list_or_value(primary_site),
        "disease_type": normalize_list_or_value(disease_type),
        "case_count": normalize_list_or_value(case_count),
        "file_count": normalize_list_or_value(file_count),
        "source_database": "GDC",
        "source_endpoint": GDC_PROJECTS_ENDPOINT,
    }

    return row


def parse_gdc_projects_response(payload: Dict[str, Any]) -> pd.DataFrame:
    """
    Parse a GDC projects endpoint JSON response into a DataFrame.
    """
    hits = payload.get("data", {}).get("hits", [])

    rows = [parse_gdc_project_hit(hit) for hit in hits]

    columns = [
        "project_id",
        "project_name",
        "program_name",
        "primary_site",
        "disease_type",
        "case_count",
        "file_count",
        "source_database",
        "source_endpoint",
    ]

    df = pd.DataFrame(rows, columns=columns)

    if not df.empty:
        df = df.sort_values(
            by=["program_name", "project_id"],
            ascending=[True, True],
            kind="stable",
        ).reset_index(drop=True)

    return df


def fetch_gdc_projects(
    endpoint: str = GDC_PROJECTS_ENDPOINT,
    fields: Optional[Iterable[str]] = None,
    size: int = 1000,
    timeout: int = 60,
) -> pd.DataFrame:
    """
    Fetch project metadata from the GDC projects endpoint.

    Parameters
    ----------
    endpoint:
        GDC projects endpoint URL.
    fields:
        Iterable of field names requested from GDC.
    size:
        Maximum number of project records to return.
    timeout:
        Request timeout in seconds.

    Returns
    -------
    pandas.DataFrame
        Flat project inventory.
    """
    if fields is None:
        fields = DEFAULT_FIELDS

    params = {
        "fields": ",".join(fields),
        "format": "JSON",
        "size": str(size),
    }

    response = requests.get(endpoint, params=params, timeout=timeout)
    response.raise_for_status()

    payload = response.json()
    return parse_gdc_projects_response(payload)


def add_inventory_annotations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add atlas-specific annotations useful for downstream ranking.

    These annotations remain general and public-data-oriented.
    """
    out = df.copy()

    if out.empty:
        out["atlas_scope"] = []
        out["public_data_use"] = []
        return out

    out["atlas_scope"] = "pan_cancer_public_reference"
    out["public_data_use"] = "project_inventory"

    return out


def write_inventory(df: pd.DataFrame, output_path: Path) -> None:
    """
    Write inventory TSV and create parent directories if needed.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, sep="\t", index=False)


def build_gdc_project_inventory(
    output_path: Path = DEFAULT_OUTPUT,
    endpoint: str = GDC_PROJECTS_ENDPOINT,
    size: int = 1000,
    timeout: int = 60,
) -> pd.DataFrame:
    """
    Fetch, annotate, and write the GDC project inventory.
    """
    df = fetch_gdc_projects(endpoint=endpoint, size=size, timeout=timeout)
    df = add_inventory_annotations(df)
    write_inventory(df, output_path)
    return df


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch public GDC project metadata and write a TSV inventory."
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output TSV path. Default: {DEFAULT_OUTPUT}",
    )

    parser.add_argument(
        "--endpoint",
        type=str,
        default=GDC_PROJECTS_ENDPOINT,
        help=f"GDC projects endpoint. Default: {GDC_PROJECTS_ENDPOINT}",
    )

    parser.add_argument(
        "--size",
        type=int,
        default=1000,
        help="Maximum number of project records to retrieve.",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="HTTP request timeout in seconds.",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        df = build_gdc_project_inventory(
            output_path=args.output,
            endpoint=args.endpoint,
            size=args.size,
            timeout=args.timeout,
        )
    except requests.RequestException as exc:
        print(f"ERROR: GDC request failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: Failed to build GDC project inventory: {exc}", file=sys.stderr)
        return 1

    print("GDC project inventory complete.")
    print(f"Rows: {len(df)}")
    print(f"Output: {args.output}")

    if not df.empty:
        program_counts = df["program_name"].value_counts(dropna=False).to_dict()
        print("Program counts:")
        for program, count in program_counts.items():
            print(f"  {program}: {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
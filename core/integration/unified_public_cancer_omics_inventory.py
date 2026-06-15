#!/usr/bin/env python3

"""
Unified Public Cancer Omics Inventory

Project:
    OpenMultiOmics-Cancer-Atlas

Purpose:
    Combine public GDC project-level inventory/ranking records with UCSC Xena
    dataset-level inventory records into one normalized public cancer omics
    inventory table.

Inputs:
    GDC inventory/ranking TSV files from previous GDC pipeline milestones.
    Xena dataset inventory TSV from the Xena metadata pipeline.

Output:
    outputs/dataset_inventory/unified_public_cancer_omics_inventory.tsv

Examples:
    python -m core.integration.unified_public_cancer_omics_inventory

    python -m core.integration.unified_public_cancer_omics_inventory `
      --xena-input outputs/dataset_inventory/xena_dataset_inventory.tsv

    python -m core.integration.unified_public_cancer_omics_inventory `
      --gdc-input outputs/dataset_inventory/gdc_project_priority_ranking.tsv `
      --xena-input outputs/dataset_inventory/xena_dataset_inventory.tsv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd


DEFAULT_OUTPUT = Path("outputs/dataset_inventory/unified_public_cancer_omics_inventory.tsv")

DEFAULT_XENA_INPUT = Path("outputs/dataset_inventory/xena_dataset_inventory.tsv")

GDC_INPUT_CANDIDATES = [
    Path("outputs/dataset_inventory/gdc_project_priority_ranking.tsv"),
    Path("outputs/dataset_inventory/gdc_project_priority_ranked.tsv"),
    Path("outputs/dataset_inventory/gdc_project_priority.tsv"),
    Path("outputs/dataset_inventory/gdc_project_modality_matrix.tsv"),
    Path("outputs/dataset_inventory/gdc_project_inventory.tsv"),
    Path("outputs/reports/gdc_project_priority_ranking.tsv"),
    Path("outputs/gdc_project_priority_ranking.tsv"),
    Path("outputs/gdc_project_inventory.tsv"),
]


UNIFIED_COLUMNS = [
    "source_id",
    "source_name",
    "source_record_type",
    "record_id",
    "record_name",
    "project_id",
    "dataset_id",
    "hub_id",
    "cancer_scope",
    "primary_site",
    "disease_type",
    "data_category",
    "omics_modality",
    "matrix_type",
    "resource_family",
    "sample_scope",
    "case_count",
    "file_count",
    "priority_for_atlas",
    "priority_score",
    "priority_label",
    "integration_stage",
    "source_url",
    "notes",
]


def normalize_text(value: object) -> str:
    """
    Convert a value to a stripped string.
    """
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return str(value).strip()


def first_existing_path(paths: Iterable[Path]) -> Optional[Path]:
    """
    Return first existing path from a list of paths.
    """
    for path in paths:
        if path.exists():
            return path
    return None


def read_tsv_if_exists(path: Path) -> pd.DataFrame:
    """
    Read a TSV file if it exists.
    """
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    return pd.read_csv(path, sep="\t")


def coalesce_row_value(row: pd.Series, candidates: Iterable[str], default: object = "") -> object:
    """
    Return first non-empty value from candidate columns.
    """
    for column in candidates:
        if column in row.index:
            value = row[column]
            text = normalize_text(value)
            if text != "":
                return value
    return default


def to_numeric_or_blank(value: object) -> object:
    """
    Convert value to numeric if possible, otherwise blank.
    """
    text = normalize_text(value)

    if text == "":
        return ""

    numeric = pd.to_numeric(text, errors="coerce")

    if pd.isna(numeric):
        return ""

    if float(numeric).is_integer():
        return int(numeric)

    return float(numeric)


def infer_priority_for_atlas_from_score(score: object, label: object = "") -> int:
    """
    Infer normalized 1-5 atlas priority from available score/label fields.
    """
    label_text = normalize_text(label).lower()

    if "very high" in label_text or label_text == "very_high":
        return 5
    if "high" in label_text:
        return 4
    if "medium" in label_text or "moderate" in label_text:
        return 3
    if "low" in label_text:
        return 2

    numeric = pd.to_numeric(score, errors="coerce")

    if pd.isna(numeric):
        return 3

    if numeric >= 80:
        return 5
    if numeric >= 60:
        return 4
    if numeric >= 40:
        return 3
    if numeric >= 20:
        return 2

    return 1


def infer_gdc_omics_modality(row: pd.Series) -> str:
    """
    Infer coarse GDC omics modality summary from known boolean/count columns.
    """
    modality_tokens = []

    column_text = " ".join([str(column).lower() for column in row.index])

    modality_patterns = [
        ("transcriptomics", ["rna", "transcript", "expression"]),
        ("snv", ["mutation", "maf", "snv", "variant"]),
        ("cnv", ["copy", "cnv", "cna"]),
        ("methylation", ["methyl"]),
        ("proteomics", ["protein", "proteomic", "rppa"]),
        ("clinical_annotation", ["clinical", "phenotype", "biospecimen"]),
        ("imaging", ["image", "imaging"]),
    ]

    for modality, patterns in modality_patterns:
        for pattern in patterns:
            matching_columns = [column for column in row.index if pattern in str(column).lower()]
            for column in matching_columns:
                value = row[column]
                value_text = normalize_text(value).lower()

                if value_text in {"true", "yes", "1"}:
                    modality_tokens.append(modality)
                else:
                    numeric = pd.to_numeric(value, errors="coerce")
                    if not pd.isna(numeric) and numeric > 0:
                        modality_tokens.append(modality)

        if modality in modality_tokens:
            continue

        if any(pattern in column_text for pattern in patterns):
            # Only use this weaker signal if a modality-specific column is present.
            pass

    modality_tokens = sorted(set(modality_tokens))

    if modality_tokens:
        return ";".join(modality_tokens)

    return "project_level_multi_omics_metadata"


def normalize_gdc_inventory(
    gdc_df: pd.DataFrame,
    input_path: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Normalize GDC inventory/ranking rows into unified schema.
    """
    records = []

    for _, row in gdc_df.iterrows():
        project_id = normalize_text(
            coalesce_row_value(
                row,
                [
                    "project_id",
                    "id",
                    "gdc_project_id",
                    "project",
                ],
            )
        )

        project_name = normalize_text(
            coalesce_row_value(
                row,
                [
                    "project_name",
                    "name",
                    "project_title",
                    "program_name",
                    "project_id",
                ],
                default=project_id,
            )
        )

        primary_site = normalize_text(
            coalesce_row_value(
                row,
                [
                    "primary_site",
                    "primary_sites",
                    "site",
                    "tissue",
                ],
            )
        )

        disease_type = normalize_text(
            coalesce_row_value(
                row,
                [
                    "disease_type",
                    "disease_types",
                    "cancer_type",
                    "tumor_type",
                ],
            )
        )

        case_count = to_numeric_or_blank(
            coalesce_row_value(
                row,
                [
                    "case_count",
                    "cases_count",
                    "num_cases",
                    "cases",
                ],
            )
        )

        file_count = to_numeric_or_blank(
            coalesce_row_value(
                row,
                [
                    "file_count",
                    "files_count",
                    "num_files",
                    "files",
                    "total_files",
                ],
            )
        )

        priority_score = to_numeric_or_blank(
            coalesce_row_value(
                row,
                [
                    "priority_score",
                    "score",
                    "atlas_priority_score",
                ],
            )
        )

        priority_label = normalize_text(
            coalesce_row_value(
                row,
                [
                    "priority_label",
                    "priority",
                    "atlas_priority_label",
                ],
            )
        )

        priority_for_atlas = infer_priority_for_atlas_from_score(
            score=priority_score,
            label=priority_label,
        )

        source_url = ""
        if project_id:
            source_url = f"https://portal.gdc.cancer.gov/projects/{project_id}"

        records.append(
            {
                "source_id": "gdc",
                "source_name": "NCI Genomic Data Commons",
                "source_record_type": "gdc_project",
                "record_id": project_id,
                "record_name": project_name,
                "project_id": project_id,
                "dataset_id": "",
                "hub_id": "",
                "cancer_scope": "GDC project/cohort",
                "primary_site": primary_site,
                "disease_type": disease_type,
                "data_category": "GDC project metadata",
                "omics_modality": infer_gdc_omics_modality(row),
                "matrix_type": "project-level metadata",
                "resource_family": normalize_text(
                    coalesce_row_value(row, ["program_name", "program", "resource_family"], default="GDC")
                ),
                "sample_scope": "cases",
                "case_count": case_count,
                "file_count": file_count,
                "priority_for_atlas": priority_for_atlas,
                "priority_score": priority_score,
                "priority_label": priority_label,
                "integration_stage": "unified_inventory",
                "source_url": source_url,
                "notes": f"Normalized from GDC inventory input: {input_path}" if input_path else "Normalized from GDC inventory input.",
            }
        )

    return pd.DataFrame(records)


def normalize_xena_inventory(
    xena_df: pd.DataFrame,
    input_path: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Normalize Xena dataset inventory rows into unified schema.
    """
    records = []

    for _, row in xena_df.iterrows():
        hub_id = normalize_text(coalesce_row_value(row, ["hub_id"]))
        dataset_id = normalize_text(coalesce_row_value(row, ["dataset_id", "dataset_name"]))
        hub_url = normalize_text(coalesce_row_value(row, ["hub_url"]))

        source_url = hub_url
        if hub_url and dataset_id:
            source_url = hub_url.rstrip("/") + "/"

        priority_for_atlas = to_numeric_or_blank(
            coalesce_row_value(row, ["priority_for_atlas"], default=3)
        )

        if priority_for_atlas == "":
            priority_for_atlas = 3

        records.append(
            {
                "source_id": "xena",
                "source_name": "UCSC Xena",
                "source_record_type": "xena_dataset",
                "record_id": dataset_id,
                "record_name": normalize_text(coalesce_row_value(row, ["dataset_label", "dataset_name", "dataset_id"])),
                "project_id": "",
                "dataset_id": dataset_id,
                "hub_id": hub_id,
                "cancer_scope": normalize_text(coalesce_row_value(row, ["cancer_scope"])),
                "primary_site": "",
                "disease_type": "",
                "data_category": normalize_text(coalesce_row_value(row, ["data_category"])),
                "omics_modality": normalize_text(coalesce_row_value(row, ["omics_modality"])),
                "matrix_type": normalize_text(coalesce_row_value(row, ["matrix_type"])),
                "resource_family": normalize_text(coalesce_row_value(row, ["resource_family"])),
                "sample_scope": normalize_text(coalesce_row_value(row, ["sample_scope"])),
                "case_count": "",
                "file_count": "",
                "priority_for_atlas": int(priority_for_atlas),
                "priority_score": "",
                "priority_label": "",
                "integration_stage": "unified_inventory",
                "source_url": source_url,
                "notes": f"Normalized from Xena dataset inventory input: {input_path}" if input_path else "Normalized from Xena dataset inventory input.",
            }
        )

    return pd.DataFrame(records)


def finalize_unified_inventory(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure unified schema, types, sorting, and stable output.
    """
    if df.empty:
        out = pd.DataFrame(columns=UNIFIED_COLUMNS)
    else:
        out = df.copy()

    for column in UNIFIED_COLUMNS:
        if column not in out.columns:
            out[column] = ""

    out = out.loc[:, UNIFIED_COLUMNS].copy()

    if not out.empty:
        out["priority_for_atlas"] = pd.to_numeric(
            out["priority_for_atlas"],
            errors="coerce",
        ).fillna(3).astype(int)

        out = out.sort_values(
            by=[
                "priority_for_atlas",
                "source_id",
                "source_record_type",
                "record_id",
            ],
            ascending=[False, True, True, True],
            kind="stable",
        ).reset_index(drop=True)

    return out


def build_unified_public_cancer_omics_inventory(
    gdc_input: Optional[Path] = None,
    xena_input: Optional[Path] = DEFAULT_XENA_INPUT,
    allow_missing_inputs: bool = True,
) -> pd.DataFrame:
    """
    Build unified public cancer omics inventory from GDC and Xena sources.
    """
    normalized_tables = []
    missing_inputs = []

    resolved_gdc_input = gdc_input

    if resolved_gdc_input is None:
        resolved_gdc_input = first_existing_path(GDC_INPUT_CANDIDATES)

    if resolved_gdc_input is not None and resolved_gdc_input.exists():
        gdc_df = read_tsv_if_exists(resolved_gdc_input)
        normalized_tables.append(
            normalize_gdc_inventory(
                gdc_df=gdc_df,
                input_path=resolved_gdc_input,
            )
        )
    else:
        missing_inputs.append(
            "GDC input not found. Checked default candidates."
            if gdc_input is None
            else f"GDC input not found: {gdc_input}"
        )

    if xena_input is not None and xena_input.exists():
        xena_df = read_tsv_if_exists(xena_input)
        normalized_tables.append(
            normalize_xena_inventory(
                xena_df=xena_df,
                input_path=xena_input,
            )
        )
    else:
        missing_inputs.append(
            "Xena input not found."
            if xena_input is None
            else f"Xena input not found: {xena_input}"
        )

    if missing_inputs and not allow_missing_inputs:
        raise FileNotFoundError(" ; ".join(missing_inputs))

    if not normalized_tables:
        raise FileNotFoundError(
            "No input inventories were found. "
            "Run the GDC and/or Xena metadata pipelines first."
        )

    unified_df = pd.concat(normalized_tables, ignore_index=True)

    return finalize_unified_inventory(unified_df)


def write_unified_public_cancer_omics_inventory(
    output_path: Path = DEFAULT_OUTPUT,
    gdc_input: Optional[Path] = None,
    xena_input: Optional[Path] = DEFAULT_XENA_INPUT,
    allow_missing_inputs: bool = True,
) -> pd.DataFrame:
    """
    Build and write unified public cancer omics inventory.
    """
    unified_df = build_unified_public_cancer_omics_inventory(
        gdc_input=gdc_input,
        xena_input=xena_input,
        allow_missing_inputs=allow_missing_inputs,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    unified_df.to_csv(output_path, sep="\t", index=False)

    return unified_df


def print_unified_inventory_summary(df: pd.DataFrame, output_path: Path) -> None:
    """
    Print a concise inventory summary.
    """
    print("Unified public cancer omics inventory complete.")
    print(f"Rows: {len(df)}")
    print(f"Output: {output_path}")

    if df.empty:
        return

    print("\nRows by source:")
    for source_id, count in df["source_id"].value_counts().items():
        print(f"  {source_id}: {count}")

    print("\nRows by record type:")
    for record_type, count in df["source_record_type"].value_counts().items():
        print(f"  {record_type}: {count}")

    print("\nRows by modality:")
    for modality, count in df["omics_modality"].fillna("").astype(str).value_counts().head(12).items():
        print(f"  {modality}: {count}")


def build_arg_parser() -> argparse.ArgumentParser:
    """
    Build CLI parser.
    """
    parser = argparse.ArgumentParser(
        description="Build unified public cancer omics inventory from GDC and UCSC Xena inputs."
    )

    parser.add_argument(
        "--gdc-input",
        type=Path,
        default=None,
        help=(
            "Optional GDC inventory/ranking TSV. If omitted, known default "
            "GDC output paths are checked."
        ),
    )

    parser.add_argument(
        "--xena-input",
        type=Path,
        default=DEFAULT_XENA_INPUT,
        help=f"Xena dataset inventory TSV. Default: {DEFAULT_XENA_INPUT}",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Unified output TSV. Default: {DEFAULT_OUTPUT}",
    )

    parser.add_argument(
        "--strict-inputs",
        action="store_true",
        help="Fail if either GDC or Xena input is missing.",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    CLI entrypoint.
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        unified_df = write_unified_public_cancer_omics_inventory(
            output_path=args.output,
            gdc_input=args.gdc_input,
            xena_input=args.xena_input,
            allow_missing_inputs=not args.strict_inputs,
        )
    except Exception as exc:
        print(f"ERROR: Failed to build unified public cancer omics inventory: {exc}", file=sys.stderr)
        return 1

    print_unified_inventory_summary(unified_df, args.output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
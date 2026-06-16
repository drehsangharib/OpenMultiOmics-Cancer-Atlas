#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd


DEFAULT_INPUT = Path("outputs/dataset_inventory/unified_public_cancer_omics_inventory.tsv")
DEFAULT_OUTPUT = Path("outputs/atlases/gbm/gbm_public_omics_atlas_inventory.tsv")
DEFAULT_REPORT = Path("outputs/reports/gbm_public_omics_atlas_report.html")

GBM_KEYWORDS = [
    "gbm",
    "glioblastoma",
    "glioma",
    "brain",
    "lgg",
    "tcga-gbm",
    "tcga-lgg",
]

SEARCH_COLUMNS = [
     "record_id",
    "record_name",
    "project_id",
    "dataset_id",
    "primary_site",
    "disease_type",
    "cancer_scope",
    "resource_family"
]

DISPLAY_COLUMNS = [
    "source_id",
    "source_record_type",
    "record_id",
    "record_name",
    "project_id",
    "dataset_id",
    "hub_id",
    "omics_modality",
    "data_category",
    "matrix_type",
    "resource_family",
    "primary_site",
    "disease_type",
    "cancer_scope",
    "priority_for_atlas",
    "source_url",
    "gbm_match_terms",
]


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def read_unified_inventory(input_path: Path = DEFAULT_INPUT) -> pd.DataFrame:
    if not input_path.exists():
        raise FileNotFoundError(
            f"Unified inventory not found: {input_path}. "
            "Run python -m core.pipelines.run_unified_public_omics_qc_pipeline "
            "--refresh-xena --xena-recommended-only --make-report --make-qc-report first."
        )
    return pd.read_csv(input_path, sep="\t")


def collect_match_terms(
    row: pd.Series,
    keywords: Iterable[str] = GBM_KEYWORDS,
) -> List[str]:
    text_parts = []

    for column in SEARCH_COLUMNS:
        if column in row.index:
            text_parts.append(normalize_text(row[column]))

    combined = " ".join(text_parts)

    matches = []
    for keyword in keywords:
        keyword_text = keyword.lower()
        if keyword_text in combined:
            matches.append(keyword_text)

    return sorted(set(matches))


def filter_gbm_relevant_records(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        out = df.copy()
        out["gbm_match_terms"] = ""
        return out

    records = []

    for _, row in df.iterrows():
        match_terms = collect_match_terms(row)
        if match_terms:
            item = row.to_dict()
            item["gbm_match_terms"] = ";".join(match_terms)
            records.append(item)

    if not records:
        return pd.DataFrame(columns=list(df.columns) + ["gbm_match_terms"])

    out = pd.DataFrame(records)

    if "priority_for_atlas" in out.columns:
        out["priority_for_atlas"] = pd.to_numeric(
            out["priority_for_atlas"],
            errors="coerce",
        ).fillna(3).astype(int)
    else:
        out["priority_for_atlas"] = 3

    sort_columns = [
        "priority_for_atlas",
        "source_id",
        "source_record_type",
        "omics_modality",
        "record_id",
    ]
    existing_sort_columns = [column for column in sort_columns if column in out.columns]

    if existing_sort_columns:
        ascending = [
            False if column == "priority_for_atlas" else True
            for column in existing_sort_columns
        ]
        out = out.sort_values(
            by=existing_sort_columns,
            ascending=ascending,
            kind="stable",
        ).reset_index(drop=True)

    return out


def value_counts_table(
    df: pd.DataFrame,
    column: str,
    max_rows: Optional[int] = None,
) -> pd.DataFrame:
    if df.empty or column not in df.columns:
        return pd.DataFrame(columns=[column, "count"])

    counts = (
        df[column]
        .fillna("")
        .astype(str)
        .value_counts()
        .rename_axis(column)
        .reset_index(name="count")
    )

    if max_rows is not None:
        counts = counts.head(max_rows)

    return counts


def escape_html(value: object) -> str:
    if value is None:
        return ""
    return html.escape(str(value))


def dataframe_to_html_table(df: pd.DataFrame, max_rows: Optional[int] = None) -> str:
    if df.empty:
        return "<p>No records available.</p>"

    out = df.copy()
    if max_rows is not None:
        out = out.head(max_rows)

    lines = ["<table border='1' cellspacing='0' cellpadding='5'>"]
    lines.append("<thead><tr>")

    for column in out.columns:
        lines.append(f"<th>{escape_html(column)}</th>")

    lines.append("</tr></thead>")
    lines.append("<tbody>")

    for _, row in out.iterrows():
        lines.append("<tr>")
        for column in out.columns:
            lines.append(f"<td>{escape_html(row[column])}</td>")
        lines.append("</tr>")

    lines.append("</tbody></table>")
    return "\n".join(lines)


def select_display_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=DISPLAY_COLUMNS)

    out = df.copy()
    for column in DISPLAY_COLUMNS:
        if column not in out.columns:
            out[column] = ""

    return out.loc[:, DISPLAY_COLUMNS]


def build_gbm_public_omics_atlas_report_html(
    gbm_df: pd.DataFrame,
    title: str = "GBM Public Omics Atlas Inventory Report",
) -> str:
    total_rows = int(len(gbm_df))

    source_count = int(gbm_df["source_id"].nunique()) if "source_id" in gbm_df.columns and not gbm_df.empty else 0
    record_type_count = int(gbm_df["source_record_type"].nunique()) if "source_record_type" in gbm_df.columns and not gbm_df.empty else 0
    modality_count = int(gbm_df["omics_modality"].nunique()) if "omics_modality" in gbm_df.columns and not gbm_df.empty else 0

    source_counts = value_counts_table(gbm_df, "source_id")
    record_type_counts = value_counts_table(gbm_df, "source_record_type")
    modality_counts = value_counts_table(gbm_df, "omics_modality")
    data_category_counts = value_counts_table(gbm_df, "data_category", max_rows=30)
    match_term_counts = value_counts_table(gbm_df, "gbm_match_terms", max_rows=30)
    examples = select_display_columns(gbm_df)

    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        f"<title>{escape_html(title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This report summarizes GBM / brain / glioma relevant public omics records derived from the unified inventory.</p>",
        "<p><strong>Scope:</strong> This is a metadata-only atlas slice. Molecular matrices are not downloaded.</p>",
        "<h2>Summary</h2>",
        "<ul>",
        f"<li>GBM-relevant records: {total_rows}</li>",
        f"<li>Sources: {source_count}</li>",
        f"<li>Record types: {record_type_count}</li>",
        f"<li>Modalities: {modality_count}</li>",
        "</ul>",
        "<h2>Rows by source</h2>",
        dataframe_to_html_table(source_counts),
        "<h2>Rows by record type</h2>",
        dataframe_to_html_table(record_type_counts),
        "<h2>Rows by omics modality</h2>",
        dataframe_to_html_table(modality_counts),
        "<h2>Rows by data category</h2>",
        dataframe_to_html_table(data_category_counts),
        "<h2>Rows by GBM match terms</h2>",
        dataframe_to_html_table(match_term_counts),
        "<h2>GBM atlas inventory examples</h2>",
        dataframe_to_html_table(examples, max_rows=150),
        "<p>Generated by OpenMultiOmics-Cancer-Atlas GBM public omics atlas module.</p>",
        "</body>",
        "</html>",
    ]

    return "\n".join(html_parts)


def build_gbm_public_omics_atlas(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
    report_path: Path = DEFAULT_REPORT,
    make_report: bool = True,
    report_title: str = "GBM Public Omics Atlas Inventory Report",
) -> pd.DataFrame:
    unified_df = read_unified_inventory(input_path)
    gbm_df = filter_gbm_relevant_records(unified_df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    gbm_df.to_csv(output_path, sep="\t", index=False)

    if make_report:
        report_html = build_gbm_public_omics_atlas_report_html(
            gbm_df,
            title=report_title,
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_html, encoding="utf-8")

    return gbm_df


def print_summary(
    df: pd.DataFrame,
    output_path: Path,
    report_path: Path,
    make_report: bool,
) -> None:
    print("GBM public omics atlas slice complete.")
    print(f"Rows: {len(df)}")
    print(f"Output: {output_path}")

    if make_report:
        print(f"Report: {report_path}")

    if not df.empty and "source_id" in df.columns:
        print("\nRows by source:")
        for name, count in df["source_id"].fillna("").astype(str).value_counts().items():
            print(f"  {name}: {count}")

    if not df.empty and "omics_modality" in df.columns:
        print("\nRows by modality:")
        modality_counts = df["omics_modality"].fillna("").astype(str).value_counts().head(12)
        for name, count in modality_counts.items():
            print(f"  {name}: {count}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build GBM / brain / glioma public omics atlas slice from unified inventory."
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input unified inventory TSV. Default: {DEFAULT_INPUT}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output GBM atlas inventory TSV. Default: {DEFAULT_OUTPUT}",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"Output GBM atlas HTML report. Default: {DEFAULT_REPORT}",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Disable GBM atlas HTML report generation.",
    )
    parser.add_argument(
        "--report-title",
        default="GBM Public Omics Atlas Inventory Report",
        help="HTML report title.",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        gbm_df = build_gbm_public_omics_atlas(
            input_path=args.input,
            output_path=args.output,
            report_path=args.report,
            make_report=not args.no_report,
            report_title=args.report_title,
        )
    except Exception as exc:
        print(f"ERROR: Failed to build GBM public omics atlas slice: {exc}", file=sys.stderr)
        return 1

    print_summary(
        df=gbm_df,
        output_path=args.output,
        report_path=args.report,
        make_report=not args.no_report,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
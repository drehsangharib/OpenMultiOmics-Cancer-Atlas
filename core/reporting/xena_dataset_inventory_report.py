#!/usr/bin/env python3

"""
UCSC Xena Dataset Inventory Report

Project:
    OpenMultiOmics-Cancer-Atlas

Purpose:
    Generate a readable HTML report from the metadata-only UCSC Xena dataset
    inventory.

Input:
    outputs/dataset_inventory/xena_dataset_inventory.tsv

Output:
    outputs/reports/xena_dataset_inventory_report.html

Example:
    python -m core.reporting.xena_dataset_inventory_report
"""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd


DEFAULT_INPUT = Path("outputs/dataset_inventory/xena_dataset_inventory.tsv")
DEFAULT_OUTPUT = Path("outputs/reports/xena_dataset_inventory_report.html")


REPORT_COLUMNS = [
    "hub_id",
    "hub_name",
    "dataset_id",
    "dataset_label",
    "data_category",
    "omics_modality",
    "matrix_type",
    "resource_family",
    "cancer_scope",
    "sample_scope",
    "priority_for_atlas",
    "integration_stage",
    "notes",
]


def read_xena_dataset_inventory(input_path: Path = DEFAULT_INPUT) -> pd.DataFrame:
    """
    Read Xena dataset inventory TSV.
    """
    if not input_path.exists():
        raise FileNotFoundError(
            f"Xena dataset inventory not found: {input_path}. "
            "Run python -m core.pipelines.run_xena_metadata_pipeline --recommended-only first."
        )

    df = pd.read_csv(input_path, sep="\t")

    for column in REPORT_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    return df


def escape_html(value: object) -> str:
    """
    HTML-escape a value.
    """
    if value is None:
        return ""
    return html.escape(str(value))


def value_counts_table(
    df: pd.DataFrame,
    column: str,
    max_rows: Optional[int] = None,
) -> pd.DataFrame:
    """
    Build value-count table for a column.
    """
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


def dataframe_to_html_table(
    df: pd.DataFrame,
    max_rows: Optional[int] = None,
    css_class: str = "data-table",
) -> str:
    """
    Convert DataFrame to a small escaped HTML table.
    """
    if df.empty:
        return '<p class="empty-note">No records available.</p>'

    out = df.copy()

    if max_rows is not None:
        out = out.head(max_rows)

    columns = list(out.columns)

    lines = [f'<table class="{css_class}">']
    lines.append("<thead><tr>")
    for column in columns:
        lines.append(f"<th>{escape_html(column)}</th>")
    lines.append("</tr></thead>")
    lines.append("<tbody>")

    for _, row in out.iterrows():
        lines.append("<tr>")
        for column in columns:
            lines.append(f"<td>{escape_html(row[column])}</td>")
        lines.append("</tr>")

    lines.append("</tbody></table>")

    return "\n".join(lines)


def build_unknown_review_table(
    df: pd.DataFrame,
    max_rows: int = 100,
) -> pd.DataFrame:
    """
    Build review table for unknown classifications.
    """
    if df.empty or "omics_modality" not in df.columns:
        return pd.DataFrame(columns=["hub_id", "dataset_id", "dataset_label", "data_category", "notes"])

    unknown_df = df[df["omics_modality"].fillna("").astype(str) == "unknown"].copy()

    columns = [
        "hub_id",
        "dataset_id",
        "dataset_label",
        "data_category",
        "matrix_type",
        "resource_family",
        "cancer_scope",
    ]

    columns = [column for column in columns if column in unknown_df.columns]

    if unknown_df.empty:
        return pd.DataFrame(columns=columns)

    return unknown_df.loc[:, columns].head(max_rows).reset_index(drop=True)


def build_top_priority_table(
    df: pd.DataFrame,
    max_rows: int = 50,
) -> pd.DataFrame:
    """
    Build table of high-priority datasets.
    """
    if df.empty:
        return pd.DataFrame(columns=REPORT_COLUMNS)

    out = df.copy()

    if "priority_for_atlas" in out.columns:
        out["priority_for_atlas"] = pd.to_numeric(
            out["priority_for_atlas"],
            errors="coerce",
        ).fillna(0)
        out = out.sort_values(
            by=["priority_for_atlas", "hub_id", "omics_modality", "dataset_id"],
            ascending=[False, True, True, True],
            kind="stable",
        )

    columns = [
        "hub_id",
        "dataset_id",
        "data_category",
        "omics_modality",
        "matrix_type",
        "resource_family",
        "cancer_scope",
        "priority_for_atlas",
    ]

    columns = [column for column in columns if column in out.columns]

    return out.loc[:, columns].head(max_rows).reset_index(drop=True)


def build_examples_by_hub_and_modality(
    df: pd.DataFrame,
    max_examples_per_group: int = 3,
) -> pd.DataFrame:
    """
    Build example dataset table grouped by hub and modality.
    """
    if df.empty:
        return pd.DataFrame(columns=["hub_id", "omics_modality", "example_dataset_id"])

    required = {"hub_id", "omics_modality", "dataset_id"}
    if not required.issubset(set(df.columns)):
        return pd.DataFrame(columns=["hub_id", "omics_modality", "example_dataset_id"])

    rows = []

    grouped = df.groupby(["hub_id", "omics_modality"], dropna=False)

    for (hub_id, modality), group in grouped:
        examples = (
            group["dataset_id"]
            .fillna("")
            .astype(str)
            .drop_duplicates()
            .head(max_examples_per_group)
            .tolist()
        )

        for example in examples:
            rows.append(
                {
                    "hub_id": hub_id,
                    "omics_modality": modality,
                    "example_dataset_id": example,
                }
            )

    return pd.DataFrame(rows)


def build_report_css() -> str:
    """
    Build CSS for report.
    """
    return """
body {
    font-family: Arial, Helvetica, sans-serif;
    margin: 32px;
    color: #222;
    background: #fff;
}
h1, h2, h3 {
    color: #17324d;
}
.summary-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(140px, 1fr));
    gap: 12px;
    margin: 20px 0;
}
.metric-card {
    border: 1px solid #d9e2ec;
    border-radius: 8px;
    padding: 14px;
    background: #f8fbff;
}
.metric-value {
    font-size: 26px;
    font-weight: bold;
    color: #0b5cab;
}
.metric-label {
    font-size: 13px;
    color: #556;
}
.data-table {
    border-collapse: collapse;
    width: 100%;
    margin: 12px 0 28px 0;
    font-size: 13px;
}
.data-table th {
    background: #17324d;
    color: white;
    text-align: left;
    padding: 8px;
    border: 1px solid #d0d7de;
}
.data-table td {
    padding: 7px;
    border: 1px solid #d0d7de;
    vertical-align: top;
}
.data-table tr:nth-child(even) {
    background: #f6f8fa;
}
.note {
    background: #fff8e1;
    border-left: 4px solid #f2c94c;
    padding: 10px 12px;
    margin: 12px 0 24px 0;
}
.empty-note {
    color: #666;
    font-style: italic;
}
.footer {
    margin-top: 40px;
    color: #666;
    font-size: 12px;
}
"""


def build_xena_dataset_inventory_report_html(
    inventory_df: pd.DataFrame,
    title: str = "UCSC Xena Dataset Inventory Report",
) -> str:
    """
    Build full HTML report from Xena dataset inventory.
    """
    df = inventory_df.copy()

    total_rows = int(len(df))
    hub_count = int(df["hub_id"].nunique()) if "hub_id" in df.columns and not df.empty else 0

    query_error_rows = 0
    if "integration_stage" in df.columns:
        query_error_rows = int((df["integration_stage"] == "query_error").sum())

    unknown_rows = 0
    if "omics_modality" in df.columns:
        unknown_rows = int((df["omics_modality"] == "unknown").sum())

    modality_count = int(df["omics_modality"].nunique()) if "omics_modality" in df.columns and not df.empty else 0

    hub_counts = value_counts_table(df, "hub_id")
    modality_counts = value_counts_table(df, "omics_modality")
    category_counts = value_counts_table(df, "data_category")
    stage_counts = value_counts_table(df, "integration_stage")
    top_priority = build_top_priority_table(df)
    unknown_review = build_unknown_review_table(df)
    examples = build_examples_by_hub_and_modality(df)

    html_lines = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        '<meta charset="utf-8">',
        f"<title>{escape_html(title)}</title>",
        "<style>",
        build_report_css(),
        "</style>",
        "</head>",
        "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This report summarizes the metadata-only UCSC Xena dataset inventory generated by OpenMultiOmics-Cancer-Atlas.</p>",
        '<div class="note"><strong>Scope:</strong> This report inventories dataset metadata only. No molecular matrices are downloaded.</div>',
        '<div class="summary-grid">',
        f'<div class="metric-card"><div class="metric-value">{total_rows}</div><div class="metric-label">Dataset rows</div></div>',
        f'<div class="metric-card"><div class="metric-value">{hub_count}</div><div class="metric-label">Hubs represented</div></div>',
        f'<div class="metric-card"><div class="metric-value">{modality_count}</div><div class="metric-label">Modalities represented</div></div>',
        f'<div class="metric-card"><div class="metric-value">{query_error_rows}</div><div class="metric-label">Query-error rows</div></div>',
        "</div>",
        f"<p><strong>Unknown modality rows:</strong> {unknown_rows}</p>",
        "<h2>Dataset counts by hub</h2>",
        dataframe_to_html_table(hub_counts),
        "<h2>Dataset counts by omics modality</h2>",
        dataframe_to_html_table(modality_counts),
        "<h2>Dataset counts by data category</h2>",
        dataframe_to_html_table(category_counts),
        "<h2>Inventory integration-stage counts</h2>",
        dataframe_to_html_table(stage_counts),
        "<h2>Top high-priority datasets</h2>",
        dataframe_to_html_table(top_priority, max_rows=50),
        "<h2>Example datasets by hub and modality</h2>",
        dataframe_to_html_table(examples, max_rows=120),
        "<h2>Unknown-classification review list</h2>",
        '<div class="note">These rows are candidates for future classification-rule improvements.</div>',
        dataframe_to_html_table(unknown_review, max_rows=100),
        '<div class="footer">Generated by OpenMultiOmics-Cancer-Atlas Xena dataset inventory report module.</div>',
        "</body>",
        "</html>",
    ]

    return "\n".join(html_lines)


def generate_xena_dataset_inventory_report(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
    title: str = "UCSC Xena Dataset Inventory Report",
) -> str:
    """
    Generate Xena dataset inventory HTML report and return HTML string.
    """
    inventory_df = read_xena_dataset_inventory(input_path)
    html_text = build_xena_dataset_inventory_report_html(
        inventory_df=inventory_df,
        title=title,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_text, encoding="utf-8")

    return html_text


def build_arg_parser() -> argparse.ArgumentParser:
    """
    Build CLI parser.
    """
    parser = argparse.ArgumentParser(
        description="Generate HTML report for UCSC Xena dataset inventory."
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input Xena dataset inventory TSV. Default: {DEFAULT_INPUT}",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output HTML report. Default: {DEFAULT_OUTPUT}",
    )

    parser.add_argument(
        "--title",
        default="UCSC Xena Dataset Inventory Report",
        help="HTML report title.",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    CLI entrypoint.
    """
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        html_text = generate_xena_dataset_inventory_report(
            input_path=args.input,
            output_path=args.output,
            title=args.title,
        )
    except Exception as exc:
        print(f"ERROR: Failed to generate Xena dataset inventory report: {exc}", file=sys.stderr)
        return 1

    print("Xena dataset inventory report complete.")
    print(f"HTML characters: {len(html_text)}")
    print(f"Output: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
#!/usr/bin/env python3

"""
Unified Public Cancer Omics Inventory Report

Project:
    OpenMultiOmics-Cancer-Atlas

Purpose:
    Generate a readable HTML report from the unified public cancer omics
    inventory built from GDC and UCSC Xena metadata outputs.

Input:
    outputs/dataset_inventory/unified_public_cancer_omics_inventory.tsv

Output:
    outputs/reports/unified_public_cancer_omics_inventory_report.html

Example:
    python -m core.reporting.unified_public_cancer_omics_inventory_report
"""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path
from typing import List, Optional

import pandas as pd


DEFAULT_INPUT = Path("outputs/dataset_inventory/unified_public_cancer_omics_inventory.tsv")
DEFAULT_OUTPUT = Path("outputs/reports/unified_public_cancer_omics_inventory_report.html")


REPORT_COLUMNS = [
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


def read_unified_inventory(input_path: Path = DEFAULT_INPUT) -> pd.DataFrame:
    """
    Read unified public cancer omics inventory TSV.
    """
    if not input_path.exists():
        raise FileNotFoundError(
            f"Unified inventory not found: {input_path}. "
            "Run python -m core.integration.unified_public_cancer_omics_inventory first."
        )

    df = pd.read_csv(input_path, sep="\t")

    for column in REPORT_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    return df.loc[:, REPORT_COLUMNS].copy()


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
    Build value-count table for one column.
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
    Convert DataFrame to escaped HTML table.
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


def build_high_priority_table(
    df: pd.DataFrame,
    max_rows: int = 80,
) -> pd.DataFrame:
    """
    Build high-priority records table.
    """
    if df.empty:
        return pd.DataFrame(columns=REPORT_COLUMNS)

    out = df.copy()

    out["priority_for_atlas"] = pd.to_numeric(
        out["priority_for_atlas"],
        errors="coerce",
    ).fillna(0)

    out = out.sort_values(
        by=[
            "priority_for_atlas",
            "source_id",
            "source_record_type",
            "omics_modality",
            "record_id",
        ],
        ascending=[False, True, True, True, True],
        kind="stable",
    )

    columns = [
        "source_id",
        "source_record_type",
        "record_id",
        "record_name",
        "omics_modality",
        "data_category",
        "cancer_scope",
        "primary_site",
        "priority_for_atlas",
    ]

    columns = [column for column in columns if column in out.columns]

    return out.loc[:, columns].head(max_rows).reset_index(drop=True)


def build_unknown_modality_table(
    df: pd.DataFrame,
    max_rows: int = 120,
) -> pd.DataFrame:
    """
    Build unknown-modality review table.
    """
    if df.empty or "omics_modality" not in df.columns:
        return pd.DataFrame()

    out = df[df["omics_modality"].fillna("").astype(str) == "unknown"].copy()

    columns = [
        "source_id",
        "source_record_type",
        "record_id",
        "record_name",
        "data_category",
        "matrix_type",
        "resource_family",
        "cancer_scope",
    ]

    columns = [column for column in columns if column in out.columns]

    return out.loc[:, columns].head(max_rows).reset_index(drop=True)


def build_gdc_project_examples(
    df: pd.DataFrame,
    max_rows: int = 60,
) -> pd.DataFrame:
    """
    Build GDC project examples table.
    """
    if df.empty:
        return pd.DataFrame()

    out = df[df["source_record_type"].fillna("").astype(str) == "gdc_project"].copy()

    columns = [
        "project_id",
        "record_name",
        "primary_site",
        "disease_type",
        "omics_modality",
        "case_count",
        "file_count",
        "priority_for_atlas",
        "priority_score",
        "priority_label",
    ]

    columns = [column for column in columns if column in out.columns]

    return out.loc[:, columns].head(max_rows).reset_index(drop=True)


def build_xena_dataset_examples(
    df: pd.DataFrame,
    max_rows: int = 80,
) -> pd.DataFrame:
    """
    Build Xena dataset examples table.
    """
    if df.empty:
        return pd.DataFrame()

    out = df[df["source_record_type"].fillna("").astype(str) == "xena_dataset"].copy()

    columns = [
        "hub_id",
        "dataset_id",
        "record_name",
        "omics_modality",
        "data_category",
        "matrix_type",
        "resource_family",
        "cancer_scope",
        "priority_for_atlas",
    ]

    columns = [column for column in columns if column in out.columns]

    return out.loc[:, columns].head(max_rows).reset_index(drop=True)


def build_brain_gbm_relevant_table(
    df: pd.DataFrame,
    max_rows: int = 120,
) -> pd.DataFrame:
    """
    Build table of Brain/GBM/LGG-relevant unified records.
    """
    if df.empty:
        return pd.DataFrame()

    text_columns = [
        "record_id",
        "record_name",
        "project_id",
        "dataset_id",
        "primary_site",
        "disease_type",
        "cancer_scope",
        "resource_family",
        "notes",
    ]

    available = [column for column in text_columns if column in df.columns]

    if not available:
        return pd.DataFrame()

    combined = df[available].fillna("").astype(str).agg(" ".join, axis=1).str.lower()

    mask = (
        combined.str.contains("brain", regex=False)
        | combined.str.contains("gbm", regex=False)
        | combined.str.contains("lgg", regex=False)
        | combined.str.contains("glioma", regex=False)
        | combined.str.contains("glioblastoma", regex=False)
    )

    out = df[mask].copy()

    columns = [
        "source_id",
        "source_record_type",
        "record_id",
        "record_name",
        "omics_modality",
        "data_category",
        "primary_site",
        "disease_type",
        "cancer_scope",
        "priority_for_atlas",
    ]

    columns = [column for column in columns if column in out.columns]

    return out.loc[:, columns].head(max_rows).reset_index(drop=True)


def build_examples_by_source_and_modality(
    df: pd.DataFrame,
    max_examples_per_group: int = 3,
) -> pd.DataFrame:
    """
    Build selected example records grouped by source and modality.
    """
    required = {"source_id", "omics_modality", "record_id"}

    if df.empty or not required.issubset(set(df.columns)):
        return pd.DataFrame(columns=["source_id", "omics_modality", "example_record_id"])

    rows = []

    grouped = df.groupby(["source_id", "omics_modality"], dropna=False)

    for (source_id, modality), group in grouped:
        examples = (
            group["record_id"]
            .fillna("")
            .astype(str)
            .drop_duplicates()
            .head(max_examples_per_group)
            .tolist()
        )

        for example in examples:
            rows.append(
                {
                    "source_id": source_id,
                    "omics_modality": modality,
                    "example_record_id": example,
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
    grid-template-columns: repeat(5, minmax(140px, 1fr));
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


def build_unified_inventory_report_html(
    inventory_df: pd.DataFrame,
    title: str = "Unified Public Cancer Omics Inventory Report",
) -> str:
    """
    Build full HTML report from unified public cancer omics inventory.
    """
    df = inventory_df.copy()

    total_rows = int(len(df))
    source_count = int(df["source_id"].nunique()) if "source_id" in df.columns and not df.empty else 0
    record_type_count = int(df["source_record_type"].nunique()) if "source_record_type" in df.columns and not df.empty else 0
    modality_count = int(df["omics_modality"].nunique()) if "omics_modality" in df.columns and not df.empty else 0

    unknown_rows = 0
    if "omics_modality" in df.columns:
        unknown_rows = int((df["omics_modality"] == "unknown").sum())

    source_counts = value_counts_table(df, "source_id")
    record_type_counts = value_counts_table(df, "source_record_type")
    modality_counts = value_counts_table(df, "omics_modality")
    category_counts = value_counts_table(df, "data_category")
    cancer_scope_counts = value_counts_table(df, "cancer_scope", max_rows=30)

    high_priority = build_high_priority_table(df)
    unknown_review = build_unknown_modality_table(df)
    gdc_examples = build_gdc_project_examples(df)
    xena_examples = build_xena_dataset_examples(df)
    brain_gbm = build_brain_gbm_relevant_table(df)
    examples = build_examples_by_source_and_modality(df)

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
        "<p>This report summarizes the unified public cancer omics inventory generated by OpenMultiOmics-Cancer-Atlas.</p>",
        '<div class="note"><strong>Scope:</strong> This is a metadata-only report combining public GDC project-level records and UCSC Xena dataset-level records. Molecular matrices are not downloaded.</div>',
        '<div class="summary-grid">',
        f'<div class="metric-card"><div class="metric-value">{total_rows}</div><div class="metric-label">Unified records</div></div>',
        f'<div class="metric-card"><div class="metric-value">{source_count}</div><div class="metric-label">Sources</div></div>',
        f'<div class="metric-card"><div class="metric-value">{record_type_count}</div><div class="metric-label">Record types</div></div>',
        f'<div class="metric-card"><div class="metric-value">{modality_count}</div><div class="metric-label">Modalities</div></div>',
        f'<div class="metric-card"><div class="metric-value">{unknown_rows}</div><div class="metric-label">Unknown modality rows</div></div>',
        "</div>",
        "<h2>Rows by source</h2>",
        dataframe_to_html_table(source_counts),
        "<h2>Rows by record type</h2>",
        dataframe_to_html_table(record_type_counts),
        "<h2>Rows by omics modality</h2>",
        dataframe_to_html_table(modality_counts),
        "<h2>Rows by data category</h2>",
        dataframe_to_html_table(category_counts),
        "<h2>Rows by cancer scope</h2>",
        dataframe_to_html_table(cancer_scope_counts),
        "<h2>High-priority unified records</h2>",
        dataframe_to_html_table(high_priority, max_rows=80),
        "<h2>GDC project examples</h2>",
        dataframe_to_html_table(gdc_examples, max_rows=60),
        "<h2>Xena dataset examples</h2>",
        dataframe_to_html_table(xena_examples, max_rows=80),
        "<h2>Brain / GBM / LGG relevant records</h2>",
        dataframe_to_html_table(brain_gbm, max_rows=120),
        "<h2>Example records by source and modality</h2>",
        dataframe_to_html_table(examples, max_rows=120),
        "<h2>Unknown-modality review list</h2>",
        '<div class="note">These rows are candidates for future modality-classification improvements.</div>',
        dataframe_to_html_table(unknown_review, max_rows=120),
        '<div class="footer">Generated by OpenMultiOmics-Cancer-Atlas unified inventory report module.</div>',
        "</body>",
        "</html>",
    ]

    return "\n".join(html_lines)


def generate_unified_public_cancer_omics_inventory_report(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
    title: str = "Unified Public Cancer Omics Inventory Report",
) -> str:
    """
    Generate unified inventory HTML report and return HTML string.
    """
    inventory_df = read_unified_inventory(input_path)
    html_text = build_unified_inventory_report_html(
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
        description="Generate HTML report for unified public cancer omics inventory."
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
        help=f"Output HTML report. Default: {DEFAULT_OUTPUT}",
    )

    parser.add_argument(
        "--title",
        default="Unified Public Cancer Omics Inventory Report",
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
        html_text = generate_unified_public_cancer_omics_inventory_report(
            input_path=args.input,
            output_path=args.output,
            title=args.title,
        )
    except Exception as exc:
        print(f"ERROR: Failed to generate unified inventory report: {exc}", file=sys.stderr)
        return 1

    print("Unified public cancer omics inventory report complete.")
    print(f"HTML characters: {len(html_text)}")
    print(f"Output: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
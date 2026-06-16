#!/usr/bin/env python3

"""
Unified Public Cancer Omics Inventory QC Report

Project:
    OpenMultiOmics-Cancer-Atlas

Purpose:
    Generate quality-control summaries for the unified public cancer omics
    inventory.

Input:
    outputs/dataset_inventory/unified_public_cancer_omics_inventory.tsv

Output:
    outputs/reports/unified_public_cancer_omics_qc_report.html

Example:
    python -m core.reporting.unified_public_cancer_omics_qc_report
"""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path
from typing import List, Optional

import pandas as pd


DEFAULT_INPUT = Path("outputs/dataset_inventory/unified_public_cancer_omics_inventory.tsv")
DEFAULT_OUTPUT = Path("outputs/reports/unified_public_cancer_omics_qc_report.html")


REQUIRED_COLUMNS = [
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
    Read unified inventory TSV and guarantee required columns.
    """
    if not input_path.exists():
        raise FileNotFoundError(
            f"Unified inventory not found: {input_path}. "
            "Run python -m core.pipelines.run_unified_public_omics_pipeline --make-report first."
        )

    df = pd.read_csv(input_path, sep="\t")

    for column in REQUIRED_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    return df.loc[:, REQUIRED_COLUMNS].copy()


def escape_html(value: object) -> str:
    """
    Escape a value for HTML rendering.
    """
    if value is None:
        return ""
    return html.escape(str(value))


def dataframe_to_html_table(
    df: pd.DataFrame,
    max_rows: Optional[int] = None,
    css_class: str = "data-table",
) -> str:
    """
    Convert a DataFrame to escaped HTML table.
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


def value_counts_table(df: pd.DataFrame, column: str, max_rows: Optional[int] = None) -> pd.DataFrame:
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


def build_qc_metric_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build top-level QC metric table.
    """
    total_rows = int(len(df))

    def count_missing(column: str) -> int:
        if column not in df.columns:
            return total_rows
        return int((df[column].fillna("").astype(str).str.strip() == "").sum())

    unknown_modality_rows = 0
    if "omics_modality" in df.columns:
        unknown_modality_rows = int((df["omics_modality"].fillna("").astype(str) == "unknown").sum())

    duplicate_record_rows = 0
    if "source_id" in df.columns and "record_id" in df.columns:
        duplicate_record_rows = int(df.duplicated(subset=["source_id", "record_id"], keep=False).sum())

    metrics = [
        {"metric": "total_rows", "value": total_rows},
        {"metric": "source_count", "value": int(df["source_id"].nunique()) if "source_id" in df.columns else 0},
        {
            "metric": "record_type_count",
            "value": int(df["source_record_type"].nunique()) if "source_record_type" in df.columns else 0,
        },
        {"metric": "unknown_modality_rows", "value": unknown_modality_rows},
        {"metric": "duplicate_source_record_id_rows", "value": duplicate_record_rows},
        {"metric": "missing_record_id_rows", "value": count_missing("record_id")},
        {"metric": "missing_omics_modality_rows", "value": count_missing("omics_modality")},
        {"metric": "missing_data_category_rows", "value": count_missing("data_category")},
        {"metric": "missing_priority_for_atlas_rows", "value": count_missing("priority_for_atlas")},
        {"metric": "missing_source_url_rows", "value": count_missing("source_url")},
    ]

    return pd.DataFrame(metrics)


def build_missingness_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build missingness summary for required columns.
    """
    rows = []
    total_rows = int(len(df))

    for column in REQUIRED_COLUMNS:
        if column not in df.columns:
            missing = total_rows
        else:
            missing = int((df[column].fillna("").astype(str).str.strip() == "").sum())

        percent = 0.0
        if total_rows > 0:
            percent = round(100.0 * missing / total_rows, 2)

        rows.append(
            {
                "column": column,
                "missing_rows": missing,
                "missing_percent": percent,
            }
        )

    return pd.DataFrame(rows)


def build_unknown_modality_table(df: pd.DataFrame, max_rows: int = 150) -> pd.DataFrame:
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
        "source_url",
    ]

    columns = [column for column in columns if column in out.columns]

    return out.loc[:, columns].head(max_rows).reset_index(drop=True)


def build_duplicate_record_table(df: pd.DataFrame, max_rows: int = 150) -> pd.DataFrame:
    """
    Build duplicate source_id + record_id review table.
    """
    if df.empty or not {"source_id", "record_id"}.issubset(set(df.columns)):
        return pd.DataFrame()

    out = df[df.duplicated(subset=["source_id", "record_id"], keep=False)].copy()

    columns = [
        "source_id",
        "source_record_type",
        "record_id",
        "record_name",
        "omics_modality",
        "data_category",
        "priority_for_atlas",
    ]

    columns = [column for column in columns if column in out.columns]

    return out.loc[:, columns].head(max_rows).reset_index(drop=True)


def build_missing_source_url_table(df: pd.DataFrame, max_rows: int = 150) -> pd.DataFrame:
    """
    Build missing source URL review table.
    """
    if df.empty or "source_url" not in df.columns:
        return pd.DataFrame()

    mask = df["source_url"].fillna("").astype(str).str.strip() == ""
    out = df[mask].copy()

    columns = [
        "source_id",
        "source_record_type",
        "record_id",
        "record_name",
        "omics_modality",
        "data_category",
        "cancer_scope",
    ]

    columns = [column for column in columns if column in out.columns]

    return out.loc[:, columns].head(max_rows).reset_index(drop=True)


def build_brain_gbm_relevant_table(df: pd.DataFrame, max_rows: int = 150) -> pd.DataFrame:
    """
    Build Brain/GBM/LGG/glioma-relevant record table.
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


def build_report_css() -> str:
    """
    Report CSS.
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


def build_qc_report_html(
    inventory_df: pd.DataFrame,
    title: str = "Unified Public Cancer Omics Inventory QC Report",
) -> str:
    """
    Build HTML QC report.
    """
    df = inventory_df.copy()

    metrics = build_qc_metric_table(df)
    missingness = build_missingness_table(df)
    source_counts = value_counts_table(df, "source_id")
    record_type_counts = value_counts_table(df, "source_record_type")
    modality_counts = value_counts_table(df, "omics_modality")
    category_counts = value_counts_table(df, "data_category", max_rows=30)

    unknown_modality = build_unknown_modality_table(df)
    duplicates = build_duplicate_record_table(df)
    missing_urls = build_missing_source_url_table(df)
    brain_gbm = build_brain_gbm_relevant_table(df)

    metric_lookup = dict(zip(metrics["metric"], metrics["value"]))

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
        "<p>This report summarizes quality-control checks for the unified public cancer omics inventory.</p>",
        '<div class="note"><strong>Scope:</strong> This is a metadata-only QC report. Molecular matrices are not downloaded.</div>',
        '<div class="summary-grid">',
        f'<div class="metric-card"><div class="metric-value">{metric_lookup.get("total_rows", 0)}</div><div class="metric-label">Total records</div></div>',
        f'<div class="metric-card"><div class="metric-value">{metric_lookup.get("unknown_modality_rows", 0)}</div><div class="metric-label">Unknown modality rows</div></div>',
        f'<div class="metric-card"><div class="metric-value">{metric_lookup.get("duplicate_source_record_id_rows", 0)}</div><div class="metric-label">Duplicate source+record rows</div></div>',
        f'<div class="metric-card"><div class="metric-value">{metric_lookup.get("missing_source_url_rows", 0)}</div><div class="metric-label">Missing source URLs</div></div>',
        f'<div class="metric-card"><div class="metric-value">{metric_lookup.get("source_count", 0)}</div><div class="metric-label">Sources</div></div>',
        "</div>",
        "<h2>QC metrics</h2>",
        dataframe_to_html_table(metrics),
        "<h2>Required-column missingness</h2>",
        dataframe_to_html_table(missingness),
        "<h2>Rows by source</h2>",
        dataframe_to_html_table(source_counts),
        "<h2>Rows by record type</h2>",
        dataframe_to_html_table(record_type_counts),
        "<h2>Rows by omics modality</h2>",
        dataframe_to_html_table(modality_counts),
        "<h2>Rows by data category</h2>",
        dataframe_to_html_table(category_counts),
        "<h2>Unknown-modality review list</h2>",
        dataframe_to_html_table(unknown_modality, max_rows=150),
        "<h2>Duplicate source_id + record_id review list</h2>",
        dataframe_to_html_table(duplicates, max_rows=150),
        "<h2>Missing source URL review list</h2>",
        dataframe_to_html_table(missing_urls, max_rows=150),
        "<h2>Brain / GBM / LGG relevant records</h2>",
        dataframe_to_html_table(brain_gbm, max_rows=150),
        '<div class="footer">Generated by OpenMultiOmics-Cancer-Atlas unified inventory QC report module.</div>',
        "</body>",
        "</html>",
    ]

    return "\n".join(html_lines)


def generate_unified_public_cancer_omics_qc_report(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
    title: str = "Unified Public Cancer Omics Inventory QC Report",
) -> str:
    """
    Generate QC HTML report and return HTML string.
    """
    df = read_unified_inventory(input_path)
    html_text = build_qc_report_html(df, title=title)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_text, encoding="utf-8")

    return html_text


def build_arg_parser() -> argparse.ArgumentParser:
    """
    Build CLI parser.
    """
    parser = argparse.ArgumentParser(
        description="Generate QC report for unified public cancer omics inventory."
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
        help=f"Output QC HTML report. Default: {DEFAULT_OUTPUT}",
    )

    parser.add_argument(
        "--title",
        default="Unified Public Cancer Omics Inventory QC Report",
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
        html_text = generate_unified_public_cancer_omics_qc_report(
            input_path=args.input,
            output_path=args.output,
            title=args.title,
        )
    except Exception as exc:
        print(f"ERROR: Failed to generate unified inventory QC report: {exc}", file=sys.stderr)
        return 1

    print("Unified public cancer omics inventory QC report complete.")
    print(f"HTML characters: {len(html_text)}")
    print(f"Output: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
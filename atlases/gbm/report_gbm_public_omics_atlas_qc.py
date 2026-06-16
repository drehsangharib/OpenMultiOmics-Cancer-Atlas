#!/usr/bin/env python3

import argparse
import html
import sys
from pathlib import Path

import pandas as pd


DEFAULT_INPUT = Path("outputs/atlases/gbm/gbm_public_omics_atlas_inventory.tsv")
DEFAULT_OUTPUT = Path("outputs/reports/gbm_public_omics_atlas_qc_report.html")

REQUIRED_COLUMNS = [
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


def read_gbm_inventory(input_path=DEFAULT_INPUT):
    if not input_path.exists():
        raise FileNotFoundError(
            f"GBM atlas inventory not found: {input_path}. "
            "Run python -m atlases.gbm.build_gbm_public_omics_atlas first."
        )

    df = pd.read_csv(input_path, sep="\t")

    for column in REQUIRED_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    return df.loc[:, REQUIRED_COLUMNS].copy()


def escape_html(value):
    if value is None:
        return ""
    return html.escape(str(value))


def dataframe_to_html_table(df, max_rows=None):
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


def value_counts_table(df, column, max_rows=None):
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


def build_qc_metrics(df):
    total_rows = int(len(df))
    source_count = int(df["source_id"].nunique()) if not df.empty else 0
    record_type_count = int(df["source_record_type"].nunique()) if not df.empty else 0
    modality_count = int(df["omics_modality"].nunique()) if not df.empty else 0
    unknown_modality_rows = int((df["omics_modality"].fillna("").astype(str) == "unknown").sum())
    missing_source_url_rows = int((df["source_url"].fillna("").astype(str).str.strip() == "").sum())

    return pd.DataFrame(
        [
            {"metric": "total_rows", "value": total_rows},
            {"metric": "source_count", "value": source_count},
            {"metric": "record_type_count", "value": record_type_count},
            {"metric": "modality_count", "value": modality_count},
            {"metric": "unknown_modality_rows", "value": unknown_modality_rows},
            {"metric": "missing_source_url_rows", "value": missing_source_url_rows},
        ]
    )


def build_missingness_table(df):
    rows = []
    total_rows = int(len(df))

    for column in REQUIRED_COLUMNS:
        missing = int((df[column].fillna("").astype(str).str.strip() == "").sum())
        missing_percent = round(100.0 * missing / total_rows, 2) if total_rows > 0 else 0.0

        rows.append(
            {
                "column": column,
                "missing_rows": missing,
                "missing_percent": missing_percent,
            }
        )

    return pd.DataFrame(rows)


def build_unknown_modality_table(df, max_rows=100):
    out = df[df["omics_modality"].fillna("").astype(str) == "unknown"].copy()

    columns = [
        "source_id",
        "source_record_type",
        "record_id",
        "record_name",
        "data_category",
        "matrix_type",
        "gbm_match_terms",
        "source_url",
    ]

    return out.loc[:, columns].head(max_rows).reset_index(drop=True)


def build_missing_source_url_table(df, max_rows=100):
    mask = df["source_url"].fillna("").astype(str).str.strip() == ""
    out = df[mask].copy()

    columns = [
        "source_id",
        "source_record_type",
        "record_id",
        "record_name",
        "omics_modality",
        "data_category",
        "gbm_match_terms",
    ]

    return out.loc[:, columns].head(max_rows).reset_index(drop=True)


def build_source_modality_coverage_table(df):
    if df.empty:
        return pd.DataFrame()

    out = (
        df.assign(_count=1)
        .pivot_table(
            index="source_id",
            columns="omics_modality",
            values="_count",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )

    out.columns.name = None
    return out


def build_qc_report_html(df, title="GBM Public Omics Atlas QC Report"):
    metrics = build_qc_metrics(df)
    source_counts = value_counts_table(df, "source_id")
    modality_counts = value_counts_table(df, "omics_modality")
    category_counts = value_counts_table(df, "data_category", max_rows=30)
    match_counts = value_counts_table(df, "gbm_match_terms", max_rows=30)
    missingness = build_missingness_table(df)
    unknown_modality = build_unknown_modality_table(df)
    missing_urls = build_missing_source_url_table(df)
    coverage = build_source_modality_coverage_table(df)

    metric_lookup = dict(zip(metrics["metric"], metrics["value"]))

    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        f"<title>{escape_html(title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This report summarizes quality-control checks for the GBM public omics atlas inventory.</p>",
        "<p><strong>Scope:</strong> This is a metadata-only QC report. Molecular matrices are not downloaded.</p>",
        "<h2>Summary</h2>",
        "<ul>",
        f"<li>Total records: {metric_lookup.get('total_rows', 0)}</li>",
        f"<li>Sources: {metric_lookup.get('source_count', 0)}</li>",
        f"<li>Record types: {metric_lookup.get('record_type_count', 0)}</li>",
        f"<li>Modalities: {metric_lookup.get('modality_count', 0)}</li>",
        f"<li>Unknown modality rows: {metric_lookup.get('unknown_modality_rows', 0)}</li>",
        f"<li>Missing source URL rows: {metric_lookup.get('missing_source_url_rows', 0)}</li>",
        "</ul>",
        "<h2>QC metrics</h2>",
        dataframe_to_html_table(metrics),
        "<h2>Rows by source</h2>",
        dataframe_to_html_table(source_counts),
        "<h2>Rows by modality</h2>",
        dataframe_to_html_table(modality_counts),
        "<h2>Rows by data category</h2>",
        dataframe_to_html_table(category_counts),
        "<h2>Rows by GBM match terms</h2>",
        dataframe_to_html_table(match_counts),
        "<h2>Source x modality coverage</h2>",
        dataframe_to_html_table(coverage),
        "<h2>Required-column missingness</h2>",
        dataframe_to_html_table(missingness),
        "<h2>Unknown-modality review</h2>",
        dataframe_to_html_table(unknown_modality, max_rows=100),
        "<h2>Missing source URL review</h2>",
        dataframe_to_html_table(missing_urls, max_rows=100),
        "</body>",
        "</html>",
    ]

    return "\n".join(html_parts)


def generate_gbm_public_omics_atlas_qc_report(
    input_path=DEFAULT_INPUT,
    output_path=DEFAULT_OUTPUT,
    title="GBM Public Omics Atlas QC Report",
):
    df = read_gbm_inventory(input_path)
    report_html = build_qc_report_html(df, title=title)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_html, encoding="utf-8")

    return report_html


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Generate QC report for GBM public omics atlas inventory."
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Input GBM atlas inventory TSV. Default: {DEFAULT_INPUT}",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output QC HTML report. Default: {DEFAULT_OUTPUT}",
    )

    parser.add_argument(
        "--title",
        default="GBM Public Omics Atlas QC Report",
        help="HTML report title.",
    )

    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        report_html = generate_gbm_public_omics_atlas_qc_report(
            input_path=args.input,
            output_path=args.output,
            title=args.title,
        )
    except Exception as exc:
        print(f"ERROR: Failed to generate GBM atlas QC report: {exc}", file=sys.stderr)
        return 1

    print("GBM public omics atlas QC report complete.")
    print(f"HTML characters: {len(report_html)}")
    print(f"Output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
#!/usr/bin/env python3

import argparse
import html
import sys
from pathlib import Path

import pandas as pd

from core.data.validate_data_manifest import (
    DEFAULT_MANIFEST_DIR,
    validate_manifest_dir,
)


DEFAULT_SUMMARY_OUTPUT = Path("outputs/reports/data_manifest_registry_summary.tsv")
DEFAULT_REPORT_OUTPUT = Path("outputs/reports/data_manifest_registry_report.html")


def escape_html(value):
    if value is None:
        return ""
    return html.escape(str(value))


def dataframe_to_html_table(df):
    if df.empty:
        return "<p>No records available.</p>"

    lines = ["<table border='1' cellspacing='0' cellpadding='5'>", "<thead><tr>"]
    for column in df.columns:
        lines.append(f"<th>{escape_html(column)}</th>")
    lines.append("</tr></thead><tbody>")

    for _, row in df.iterrows():
        lines.append("<tr>")
        for column in df.columns:
            lines.append(f"<td>{escape_html(row[column])}</td>")
        lines.append("</tr>")

    lines.append("</tbody></table>")
    return "\n".join(lines)


def value_counts_table(df, column):
    if df.empty or column not in df.columns:
        return pd.DataFrame(columns=[column, "count"])

    return (
        df[column]
        .fillna("")
        .astype(str)
        .value_counts()
        .rename_axis(column)
        .reset_index(name="count")
    )


def build_data_manifest_registry_report_html(summary_df, title="Data Manifest Registry Report"):
    modality_counts = value_counts_table(summary_df, "modality")
    atlas_counts = value_counts_table(summary_df, "atlas_name")
    source_counts = value_counts_table(summary_df, "source_name")

    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        f"<title>{escape_html(title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This report summarizes modality-aware data manifests for the AI multi-omics analysis agent/system.</p>",
        "<p><strong>North star:</strong> raw-data-to-biological-insight across transcriptome, proteome, epigenome, metabolome, and multi-omics integration.</p>",
        "<h2>Registry summary</h2>",
        dataframe_to_html_table(summary_df),
        "<h2>Manifests by modality</h2>",
        dataframe_to_html_table(modality_counts),
        "<h2>Manifests by atlas</h2>",
        dataframe_to_html_table(atlas_counts),
        "<h2>Manifests by source</h2>",
        dataframe_to_html_table(source_counts),
        "</body>",
        "</html>",
    ]

    return "\n".join(html_parts)


def build_data_manifest_registry_summary(
    manifest_dir=DEFAULT_MANIFEST_DIR,
    summary_output=DEFAULT_SUMMARY_OUTPUT,
    report_output=DEFAULT_REPORT_OUTPUT,
    title="Data Manifest Registry Report",
):
    summary_df = validate_manifest_dir(
        manifest_dir,
        summary_output=summary_output,
    )

    report_html = build_data_manifest_registry_report_html(summary_df, title=title)

    report_output = Path(report_output)
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(report_html, encoding="utf-8")

    return summary_df, report_html


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Build a registry summary for modality-aware data manifests."
    )

    parser.add_argument(
        "--manifest-dir",
        type=Path,
        default=DEFAULT_MANIFEST_DIR,
        help=f"Data manifest directory. Default: {DEFAULT_MANIFEST_DIR}",
    )

    parser.add_argument(
        "--summary-output",
        type=Path,
        default=DEFAULT_SUMMARY_OUTPUT,
        help=f"Summary TSV output. Default: {DEFAULT_SUMMARY_OUTPUT}",
    )

    parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_REPORT_OUTPUT,
        help=f"HTML report output. Default: {DEFAULT_REPORT_OUTPUT}",
    )

    parser.add_argument(
        "--title",
        default="Data Manifest Registry Report",
        help="HTML report title.",
    )

    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        summary_df, report_html = build_data_manifest_registry_summary(
            manifest_dir=args.manifest_dir,
            summary_output=args.summary_output,
            report_output=args.report_output,
            title=args.title,
        )
    except Exception as exc:
        print(f"ERROR: Failed to build data manifest registry summary: {exc}", file=sys.stderr)
        return 1

    print("Data manifest registry summary complete.")
    print(f"Manifest count: {len(summary_df)}")
    print(f"Summary output: {args.summary_output}")
    print(f"Report output: {args.report_output}")
    print(f"HTML characters: {len(report_html)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
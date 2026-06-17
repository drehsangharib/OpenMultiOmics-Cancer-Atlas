#!/usr/bin/env python3

import argparse
import html
import sys
from pathlib import Path

import pandas as pd

DEFAULT_BUILD_SUMMARY = Path("outputs/reports/atlas_batch_summary.tsv")
DEFAULT_QC_SUMMARY = Path("outputs/reports/atlas_qc_batch_summary.tsv")
DEFAULT_ATLAS_ROOT = Path("outputs/atlases")
DEFAULT_OUTPUT_TSV = Path("outputs/reports/cross_atlas_summary.tsv")
DEFAULT_OUTPUT_HTML = Path("outputs/reports/cross_atlas_summary_report.html")


REQUIRED_COLUMNS = [
    "source_id",
    "source_record_type",
    "record_id",
    "record_name",
    "omics_modality",
    "data_category",
    "source_url",
    "atlas_match_terms",
]


def load_tsv_if_exists(path):
    path = Path(path)
    if path.exists():
        return pd.read_csv(path, sep="\t")
    return pd.DataFrame()


def resolve_atlas_names(build_summary_df, atlas_root, atlas_names=None):
    if atlas_names:
        return [str(name).strip().lower() for name in atlas_names if str(name).strip()]

    if not build_summary_df.empty and "atlas_name" in build_summary_df.columns:
        values = build_summary_df["atlas_name"].fillna("").astype(str).str.strip().str.lower()
        values = [x for x in values if x]
        if values:
            return sorted(dict.fromkeys(values))

    atlas_root = Path(atlas_root)
    if atlas_root.exists():
        values = [p.name.strip().lower() for p in atlas_root.iterdir() if p.is_dir()]
        values = [x for x in values if x]
        if values:
            return sorted(dict.fromkeys(values))

    raise ValueError("No atlas names available for cross-atlas summary.")


def read_atlas_inventory(atlas_name, atlas_root=DEFAULT_ATLAS_ROOT):
    path = Path(atlas_root) / atlas_name / f"{atlas_name}_public_omics_atlas_inventory.tsv"

    if not path.exists():
        raise FileNotFoundError(f"Atlas inventory not found: {path}")

    df = pd.read_csv(path, sep="\t")

    for column in REQUIRED_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    return df.loc[:, REQUIRED_COLUMNS].copy(), path


def build_cross_atlas_summary_df(atlas_names, atlas_root, qc_summary_df):
    qc_lookup = {}
    if not qc_summary_df.empty and {"atlas_name", "qc_html_characters", "qc_report_path"}.issubset(qc_summary_df.columns):
        for _, row in qc_summary_df.iterrows():
            atlas_name = str(row["atlas_name"]).strip().lower()
            qc_lookup[atlas_name] = {
                "qc_html_characters": int(row["qc_html_characters"]),
                "qc_report_path": str(row["qc_report_path"]),
            }

    rows = []

    for atlas_name in atlas_names:
        df, inventory_path = read_atlas_inventory(atlas_name, atlas_root=atlas_root)

        rows.append(
            {
                "atlas_name": atlas_name,
                "rows": int(len(df)),
                "source_count": int(df["source_id"].nunique()) if not df.empty else 0,
                "record_type_count": int(df["source_record_type"].nunique()) if not df.empty else 0,
                "modality_count": int(df["omics_modality"].nunique()) if not df.empty else 0,
                "unknown_modality_rows": int((df["omics_modality"].fillna("").astype(str) == "unknown").sum()),
                "missing_source_url_rows": int((df["source_url"].fillna("").astype(str).str.strip() == "").sum()),
                "inventory_path": str(inventory_path),
                "qc_html_characters": int(qc_lookup.get(atlas_name, {}).get("qc_html_characters", 0)),
                "qc_report_path": str(qc_lookup.get(atlas_name, {}).get("qc_report_path", "")),
            }
        )

    return pd.DataFrame(rows)


def build_source_coverage_table(atlas_names, atlas_root):
    rows = []

    for atlas_name in atlas_names:
        df, _ = read_atlas_inventory(atlas_name, atlas_root=atlas_root)

        counts = (
            df["source_id"]
            .fillna("")
            .astype(str)
            .value_counts()
            .to_dict()
        )

        item = {"atlas_name": atlas_name}
        item.update(counts)
        rows.append(item)

    out = pd.DataFrame(rows).fillna(0)

    for column in out.columns:
        if column != "atlas_name":
            out[column] = out[column].astype(int)

    return out


def build_modality_coverage_table(atlas_names, atlas_root):
    rows = []

    for atlas_name in atlas_names:
        df, _ = read_atlas_inventory(atlas_name, atlas_root=atlas_root)

        counts = (
            df["omics_modality"]
            .fillna("")
            .astype(str)
            .value_counts()
            .to_dict()
        )

        item = {"atlas_name": atlas_name}
        item.update(counts)
        rows.append(item)

    out = pd.DataFrame(rows).fillna(0)

    for column in out.columns:
        if column != "atlas_name":
            out[column] = out[column].astype(int)

    return out


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


def build_cross_atlas_summary_html(
    summary_df,
    source_coverage_df,
    modality_coverage_df,
    title="Cross-Atlas Summary Report",
):
    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        f"<title>{escape_html(title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This report compares atlas-level metadata coverage across the currently built public omics atlases.</p>",
        "<p><strong>Scope:</strong> This is a metadata-only comparison report.</p>",
        "<h2>Atlas-level summary</h2>",
        dataframe_to_html_table(summary_df),
        "<h2>Source coverage by atlas</h2>",
        dataframe_to_html_table(source_coverage_df),
        "<h2>Modality coverage by atlas</h2>",
        dataframe_to_html_table(modality_coverage_df),
        "</body>",
        "</html>",
    ]

    return "\n".join(html_parts)


def generate_cross_atlas_summary(
    build_summary_path=DEFAULT_BUILD_SUMMARY,
    qc_summary_path=DEFAULT_QC_SUMMARY,
    atlas_root=DEFAULT_ATLAS_ROOT,
    output_tsv_path=DEFAULT_OUTPUT_TSV,
    output_html_path=DEFAULT_OUTPUT_HTML,
    atlas_names=None,
    title="Cross-Atlas Summary Report",
):
    build_summary_df = load_tsv_if_exists(build_summary_path)
    qc_summary_df = load_tsv_if_exists(qc_summary_path)

    atlas_names = resolve_atlas_names(build_summary_df, atlas_root, atlas_names=atlas_names)

    summary_df = build_cross_atlas_summary_df(atlas_names, atlas_root, qc_summary_df)
    source_coverage_df = build_source_coverage_table(atlas_names, atlas_root)
    modality_coverage_df = build_modality_coverage_table(atlas_names, atlas_root)

    output_tsv_path = Path(output_tsv_path)
    output_html_path = Path(output_html_path)

    output_tsv_path.parent.mkdir(parents=True, exist_ok=True)
    output_html_path.parent.mkdir(parents=True, exist_ok=True)

    summary_df.to_csv(output_tsv_path, sep="\t", index=False)

    report_html = build_cross_atlas_summary_html(
        summary_df,
        source_coverage_df,
        modality_coverage_df,
        title=title,
    )
    output_html_path.write_text(report_html, encoding="utf-8")

    return summary_df, report_html


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Generate a cross-atlas summary report from built atlas inventories and QC summaries."
    )

    parser.add_argument(
        "--atlases",
        nargs="*",
        default=None,
        help="Optional atlas names, e.g. gbm luad brca lgg",
    )

    parser.add_argument(
        "--build-summary",
        type=Path,
        default=DEFAULT_BUILD_SUMMARY,
        help=f"Atlas batch summary TSV. Default: {DEFAULT_BUILD_SUMMARY}",
    )

    parser.add_argument(
        "--qc-summary",
        type=Path,
        default=DEFAULT_QC_SUMMARY,
        help=f"Atlas QC batch summary TSV. Default: {DEFAULT_QC_SUMMARY}",
    )

    parser.add_argument(
        "--atlas-root",
        type=Path,
        default=DEFAULT_ATLAS_ROOT,
        help=f"Atlas inventory root directory. Default: {DEFAULT_ATLAS_ROOT}",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_TSV,
        help=f"Cross-atlas summary TSV output. Default: {DEFAULT_OUTPUT_TSV}",
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_OUTPUT_HTML,
        help=f"Cross-atlas HTML report output. Default: {DEFAULT_OUTPUT_HTML}",
    )

    parser.add_argument(
        "--title",
        default="Cross-Atlas Summary Report",
        help="HTML report title.",
    )

    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        summary_df, report_html = generate_cross_atlas_summary(
            build_summary_path=args.build_summary,
            qc_summary_path=args.qc_summary,
            atlas_root=args.atlas_root,
            output_tsv_path=args.output,
            output_html_path=args.report,
            atlas_names=args.atlases,
            title=args.title,
        )
    except Exception as exc:
        print(f"ERROR: Failed to generate cross-atlas summary report: {exc}", file=sys.stderr)
        return 1

    print("Cross-atlas summary report complete.")
    print(f"Atlas count: {len(summary_df)}")
    print(f"Summary output: {args.output}")
    print(f"HTML report: {args.report}")
    print(f"HTML characters: {len(report_html)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


import argparse

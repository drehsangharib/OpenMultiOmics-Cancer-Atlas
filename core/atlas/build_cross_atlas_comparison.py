#!/usr/bin/env python3

import argparse
import html
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


DEFAULT_BUILD_SUMMARY = Path("outputs/reports/atlas_batch_summary.tsv")
DEFAULT_QC_SUMMARY = Path("outputs/reports/atlas_qc_batch_summary.tsv")
DEFAULT_ATLAS_ROOT = Path("outputs/atlases")

DEFAULT_SUMMARY_OUTPUT = Path("outputs/reports/cross_atlas_comparison.tsv")
DEFAULT_SOURCE_MATRIX_OUTPUT = Path("outputs/reports/cross_atlas_source_matrix.tsv")
DEFAULT_MODALITY_MATRIX_OUTPUT = Path("outputs/reports/cross_atlas_modality_matrix.tsv")
DEFAULT_QC_METRICS_OUTPUT = Path("outputs/reports/cross_atlas_qc_metrics.tsv")

DEFAULT_ROWS_BAR = Path("outputs/reports/cross_atlas_rows_bar.png")
DEFAULT_UNKNOWN_BAR = Path("outputs/reports/cross_atlas_unknown_modality_bar.png")
DEFAULT_MISSING_URL_BAR = Path("outputs/reports/cross_atlas_missing_url_bar.png")
DEFAULT_SOURCE_STACKED_BAR = Path("outputs/reports/cross_atlas_source_stacked_bar.png")
DEFAULT_MODALITY_HEATMAP = Path("outputs/reports/cross_atlas_modality_heatmap.png")

DEFAULT_REPORT = Path("outputs/reports/cross_atlas_comparison_report.html")


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


def ensure_parent(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


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
        values = [value for value in values if value]
        if values:
            return sorted(dict.fromkeys(values))

    atlas_root = Path(atlas_root)
    if atlas_root.exists():
        values = [path.name.strip().lower() for path in atlas_root.iterdir() if path.is_dir()]
        values = [value for value in values if value]
        if values:
            return sorted(dict.fromkeys(values))

    raise ValueError("No atlas names available for cross-atlas comparison.")


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


def build_qc_metrics_table(summary_df):
    columns = [
        "atlas_name",
        "rows",
        "unknown_modality_rows",
        "missing_source_url_rows",
        "qc_html_characters",
        "qc_report_path",
    ]
    available = [column for column in columns if column in summary_df.columns]
    return summary_df.loc[:, available].copy()


def save_rows_bar(summary_df, output_path):
    output_path = ensure_parent(output_path)

    plt.figure(figsize=(8, 4.5))
    plt.bar(summary_df["atlas_name"], summary_df["rows"])
    plt.title("Rows by atlas")
    plt.xlabel("Atlas")
    plt.ylabel("Rows")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def save_unknown_modality_bar(summary_df, output_path):
    output_path = ensure_parent(output_path)

    plt.figure(figsize=(8, 4.5))
    plt.bar(summary_df["atlas_name"], summary_df["unknown_modality_rows"])
    plt.title("Unknown modality rows by atlas")
    plt.xlabel("Atlas")
    plt.ylabel("Unknown modality rows")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def save_missing_url_bar(summary_df, output_path):
    output_path = ensure_parent(output_path)

    plt.figure(figsize=(8, 4.5))
    plt.bar(summary_df["atlas_name"], summary_df["missing_source_url_rows"])
    plt.title("Missing source URL rows by atlas")
    plt.xlabel("Atlas")
    plt.ylabel("Missing source URL rows")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def save_source_stacked_bar(source_coverage_df, output_path):
    output_path = ensure_parent(output_path)

    categories = [column for column in source_coverage_df.columns if column != "atlas_name"]
    x = range(len(source_coverage_df))
    bottom = [0] * len(source_coverage_df)

    plt.figure(figsize=(8, 4.8))

    for category in categories:
        values = source_coverage_df[category].tolist()
        plt.bar(x, values, bottom=bottom, label=category)
        bottom = [a + b for a, b in zip(bottom, values)]

    plt.xticks(list(x), source_coverage_df["atlas_name"].tolist())
    plt.title("Source coverage by atlas")
    plt.xlabel("Atlas")
    plt.ylabel("Rows")
    if categories:
        plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def save_modality_heatmap(modality_coverage_df, output_path):
    output_path = ensure_parent(output_path)

    categories = [column for column in modality_coverage_df.columns if column != "atlas_name"]
    values = modality_coverage_df.loc[:, categories].to_numpy(dtype=float)

    width = max(8, len(categories) * 0.75)
    height = max(4, len(modality_coverage_df) * 0.8)

    plt.figure(figsize=(width, height))
    image = plt.imshow(values, aspect="auto")
    plt.colorbar(image)
    plt.title("Modality coverage heatmap")
    plt.xlabel("Modality")
    plt.ylabel("Atlas")
    plt.xticks(range(len(categories)), categories, rotation=45, ha="right")
    plt.yticks(range(len(modality_coverage_df)), modality_coverage_df["atlas_name"].tolist())
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


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


def image_tag(image_path):
    image_path = Path(image_path)
    return f"<img src='{escape_html(image_path.name)}' style='max-width: 100%; height: auto;'/>"


def build_cross_atlas_comparison_html(
    summary_df,
    source_coverage_df,
    modality_coverage_df,
    qc_metrics_df,
    rows_bar_path,
    unknown_bar_path,
    missing_url_bar_path,
    source_stacked_bar_path,
    modality_heatmap_path,
    title="Cross-Atlas Comparison Report",
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
        "<h2>QC metrics by atlas</h2>",
        dataframe_to_html_table(qc_metrics_df),
        "<h2>Rows by atlas</h2>",
        image_tag(rows_bar_path),
        "<h2>Unknown modality rows by atlas</h2>",
        image_tag(unknown_bar_path),
        "<h2>Missing source URL rows by atlas</h2>",
        image_tag(missing_url_bar_path),
        "<h2>Source coverage by atlas</h2>",
        dataframe_to_html_table(source_coverage_df),
        image_tag(source_stacked_bar_path),
        "<h2>Modality coverage by atlas</h2>",
        dataframe_to_html_table(modality_coverage_df),
        image_tag(modality_heatmap_path),
        "</body>",
        "</html>",
    ]

    return "\n".join(html_parts)


def generate_cross_atlas_comparison(
    build_summary_path=DEFAULT_BUILD_SUMMARY,
    qc_summary_path=DEFAULT_QC_SUMMARY,
    atlas_root=DEFAULT_ATLAS_ROOT,
    summary_output_path=DEFAULT_SUMMARY_OUTPUT,
    source_matrix_output_path=DEFAULT_SOURCE_MATRIX_OUTPUT,
    modality_matrix_output_path=DEFAULT_MODALITY_MATRIX_OUTPUT,
    qc_metrics_output_path=DEFAULT_QC_METRICS_OUTPUT,
    rows_bar_path=DEFAULT_ROWS_BAR,
    unknown_bar_path=DEFAULT_UNKNOWN_BAR,
    missing_url_bar_path=DEFAULT_MISSING_URL_BAR,
    source_stacked_bar_path=DEFAULT_SOURCE_STACKED_BAR,
    modality_heatmap_path=DEFAULT_MODALITY_HEATMAP,
    output_html_path=DEFAULT_REPORT,
    atlas_names=None,
    title="Cross-Atlas Comparison Report",
):
    build_summary_df = load_tsv_if_exists(build_summary_path)
    qc_summary_df = load_tsv_if_exists(qc_summary_path)

    atlas_names = resolve_atlas_names(build_summary_df, atlas_root, atlas_names=atlas_names)

    summary_df = build_cross_atlas_summary_df(atlas_names, atlas_root, qc_summary_df)
    source_coverage_df = build_source_coverage_table(atlas_names, atlas_root)
    modality_coverage_df = build_modality_coverage_table(atlas_names, atlas_root)
    qc_metrics_df = build_qc_metrics_table(summary_df)

    summary_output_path = ensure_parent(summary_output_path)
    source_matrix_output_path = ensure_parent(source_matrix_output_path)
    modality_matrix_output_path = ensure_parent(modality_matrix_output_path)
    qc_metrics_output_path = ensure_parent(qc_metrics_output_path)
    output_html_path = ensure_parent(output_html_path)

    summary_df.to_csv(summary_output_path, sep="\t", index=False)
    source_coverage_df.to_csv(source_matrix_output_path, sep="\t", index=False)
    modality_coverage_df.to_csv(modality_matrix_output_path, sep="\t", index=False)
    qc_metrics_df.to_csv(qc_metrics_output_path, sep="\t", index=False)

    save_rows_bar(summary_df, rows_bar_path)
    save_unknown_modality_bar(summary_df, unknown_bar_path)
    save_missing_url_bar(summary_df, missing_url_bar_path)
    save_source_stacked_bar(source_coverage_df, source_stacked_bar_path)
    save_modality_heatmap(modality_coverage_df, modality_heatmap_path)

    report_html = build_cross_atlas_comparison_html(
        summary_df,
        source_coverage_df,
        modality_coverage_df,
        qc_metrics_df,
        rows_bar_path,
        unknown_bar_path,
        missing_url_bar_path,
        source_stacked_bar_path,
        modality_heatmap_path,
        title=title,
    )
    output_html_path.write_text(report_html, encoding="utf-8")

    return summary_df, report_html


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Generate a cross-atlas comparison report from built atlas inventories and QC summaries."
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
        default=DEFAULT_SUMMARY_OUTPUT,
        help=f"Cross-atlas comparison TSV output. Default: {DEFAULT_SUMMARY_OUTPUT}",
    )

    parser.add_argument(
        "--source-matrix",
        type=Path,
        default=DEFAULT_SOURCE_MATRIX_OUTPUT,
        help=f"Cross-atlas source matrix TSV output. Default: {DEFAULT_SOURCE_MATRIX_OUTPUT}",
    )

    parser.add_argument(
        "--modality-matrix",
        type=Path,
        default=DEFAULT_MODALITY_MATRIX_OUTPUT,
        help=f"Cross-atlas modality matrix TSV output. Default: {DEFAULT_MODALITY_MATRIX_OUTPUT}",
    )

    parser.add_argument(
        "--qc-metrics",
        type=Path,
        default=DEFAULT_QC_METRICS_OUTPUT,
        help=f"Cross-atlas QC metrics TSV output. Default: {DEFAULT_QC_METRICS_OUTPUT}",
    )

    parser.add_argument(
        "--rows-bar",
        type=Path,
        default=DEFAULT_ROWS_BAR,
        help=f"Rows-by-atlas chart PNG output. Default: {DEFAULT_ROWS_BAR}",
    )

    parser.add_argument(
        "--unknown-bar",
        type=Path,
        default=DEFAULT_UNKNOWN_BAR,
        help=f"Unknown-modality chart PNG output. Default: {DEFAULT_UNKNOWN_BAR}",
    )

    parser.add_argument(
        "--missing-url-bar",
        type=Path,
        default=DEFAULT_MISSING_URL_BAR,
        help=f"Missing-source-URL chart PNG output. Default: {DEFAULT_MISSING_URL_BAR}",
    )

    parser.add_argument(
        "--source-stacked-bar",
        type=Path,
        default=DEFAULT_SOURCE_STACKED_BAR,
        help=f"Source stacked-bar PNG output. Default: {DEFAULT_SOURCE_STACKED_BAR}",
    )

    parser.add_argument(
        "--modality-heatmap",
        type=Path,
        default=DEFAULT_MODALITY_HEATMAP,
        help=f"Modality heatmap PNG output. Default: {DEFAULT_MODALITY_HEATMAP}",
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"Cross-atlas HTML report output. Default: {DEFAULT_REPORT}",
    )

    parser.add_argument(
        "--title",
        default="Cross-Atlas Comparison Report",
        help="HTML report title.",
    )

    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        summary_df, report_html = generate_cross_atlas_comparison(
            build_summary_path=args.build_summary,
            qc_summary_path=args.qc_summary,
            atlas_root=args.atlas_root,
            summary_output_path=args.output,
            source_matrix_output_path=args.source_matrix,
            modality_matrix_output_path=args.modality_matrix,
            qc_metrics_output_path=args.qc_metrics,
            rows_bar_path=args.rows_bar,
            unknown_bar_path=args.unknown_bar,
            missing_url_bar_path=args.missing_url_bar,
            source_stacked_bar_path=args.source_stacked_bar,
            modality_heatmap_path=args.modality_heatmap,
            output_html_path=args.report,
            atlas_names=args.atlases,
            title=args.title,
        )
    except Exception as exc:
        print(f"ERROR: Failed to generate cross-atlas comparison report: {exc}", file=sys.stderr)
        return 1

    print("Cross-atlas comparison report complete.")
    print(f"Atlas count: {len(summary_df)}")
    print(f"Summary output: {args.output}")
    print(f"HTML report: {args.report}")
    print(f"HTML characters: {len(report_html)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

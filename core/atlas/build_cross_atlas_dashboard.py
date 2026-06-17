#!/usr/bin/env python3

import argparse
import html
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import yaml


DEFAULT_DISPLAY_REGISTRY = Path("configs/atlas_registry/atlas_display_registry.yaml")
DEFAULT_BUILD_SUMMARY = Path("outputs/reports/atlas_batch_summary.tsv")
DEFAULT_QC_SUMMARY = Path("outputs/reports/atlas_qc_batch_summary.tsv")
DEFAULT_ATLAS_ROOT = Path("outputs/atlases")

DEFAULT_SUMMARY_OUTPUT = Path("outputs/reports/cross_atlas_dashboard_summary.tsv")
DEFAULT_SOURCE_MATRIX_OUTPUT = Path("outputs/reports/cross_atlas_dashboard_source_matrix.tsv")
DEFAULT_MODALITY_MATRIX_OUTPUT = Path("outputs/reports/cross_atlas_dashboard_modality_matrix.tsv")
DEFAULT_QC_METRICS_OUTPUT = Path("outputs/reports/cross_atlas_dashboard_qc_metrics.tsv")
DEFAULT_RANKINGS_OUTPUT = Path("outputs/reports/cross_atlas_rankings.tsv")

DEFAULT_ROWS_BAR = Path("outputs/reports/cross_atlas_rows_bar.png")
DEFAULT_UNKNOWN_BAR = Path("outputs/reports/cross_atlas_unknown_modality_bar.png")
DEFAULT_MISSING_URL_BAR = Path("outputs/reports/cross_atlas_missing_url_bar.png")
DEFAULT_SOURCE_STACKED_BAR = Path("outputs/reports/cross_atlas_source_stacked_bar.png")
DEFAULT_MODALITY_HEATMAP = Path("outputs/reports/cross_atlas_modality_heatmap.png")
DEFAULT_RANKINGS_BAR = Path("outputs/reports/cross_atlas_rankings_bar.png")

DEFAULT_REPORT = Path("outputs/reports/cross_atlas_dashboard.html")


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


def load_yaml_mapping(path):
    path = Path(path)

    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Display registry YAML must be a mapping: {path}")

    return data


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

    raise ValueError("No atlas names available for dashboard build.")


def read_atlas_inventory(atlas_name, atlas_root=DEFAULT_ATLAS_ROOT):
    path = Path(atlas_root) / atlas_name / f"{atlas_name}_public_omics_atlas_inventory.tsv"

    if not path.exists():
        raise FileNotFoundError(f"Atlas inventory not found: {path}")

    df = pd.read_csv(path, sep="\t")

    for column in REQUIRED_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    return df.loc[:, REQUIRED_COLUMNS].copy(), path


def load_display_registry(display_registry_path, atlas_names):
    raw = load_yaml_mapping(display_registry_path)
    out = {}

    for index, atlas_name in enumerate(atlas_names, start=1):
        item = raw.get(atlas_name, {}) if isinstance(raw, dict) else {}
        if not isinstance(item, dict):
            item = {}

        out[atlas_name] = {
            "display_name": str(item.get("display_name", atlas_name.upper())),
            "short_name": str(item.get("short_name", atlas_name.upper())),
            "color": str(item.get("color", "#4c78a8")),
            "order": int(item.get("order", index)),
        }

    return out


def build_summary_lookup(build_summary_df):
    lookup = {}
    if not build_summary_df.empty and {"atlas_name", "report_path", "output_path"}.issubset(build_summary_df.columns):
        for _, row in build_summary_df.iterrows():
            atlas_name = str(row["atlas_name"]).strip().lower()
            lookup[atlas_name] = {
                "atlas_report_path": str(row["report_path"]),
                "inventory_path": str(row["output_path"]),
            }
    return lookup


def build_qc_lookup(qc_summary_df):
    lookup = {}
    if not qc_summary_df.empty and {"atlas_name", "qc_html_characters", "qc_report_path"}.issubset(qc_summary_df.columns):
        for _, row in qc_summary_df.iterrows():
            atlas_name = str(row["atlas_name"]).strip().lower()
            lookup[atlas_name] = {
                "qc_html_characters": int(row["qc_html_characters"]),
                "qc_report_path": str(row["qc_report_path"]),
            }
    return lookup


def build_dashboard_summary_df(atlas_names, atlas_root, build_summary_df, qc_summary_df, display_registry):
    build_lookup = build_summary_lookup(build_summary_df)
    qc_lookup = build_qc_lookup(qc_summary_df)

    rows = []

    for atlas_name in atlas_names:
        df, inventory_path = read_atlas_inventory(atlas_name, atlas_root=atlas_root)
        meta = display_registry[atlas_name]

        rows.append(
            {
                "atlas_name": atlas_name,
                "display_name": meta["display_name"],
                "short_name": meta["short_name"],
                "color": meta["color"],
                "order": meta["order"],
                "rows": int(len(df)),
                "source_count": int(df["source_id"].nunique()) if not df.empty else 0,
                "record_type_count": int(df["source_record_type"].nunique()) if not df.empty else 0,
                "modality_count": int(df["omics_modality"].nunique()) if not df.empty else 0,
                "unknown_modality_rows": int((df["omics_modality"].fillna("").astype(str) == "unknown").sum()),
                "missing_source_url_rows": int((df["source_url"].fillna("").astype(str).str.strip() == "").sum()),
                "inventory_path": str(build_lookup.get(atlas_name, {}).get("inventory_path", inventory_path)),
                "atlas_report_path": str(
                    build_lookup.get(atlas_name, {}).get(
                        "atlas_report_path",
                        Path("outputs/reports") / f"{atlas_name}_public_omics_atlas_report.html",
                    )
                ),
                "qc_html_characters": int(qc_lookup.get(atlas_name, {}).get("qc_html_characters", 0)),
                "qc_report_path": str(
                    qc_lookup.get(atlas_name, {}).get(
                        "qc_report_path",
                        Path("outputs/reports") / f"{atlas_name}_public_omics_atlas_qc_report.html",
                    )
                ),
            }
        )

    summary_df = pd.DataFrame(rows)
    return summary_df.sort_values(by=["order", "atlas_name"], kind="stable").reset_index(drop=True)


def build_source_matrix(atlas_names, atlas_root, display_registry):
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

        item = {
            "atlas_name": atlas_name,
            "display_name": display_registry[atlas_name]["display_name"],
        }
        item.update(counts)
        rows.append(item)

    out = pd.DataFrame(rows).fillna(0)

    for column in out.columns:
        if column not in {"atlas_name", "display_name"}:
            out[column] = out[column].astype(int)

    return out


def build_modality_matrix(atlas_names, atlas_root, display_registry):
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

        item = {
            "atlas_name": atlas_name,
            "display_name": display_registry[atlas_name]["display_name"],
        }
        item.update(counts)
        rows.append(item)

    out = pd.DataFrame(rows).fillna(0)

    for column in out.columns:
        if column not in {"atlas_name", "display_name"}:
            out[column] = out[column].astype(int)

    return out


def build_qc_metrics_df(summary_df):
    columns = [
        "atlas_name",
        "display_name",
        "rows",
        "unknown_modality_rows",
        "missing_source_url_rows",
        "qc_html_characters",
        "qc_report_path",
    ]
    return summary_df.loc[:, columns].copy()


def build_rankings_df(summary_df):
    out = summary_df.copy()

    out["rank_rows"] = out["rows"].rank(method="dense", ascending=False).astype(int)
    out["rank_modality_count"] = out["modality_count"].rank(method="dense", ascending=False).astype(int)
    out["rank_unknown_modality_rows"] = out["unknown_modality_rows"].rank(method="dense", ascending=True).astype(int)
    out["rank_missing_source_url_rows"] = out["missing_source_url_rows"].rank(method="dense", ascending=True).astype(int)

    out["composite_rank_score"] = (
        out["rank_rows"]
        + out["rank_modality_count"]
        + out["rank_unknown_modality_rows"]
        + out["rank_missing_source_url_rows"]
    )
    out["overall_rank"] = out["composite_rank_score"].rank(method="dense", ascending=True).astype(int)

    columns = [
        "atlas_name",
        "display_name",
        "rows",
        "modality_count",
        "unknown_modality_rows",
        "missing_source_url_rows",
        "rank_rows",
        "rank_modality_count",
        "rank_unknown_modality_rows",
        "rank_missing_source_url_rows",
        "composite_rank_score",
        "overall_rank",
    ]

    return out.loc[:, columns].sort_values(by=["overall_rank", "atlas_name"], kind="stable").reset_index(drop=True)


def save_rows_bar(summary_df, output_path):
    output_path = ensure_parent(output_path)

    plt.figure(figsize=(9, 4.8))
    plt.bar(summary_df["short_name"], summary_df["rows"], color=summary_df["color"])
    plt.title("Rows by atlas")
    plt.xlabel("Atlas")
    plt.ylabel("Rows")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def save_unknown_modality_bar(summary_df, output_path):
    output_path = ensure_parent(output_path)

    plt.figure(figsize=(9, 4.8))
    plt.bar(summary_df["short_name"], summary_df["unknown_modality_rows"], color=summary_df["color"])
    plt.title("Unknown modality rows by atlas")
    plt.xlabel("Atlas")
    plt.ylabel("Unknown modality rows")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def save_missing_url_bar(summary_df, output_path):
    output_path = ensure_parent(output_path)

    plt.figure(figsize=(9, 4.8))
    plt.bar(summary_df["short_name"], summary_df["missing_source_url_rows"], color=summary_df["color"])
    plt.title("Missing source URL rows by atlas")
    plt.xlabel("Atlas")
    plt.ylabel("Missing source URL rows")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def save_source_stacked_bar(source_matrix_df, summary_df, output_path):
    output_path = ensure_parent(output_path)

    categories = [column for column in source_matrix_df.columns if column not in {"atlas_name", "display_name"}]
    x = range(len(source_matrix_df))
    bottom = [0] * len(source_matrix_df)

    plt.figure(figsize=(9, 5))

    for category in categories:
        values = source_matrix_df[category].tolist()
        plt.bar(x, values, bottom=bottom, label=category)
        bottom = [a + b for a, b in zip(bottom, values)]

    plt.xticks(list(x), source_matrix_df["display_name"].tolist(), rotation=15, ha="right")
    plt.title("Source coverage by atlas")
    plt.xlabel("Atlas")
    plt.ylabel("Rows")
    if categories:
        plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def save_modality_heatmap(modality_matrix_df, output_path):
    output_path = ensure_parent(output_path)

    categories = [column for column in modality_matrix_df.columns if column not in {"atlas_name", "display_name"}]
    values = modality_matrix_df.loc[:, categories].to_numpy(dtype=float)

    width = max(10, len(categories) * 0.85)
    height = max(4.5, len(modality_matrix_df) * 0.9)

    plt.figure(figsize=(width, height))
    image = plt.imshow(values, aspect="auto")
    plt.colorbar(image)
    plt.title("Modality coverage heatmap")
    plt.xlabel("Modality")
    plt.ylabel("Atlas")
    plt.xticks(range(len(categories)), categories, rotation=45, ha="right")
    plt.yticks(range(len(modality_matrix_df)), modality_matrix_df["display_name"].tolist())
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


def save_rankings_bar(rankings_df, output_path):
    output_path = ensure_parent(output_path)

    plt.figure(figsize=(9, 4.8))
    plt.bar(rankings_df["display_name"], rankings_df["composite_rank_score"])
    plt.title("Composite ranking score by atlas (lower is better)")
    plt.xlabel("Atlas")
    plt.ylabel("Composite rank score")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
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


def build_atlas_cards_html(summary_df):
    cards = []

    for _, row in summary_df.iterrows():
        cards.append(
            (
                "<div style='border: 1px solid #ccc; padding: 12px; margin: 8px; border-radius: 8px; "
                "display: inline-block; min-width: 240px; vertical-align: top;'>"
                f"<h3 style='margin-top: 0;'>{escape_html(row['display_name'])} ({escape_html(row['short_name'])})</h3>"
                f"<p><strong>Rows:</strong> {row['rows']}</p>"
                f"<p><strong>Sources:</strong> {row['source_count']}</p>"
                f"<p><strong>Modalities:</strong> {row['modality_count']}</p>"
                f"<p><strong>Unknown modality rows:</strong> {row['unknown_modality_rows']}</p>"
                f"<p><strong>Missing source URL rows:</strong> {row['missing_source_url_rows']}</p>"
                f"<p><strong>Atlas report:</strong> {escape_html(row['atlas_report_path'])}</p>"
                f"<p><strong>Atlas QC report:</strong> {escape_html(row['qc_report_path'])}</p>"
                "</div>"
            )
        )

    return "\n".join(cards)


def build_cross_atlas_dashboard_html(
    summary_df,
    source_matrix_df,
    modality_matrix_df,
    qc_metrics_df,
    rankings_df,
    rows_bar_path,
    unknown_bar_path,
    missing_url_bar_path,
    source_stacked_bar_path,
    modality_heatmap_path,
    rankings_bar_path,
    title="Cross-Atlas Intelligence Dashboard",
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
        "<p>This dashboard compares metadata coverage, QC burden, and overall atlas footprint across the currently built public omics atlases.</p>",
        "<p><strong>Scope:</strong> This is a metadata-only dashboard.</p>",
        "<h2>Atlas overview cards</h2>",
        build_atlas_cards_html(summary_df),
        "<h2>Atlas-level summary</h2>",
        dataframe_to_html_table(summary_df),
        "<h2>Atlas rankings</h2>",
        dataframe_to_html_table(rankings_df),
        image_tag(rankings_bar_path),
        "<h2>QC metrics by atlas</h2>",
        dataframe_to_html_table(qc_metrics_df),
        "<h2>Rows by atlas</h2>",
        image_tag(rows_bar_path),
        "<h2>Unknown modality rows by atlas</h2>",
        image_tag(unknown_bar_path),
        "<h2>Missing source URL rows by atlas</h2>",
        image_tag(missing_url_bar_path),
        "<h2>Source coverage by atlas</h2>",
        dataframe_to_html_table(source_matrix_df),
        image_tag(source_stacked_bar_path),
        "<h2>Modality coverage by atlas</h2>",
        dataframe_to_html_table(modality_matrix_df),
        image_tag(modality_heatmap_path),
        "</body>",
        "</html>",
    ]

    return "\n".join(html_parts)


def generate_cross_atlas_dashboard(
    display_registry_path=DEFAULT_DISPLAY_REGISTRY,
    build_summary_path=DEFAULT_BUILD_SUMMARY,
    qc_summary_path=DEFAULT_QC_SUMMARY,
    atlas_root=DEFAULT_ATLAS_ROOT,
    summary_output_path=DEFAULT_SUMMARY_OUTPUT,
    source_matrix_output_path=DEFAULT_SOURCE_MATRIX_OUTPUT,
    modality_matrix_output_path=DEFAULT_MODALITY_MATRIX_OUTPUT,
    qc_metrics_output_path=DEFAULT_QC_METRICS_OUTPUT,
    rankings_output_path=DEFAULT_RANKINGS_OUTPUT,
    rows_bar_path=DEFAULT_ROWS_BAR,
    unknown_bar_path=DEFAULT_UNKNOWN_BAR,
    missing_url_bar_path=DEFAULT_MISSING_URL_BAR,
    source_stacked_bar_path=DEFAULT_SOURCE_STACKED_BAR,
    modality_heatmap_path=DEFAULT_MODALITY_HEATMAP,
    rankings_bar_path=DEFAULT_RANKINGS_BAR,
    output_html_path=DEFAULT_REPORT,
    atlas_names=None,
    title="Cross-Atlas Intelligence Dashboard",
):
    build_summary_df = load_tsv_if_exists(build_summary_path)
    qc_summary_df = load_tsv_if_exists(qc_summary_path)

    atlas_names = resolve_atlas_names(build_summary_df, atlas_root, atlas_names=atlas_names)
    display_registry = load_display_registry(display_registry_path, atlas_names)

    summary_df = build_dashboard_summary_df(atlas_names, atlas_root, build_summary_df, qc_summary_df, display_registry)
    source_matrix_df = build_source_matrix(atlas_names, atlas_root, display_registry)
    modality_matrix_df = build_modality_matrix(atlas_names, atlas_root, display_registry)
    qc_metrics_df = build_qc_metrics_df(summary_df)
    rankings_df = build_rankings_df(summary_df)

    summary_output_path = ensure_parent(summary_output_path)
    source_matrix_output_path = ensure_parent(source_matrix_output_path)
    modality_matrix_output_path = ensure_parent(modality_matrix_output_path)
    qc_metrics_output_path = ensure_parent(qc_metrics_output_path)
    rankings_output_path = ensure_parent(rankings_output_path)
    output_html_path = ensure_parent(output_html_path)

    summary_df.to_csv(summary_output_path, sep="\t", index=False)
    source_matrix_df.to_csv(source_matrix_output_path, sep="\t", index=False)
    modality_matrix_df.to_csv(modality_matrix_output_path, sep="\t", index=False)
    qc_metrics_df.to_csv(qc_metrics_output_path, sep="\t", index=False)
    rankings_df.to_csv(rankings_output_path, sep="\t", index=False)

    save_rows_bar(summary_df, rows_bar_path)
    save_unknown_modality_bar(summary_df, unknown_bar_path)
    save_missing_url_bar(summary_df, missing_url_bar_path)
    save_source_stacked_bar(source_matrix_df, summary_df, source_stacked_bar_path)
    save_modality_heatmap(modality_matrix_df, modality_heatmap_path)
    save_rankings_bar(rankings_df, rankings_bar_path)

    report_html = build_cross_atlas_dashboard_html(
        summary_df,
        source_matrix_df,
        modality_matrix_df,
        qc_metrics_df,
        rankings_df,
        rows_bar_path,
        unknown_bar_path,
        missing_url_bar_path,
        source_stacked_bar_path,
        modality_heatmap_path,
        rankings_bar_path,
        title=title,
    )
    output_html_path.write_text(report_html, encoding="utf-8")

    return summary_df, rankings_df, report_html


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Generate a cross-atlas intelligence dashboard from built atlas inventories and QC summaries."
    )

    parser.add_argument(
        "--atlases",
        nargs="*",
        default=None,
        help="Optional atlas names, e.g. gbm luad brca lgg",
    )

    parser.add_argument(
        "--display-registry",
        type=Path,
        default=DEFAULT_DISPLAY_REGISTRY,
        help=f"Atlas display registry YAML. Default: {DEFAULT_DISPLAY_REGISTRY}",
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
        help=f"Dashboard summary TSV output. Default: {DEFAULT_SUMMARY_OUTPUT}",
    )

    parser.add_argument(
        "--source-matrix",
        type=Path,
        default=DEFAULT_SOURCE_MATRIX_OUTPUT,
        help=f"Dashboard source matrix TSV output. Default: {DEFAULT_SOURCE_MATRIX_OUTPUT}",
    )

    parser.add_argument(
        "--modality-matrix",
        type=Path,
        default=DEFAULT_MODALITY_MATRIX_OUTPUT,
        help=f"Dashboard modality matrix TSV output. Default: {DEFAULT_MODALITY_MATRIX_OUTPUT}",
    )

    parser.add_argument(
        "--qc-metrics",
        type=Path,
        default=DEFAULT_QC_METRICS_OUTPUT,
        help=f"Dashboard QC metrics TSV output. Default: {DEFAULT_QC_METRICS_OUTPUT}",
    )

    parser.add_argument(
        "--rankings",
        type=Path,
        default=DEFAULT_RANKINGS_OUTPUT,
        help=f"Dashboard rankings TSV output. Default: {DEFAULT_RANKINGS_OUTPUT}",
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
        "--rankings-bar",
        type=Path,
        default=DEFAULT_RANKINGS_BAR,
        help=f"Rankings bar PNG output. Default: {DEFAULT_RANKINGS_BAR}",
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"Dashboard HTML report output. Default: {DEFAULT_REPORT}",
    )

    parser.add_argument(
        "--title",
        default="Cross-Atlas Intelligence Dashboard",
        help="HTML report title.",
    )

    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        summary_df, rankings_df, report_html = generate_cross_atlas_dashboard(
            display_registry_path=args.display_registry,
            build_summary_path=args.build_summary,
            qc_summary_path=args.qc_summary,
            atlas_root=args.atlas_root,
            summary_output_path=args.output,
            source_matrix_output_path=args.source_matrix,
            modality_matrix_output_path=args.modality_matrix,
            qc_metrics_output_path=args.qc_metrics,
            rankings_output_path=args.rankings,
            rows_bar_path=args.rows_bar,
            unknown_bar_path=args.unknown_bar,
            missing_url_bar_path=args.missing_url_bar,
            source_stacked_bar_path=args.source_stacked_bar,
            modality_heatmap_path=args.modality_heatmap,
            rankings_bar_path=args.rankings_bar,
            output_html_path=args.report,
            atlas_names=args.atlases,
            title=args.title,
        )
    except Exception as exc:
        print(f"ERROR: Failed to generate cross-atlas dashboard: {exc}", file=sys.stderr)
        return 1

    print("Cross-atlas dashboard complete.")
    print(f"Atlas count: {len(summary_df)}")
    print(f"Ranked atlases: {len(rankings_df)}")
    print(f"Summary output: {args.output}")
    print(f"HTML report: {args.report}")
    print(f"HTML characters: {len(report_html)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
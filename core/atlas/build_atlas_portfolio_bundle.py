#!/usr/bin/env python3

import argparse
import html
import shutil
import sys
import zipfile
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_DISPLAY_REGISTRY = Path("configs/atlas_registry/atlas_display_registry.yaml")
DEFAULT_DASHBOARD_SUMMARY = Path("outputs/reports/cross_atlas_dashboard_summary.tsv")
DEFAULT_RANKINGS = Path("outputs/reports/cross_atlas_rankings.tsv")
DEFAULT_DASHBOARD_HTML = Path("outputs/reports/cross_atlas_dashboard.html")
DEFAULT_REPORTS_DIR = Path("outputs/reports")
DEFAULT_BUNDLE_DIR = Path("outputs/releases/atlas_portfolio_bundle")
DEFAULT_ZIP_OUTPUT = Path("outputs/releases/openmultiomics_cancer_atlas_portfolio_v0_3_0.zip")


def ensure_parent(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def ensure_dir(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_tsv(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Required TSV not found: {path}")
    return pd.read_csv(path, sep="\t")


def load_yaml_mapping(path):
    path = Path(path)
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ValueError(f"YAML mapping expected: {path}")

    return data


def filter_atlases(summary_df, atlas_names=None):
    if not atlas_names:
        return summary_df.copy()

    selected = {str(name).strip().lower() for name in atlas_names if str(name).strip()}
    out = summary_df.copy()
    out["atlas_name"] = out["atlas_name"].astype(str).str.strip().str.lower()
    return out[out["atlas_name"].isin(selected)].reset_index(drop=True)


def normalize_registry(display_registry, atlas_names):
    out = {}
    for index, atlas_name in enumerate(atlas_names, start=1):
        item = display_registry.get(atlas_name, {}) if isinstance(display_registry, dict) else {}
        if not isinstance(item, dict):
            item = {}
        out[atlas_name] = {
            "display_name": str(item.get("display_name", atlas_name.upper())),
            "short_name": str(item.get("short_name", atlas_name.upper())),
            "color": str(item.get("color", "#4c78a8")),
            "order": int(item.get("order", index)),
        }
    return out


def safe_copy(src, dst_dir):
    src = Path(src)
    dst_dir = ensure_dir(dst_dir)

    if not src.exists():
        return ""

    dst = dst_dir / src.name
    shutil.copy2(src, dst)
    return dst.name


def collect_report_files(summary_df, reports_dir):
    reports_dir = Path(reports_dir)
    extra = []

    for column in ["atlas_report_path", "qc_report_path"]:
        if column in summary_df.columns:
            for value in summary_df[column].fillna("").astype(str):
                if value.strip():
                    extra.append(Path(value))

    known = [
        reports_dir / "cross_atlas_dashboard.html",
        reports_dir / "cross_atlas_dashboard_summary.tsv",
        reports_dir / "cross_atlas_dashboard_source_matrix.tsv",
        reports_dir / "cross_atlas_dashboard_modality_matrix.tsv",
        reports_dir / "cross_atlas_dashboard_qc_metrics.tsv",
        reports_dir / "cross_atlas_rankings.tsv",
        reports_dir / "cross_atlas_rows_bar.png",
        reports_dir / "cross_atlas_unknown_modality_bar.png",
        reports_dir / "cross_atlas_missing_url_bar.png",
        reports_dir / "cross_atlas_source_stacked_bar.png",
        reports_dir / "cross_atlas_modality_heatmap.png",
        reports_dir / "cross_atlas_rankings_bar.png",
    ]
    extra.extend(known)

    seen = set()
    deduped = []
    for path in extra:
        key = str(path)
        if key not in seen:
            seen.add(key)
            deduped.append(path)

    return deduped


def build_benchmark_df(summary_df, rankings_df, display_registry):
    if rankings_df is None or rankings_df.empty:
        out = summary_df.copy()
        out["overall_rank"] = out["rows"].rank(method="dense", ascending=False).astype(int)
        out["composite_rank_score"] = out["overall_rank"]
    else:
        merge_cols = [
            col
            for col in rankings_df.columns
            if col in {"atlas_name", "overall_rank", "composite_rank_score"}
        ]
        out = summary_df.merge(rankings_df.loc[:, merge_cols], on="atlas_name", how="left")

        if "overall_rank" not in out.columns:
            out["overall_rank"] = out["rows"].rank(method="dense", ascending=False).astype(int)
        else:
            out["overall_rank"] = out["overall_rank"].fillna(
                out["rows"].rank(method="dense", ascending=False)
            ).astype(int)

        if "composite_rank_score" not in out.columns:
            out["composite_rank_score"] = out["overall_rank"]
        else:
            out["composite_rank_score"] = out["composite_rank_score"].fillna(
                out["overall_rank"]
            ).astype(int)

    rows = []
    for _, row in out.iterrows():
        atlas_name = str(row["atlas_name"])
        meta = display_registry[atlas_name]
        rows.append(
            {
                "atlas_name": atlas_name,
                "display_name": meta["display_name"],
                "short_name": meta["short_name"],
                "rows": int(row.get("rows", 0)),
                "modality_count": int(row.get("modality_count", 0)),
                "source_count": int(row.get("source_count", 0)),
                "unknown_modality_rows": int(row.get("unknown_modality_rows", 0)),
                "missing_source_url_rows": int(row.get("missing_source_url_rows", 0)),
                "overall_rank": int(row.get("overall_rank", 0)),
                "composite_rank_score": int(row.get("composite_rank_score", 0)),
            }
        )

    benchmark_df = pd.DataFrame(rows)
    sort_cols = [col for col in ["overall_rank", "atlas_name"] if col in benchmark_df.columns]
    return benchmark_df.sort_values(by=sort_cols, kind="stable").reset_index(drop=True)


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


def link_or_text(rel_path, label=None):
    rel_path = str(rel_path).replace("\\", "/").strip()
    if not rel_path:
        return "N/A"

    shown = label if label is not None else rel_path
    return f"<a href=\"{escape_html(rel_path)}\">{escape_html(shown)}</a>"


def image_tag(image_rel_path, alt_text="chart"):
    image_rel_path = str(image_rel_path).replace("\\", "/").strip()

    if not image_rel_path:
        return "<p>No image available.</p>"

    return (
        f"<img src=\"{escape_html(image_rel_path)}\" "
        f"alt=\"{escape_html(alt_text)}\" "
        f"style=\"max-width: 100%; height: auto; border: 1px solid #ddd; margin-bottom: 12px;\"/>"
    )


def build_cards_html(summary_df, registry, copied_lookup):
    cards = []

    for _, row in summary_df.iterrows():
        atlas_name = str(row["atlas_name"])
        meta = registry[atlas_name]

        atlas_report_rel = copied_lookup.get(("atlas_report", atlas_name), "")
        qc_report_rel = copied_lookup.get(("qc_report", atlas_name), "")

        cards.append(
            (
                "<div style='border: 1px solid #ccc; padding: 12px; margin: 8px; border-radius: 8px; "
                "display: inline-block; min-width: 260px; vertical-align: top; background: #fafafa;'>"
                f"<h3 style='margin-top: 0;'>{escape_html(meta['display_name'])} ({escape_html(meta['short_name'])})</h3>"
                f"<p><strong>Rows:</strong> {int(row['rows'])}</p>"
                f"<p><strong>Modalities:</strong> {int(row['modality_count'])}</p>"
                f"<p><strong>Unknown modality rows:</strong> {int(row['unknown_modality_rows'])}</p>"
                f"<p><strong>Missing source URL rows:</strong> {int(row['missing_source_url_rows'])}</p>"
                f"<p><strong>Atlas report:</strong> {link_or_text(atlas_report_rel, 'Open report')}</p>"
                f"<p><strong>Atlas QC report:</strong> {link_or_text(qc_report_rel, 'Open QC report')}</p>"
                "</div>"
            )
        )

    return "\n".join(cards)


def build_portfolio_index_html(summary_df, benchmark_df, registry, copied_lookup):
    dashboard_rel = copied_lookup.get(("dashboard", "dashboard"), "")
    rankings_bar_rel = copied_lookup.get(("asset", "cross_atlas_rankings_bar.png"), "")
    rows_bar_rel = copied_lookup.get(("asset", "cross_atlas_rows_bar.png"), "")
    source_bar_rel = copied_lookup.get(("asset", "cross_atlas_source_stacked_bar.png"), "")
    modality_heatmap_rel = copied_lookup.get(("asset", "cross_atlas_modality_heatmap.png"), "")

    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        "<title>Atlas Portfolio Bundle</title>",
        "<style>",
        "body { font-family: Arial, sans-serif; margin: 20px; }",
        "table { border-collapse: collapse; margin-bottom: 20px; }",
        "th, td { border: 1px solid #ccc; padding: 6px 8px; text-align: left; }",
        "th { background: #f0f0f0; }",
        "a { color: #0645ad; text-decoration: none; }",
        "a:hover { text-decoration: underline; }",
        "</style>",
        "</head>",
        "<body>",
        "<h1>Atlas Portfolio Bundle</h1>",
        "<p>This portfolio bundle packages the cross-atlas dashboard and the current atlas-level artifacts into one shareable bundle.</p>",
        "<p><strong>Scope:</strong> This is a metadata-only bundle.</p>",
        f"<p><strong>Dashboard:</strong> {link_or_text(dashboard_rel, 'Open dashboard')}</p>",
        "<h2>Atlas portfolio cards</h2>",
        build_cards_html(summary_df, registry, copied_lookup),
        "<h2>Benchmark table</h2>",
        dataframe_to_html_table(benchmark_df),
    ]

    if rankings_bar_rel:
        html_parts.append("<h2>Rankings chart</h2>")
        html_parts.append(image_tag(rankings_bar_rel, "Rankings chart"))
    if rows_bar_rel:
        html_parts.append("<h2>Rows by atlas</h2>")
        html_parts.append(image_tag(rows_bar_rel, "Rows by atlas"))
    if source_bar_rel:
        html_parts.append("<h2>Source coverage</h2>")
        html_parts.append(image_tag(source_bar_rel, "Source coverage"))
    if modality_heatmap_rel:
        html_parts.append("<h2>Modality heatmap</h2>")
        html_parts.append(image_tag(modality_heatmap_rel, "Modality heatmap"))

    html_parts.extend(["</body>", "</html>"])
    return "\n".join(html_parts)


def zip_directory(source_dir, zip_path):
    source_dir = Path(source_dir)
    zip_path = ensure_parent(zip_path)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in source_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(source_dir))


def generate_atlas_portfolio_bundle(
    display_registry_path=DEFAULT_DISPLAY_REGISTRY,
    dashboard_summary_path=DEFAULT_DASHBOARD_SUMMARY,
    rankings_path=DEFAULT_RANKINGS,
    dashboard_html_path=DEFAULT_DASHBOARD_HTML,
    reports_dir=DEFAULT_REPORTS_DIR,
    bundle_dir=DEFAULT_BUNDLE_DIR,
    zip_output_path=DEFAULT_ZIP_OUTPUT,
    atlas_names=None,
):
    summary_df = load_tsv(dashboard_summary_path)
    rankings_df = load_tsv(rankings_path) if Path(rankings_path).exists() else pd.DataFrame()

    summary_df["atlas_name"] = summary_df["atlas_name"].astype(str).str.strip().str.lower()
    summary_df = filter_atlases(summary_df, atlas_names=atlas_names)

    atlas_names_final = summary_df["atlas_name"].tolist()
    registry = normalize_registry(load_yaml_mapping(display_registry_path), atlas_names_final)

    benchmark_df = build_benchmark_df(summary_df, rankings_df, registry)

    bundle_dir = ensure_dir(bundle_dir)
    reports_out = ensure_dir(bundle_dir / "reports")
    assets_out = ensure_dir(bundle_dir / "assets")

    copied_lookup = {}

    dashboard_rel = safe_copy(dashboard_html_path, reports_out)
    if dashboard_rel:
        copied_lookup[("dashboard", "dashboard")] = f"reports/{dashboard_rel}"

    for _, row in summary_df.iterrows():
        atlas_name = str(row["atlas_name"])
        atlas_report = str(row.get("atlas_report_path", "")).strip()
        qc_report = str(row.get("qc_report_path", "")).strip()

        if atlas_report:
            rel = safe_copy(atlas_report, reports_out)
            if rel:
                copied_lookup[("atlas_report", atlas_name)] = f"reports/{rel}"

        if qc_report:
            rel = safe_copy(qc_report, reports_out)
            if rel:
                copied_lookup[("qc_report", atlas_name)] = f"reports/{rel}"

    report_files = collect_report_files(summary_df, reports_dir)
    for path in report_files:
        if not Path(path).exists():
            continue

        if Path(path).suffix.lower() in {".png"}:
            rel = safe_copy(path, assets_out)
            if rel:
                copied_lookup[("asset", Path(path).name)] = f"assets/{rel}"
        elif Path(path).name != Path(dashboard_html_path).name:
            safe_copy(path, reports_out)

    benchmark_path = bundle_dir / "atlas_benchmark_table.tsv"
    manifest_path = bundle_dir / "atlas_portfolio_manifest.tsv"
    index_html_path = bundle_dir / "index.html"

    benchmark_df.to_csv(benchmark_path, sep="\t", index=False)

    manifest_rows = []
    for _, row in summary_df.iterrows():
        atlas_name = str(row["atlas_name"])
        meta = registry[atlas_name]
        manifest_rows.append(
            {
                "atlas_name": atlas_name,
                "display_name": meta["display_name"],
                "short_name": meta["short_name"],
                "rows": int(row["rows"]),
                "atlas_report_bundle_path": copied_lookup.get(("atlas_report", atlas_name), ""),
                "atlas_qc_bundle_path": copied_lookup.get(("qc_report", atlas_name), ""),
            }
        )
    manifest_df = pd.DataFrame(manifest_rows)
    manifest_df.to_csv(manifest_path, sep="\t", index=False)

    index_html = build_portfolio_index_html(summary_df, benchmark_df, registry, copied_lookup)
    index_html_path.write_text(index_html, encoding="utf-8")

    zip_directory(bundle_dir, zip_output_path)

    return benchmark_df, index_html_path, zip_output_path


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Build a shareable atlas portfolio bundle from the current cross-atlas dashboard outputs."
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
        "--dashboard-summary",
        type=Path,
        default=DEFAULT_DASHBOARD_SUMMARY,
        help=f"Dashboard summary TSV. Default: {DEFAULT_DASHBOARD_SUMMARY}",
    )

    parser.add_argument(
        "--rankings",
        type=Path,
        default=DEFAULT_RANKINGS,
        help=f"Dashboard rankings TSV. Default: {DEFAULT_RANKINGS}",
    )

    parser.add_argument(
        "--dashboard-html",
        type=Path,
        default=DEFAULT_DASHBOARD_HTML,
        help=f"Dashboard HTML input. Default: {DEFAULT_DASHBOARD_HTML}",
    )

    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=DEFAULT_REPORTS_DIR,
        help=f"Reports directory. Default: {DEFAULT_REPORTS_DIR}",
    )

    parser.add_argument(
        "--bundle-dir",
        type=Path,
        default=DEFAULT_BUNDLE_DIR,
        help=f"Bundle directory output. Default: {DEFAULT_BUNDLE_DIR}",
    )

    parser.add_argument(
        "--zip-output",
        type=Path,
        default=DEFAULT_ZIP_OUTPUT,
        help=f"Zip output path. Default: {DEFAULT_ZIP_OUTPUT}",
    )

    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        benchmark_df, index_html_path, zip_output_path = generate_atlas_portfolio_bundle(
            display_registry_path=args.display_registry,
            dashboard_summary_path=args.dashboard_summary,
            rankings_path=args.rankings,
            dashboard_html_path=args.dashboard_html,
            reports_dir=args.reports_dir,
            bundle_dir=args.bundle_dir,
            zip_output_path=args.zip_output,
            atlas_names=args.atlases,
        )
    except Exception as exc:
        print(f"ERROR: Failed to build atlas portfolio bundle: {exc}", file=sys.stderr)
        return 1

    print("Atlas portfolio bundle complete.")
    print(f"Atlas count: {len(benchmark_df)}")
    print(f"Index HTML: {index_html_path}")
    print(f"Zip bundle: {zip_output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
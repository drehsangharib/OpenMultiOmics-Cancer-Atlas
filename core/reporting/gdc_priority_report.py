#!/usr/bin/env python3

"""
GDC Project Priority HTML Report

Project:
    OpenMultiOmics-Cancer-Atlas

Purpose:
    Generate a local HTML report summarizing GDC project metadata, modality
    availability, project priority rankings, and optional generated visuals.

Inputs:
    outputs/dataset_inventory/gdc_project_inventory.tsv
    outputs/dataset_inventory/gdc_project_modality_matrix.tsv
    outputs/ranked_datasets/gdc_project_priority_ranking.tsv
    outputs/figures/*.png, optional

Output:
    outputs/reports/gdc_project_priority_report.html

Example:
    python -m core.reporting.gdc_priority_report
"""

from __future__ import annotations

import argparse
import base64
import html
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


DEFAULT_PROJECT_INVENTORY = Path("outputs/dataset_inventory/gdc_project_inventory.tsv")
DEFAULT_MODALITY_MATRIX = Path("outputs/dataset_inventory/gdc_project_modality_matrix.tsv")
DEFAULT_PRIORITY_RANKING = Path("outputs/ranked_datasets/gdc_project_priority_ranking.tsv")
DEFAULT_FIGURES_DIR = Path("outputs/figures")
DEFAULT_OUTPUT = Path("outputs/reports/gdc_project_priority_report.html")


PROJECT_REQUIRED_COLUMNS = [
    "project_id",
    "project_name",
    "program_name",
    "primary_site",
    "disease_type",
    "case_count",
    "file_count",
]


MODALITY_REQUIRED_COLUMNS = [
    "project_id",
    "has_transcriptomics",
    "has_methylation",
    "has_snv",
    "has_cnv",
    "has_structural_variation",
    "has_clinical",
    "has_biospecimen",
    "has_proteomics",
    "has_slide_images",
    "has_sequencing_reads",
    "total_file_count",
    "open_file_count",
    "controlled_file_count",
]


RANKING_REQUIRED_COLUMNS = [
    "rank",
    "project_id",
    "project_name",
    "program_name",
    "primary_site",
    "case_count",
    "priority_score",
    "priority_label",
    "multiomics_modality_count",
    "priority_rationale",
]


MODALITY_FLAG_COLUMNS = [
    "has_transcriptomics",
    "has_methylation",
    "has_snv",
    "has_cnv",
    "has_structural_variation",
    "has_clinical",
    "has_biospecimen",
    "has_proteomics",
    "has_slide_images",
    "has_sequencing_reads",
]


MODALITY_DISPLAY_NAMES = {
    "has_transcriptomics": "Transcriptomics",
    "has_methylation": "DNA methylation",
    "has_snv": "SNV",
    "has_cnv": "CNV",
    "has_structural_variation": "Structural variation",
    "has_clinical": "Clinical",
    "has_biospecimen": "Biospecimen",
    "has_proteomics": "Proteomics",
    "has_slide_images": "Slide images",
    "has_sequencing_reads": "Sequencing reads",
}


FIGURE_CONFIGS = [
    {
        "key": "pipeline_schematic",
        "title": "GDC metadata pipeline schematic",
        "filename": "gdc_pipeline_schematic.png",
        "caption": (
            "Overview of the current GDC metadata workflow from public API "
            "metadata harvesting to reporting and visual outputs."
        ),
    },
    {
        "key": "priority_label_distribution",
        "title": "Project priority label distribution",
        "filename": "gdc_priority_label_distribution.png",
        "caption": "Number of GDC projects assigned to each atlas-priority label.",
    },
    {
        "key": "modality_coverage",
        "title": "Modality coverage across GDC projects",
        "filename": "gdc_modality_coverage_barplot.png",
        "caption": "Number of GDC projects with each broad data modality available.",
    },
    {
        "key": "project_modality_heatmap",
        "title": "Top-ranked project × modality heatmap",
        "filename": "gdc_project_modality_heatmap_top30.png",
        "caption": (
            "Availability matrix for major data modalities among the top-ranked "
            "GDC projects."
        ),
    },
]


def parse_bool(value: object) -> bool:
    """
    Convert bool-like values into Python booleans.
    """
    if isinstance(value, bool):
        return value

    if pd.isna(value):
        return False

    text = str(value).strip().lower()

    if text in {"true", "1", "yes", "y"}:
        return True

    return False


def parse_int(value: object) -> int:
    """
    Convert values to integers; invalid values become zero.
    """
    try:
        if pd.isna(value):
            return 0
        return int(float(value))
    except Exception:
        return 0


def validate_columns(df: pd.DataFrame, required_columns: List[str], name: str) -> None:
    """
    Validate required columns in a DataFrame.
    """
    missing = [col for col in required_columns if col not in df.columns]

    if missing:
        raise ValueError(f"Missing required columns in {name}: " + ", ".join(missing))


def read_tsv(path: Path, required_columns: List[str], name: str) -> pd.DataFrame:
    """
    Read and validate a TSV file.
    """
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    df = pd.read_csv(path, sep="\t")
    validate_columns(df, required_columns, name=name)

    return df


def clean_project_inventory(project_df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean project inventory table for reporting.
    """
    out = project_df.copy()

    for col in [
        "project_id",
        "project_name",
        "program_name",
        "primary_site",
        "disease_type",
    ]:
        out[col] = out[col].fillna("").astype(str)

    out["case_count"] = out["case_count"].apply(parse_int)
    out["file_count"] = out["file_count"].apply(parse_int)

    return out


def clean_modality_matrix(modality_df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean modality matrix table for reporting.
    """
    out = modality_df.copy()
    out["project_id"] = out["project_id"].fillna("").astype(str)

    for col in MODALITY_FLAG_COLUMNS:
        out[col] = out[col].apply(parse_bool)

    for col in ["total_file_count", "open_file_count", "controlled_file_count"]:
        out[col] = out[col].apply(parse_int)

    return out


def clean_priority_ranking(ranking_df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean priority ranking table for reporting.
    """
    out = ranking_df.copy()

    for col in [
        "project_id",
        "project_name",
        "program_name",
        "primary_site",
        "priority_label",
        "priority_rationale",
    ]:
        out[col] = out[col].fillna("").astype(str)

    out["rank"] = out["rank"].apply(parse_int)
    out["case_count"] = out["case_count"].apply(parse_int)
    out["priority_score"] = out["priority_score"].apply(parse_int)
    out["multiomics_modality_count"] = out["multiomics_modality_count"].apply(parse_int)

    return out.sort_values("rank", ascending=True).reset_index(drop=True)


def summarize_programs(project_df: pd.DataFrame) -> pd.DataFrame:
    """
    Summarize project counts by GDC program.
    """
    if project_df.empty:
        return pd.DataFrame(
            columns=["program_name", "project_count", "case_count", "file_count"]
        )

    summary = (
        project_df.groupby("program_name", dropna=False)
        .agg(
            project_count=("project_id", "nunique"),
            case_count=("case_count", "sum"),
            file_count=("file_count", "sum"),
        )
        .reset_index()
        .sort_values(["project_count", "case_count"], ascending=[False, False])
    )

    return summary


def summarize_priority_labels(ranking_df: pd.DataFrame) -> pd.DataFrame:
    """
    Summarize count of projects by priority label.
    """
    if ranking_df.empty:
        return pd.DataFrame(columns=["priority_label", "project_count"])

    order = ["excellent", "high", "medium", "low", "very_low"]

    summary = (
        ranking_df["priority_label"]
        .value_counts()
        .rename_axis("priority_label")
        .reset_index(name="project_count")
    )

    summary["priority_label"] = pd.Categorical(
        summary["priority_label"],
        categories=order,
        ordered=True,
    )

    return summary.sort_values("priority_label").reset_index(drop=True)


def summarize_modality_coverage(modality_df: pd.DataFrame) -> pd.DataFrame:
    """
    Summarize modality coverage across projects.
    """
    rows: List[Dict[str, object]] = []

    total_projects = len(modality_df)

    for col in MODALITY_FLAG_COLUMNS:
        count = int(modality_df[col].sum()) if col in modality_df.columns else 0
        fraction = count / total_projects if total_projects > 0 else 0

        rows.append(
            {
                "modality": MODALITY_DISPLAY_NAMES.get(col, col),
                "project_count": count,
                "project_fraction": round(fraction, 3),
            }
        )

    return pd.DataFrame(rows)


def dataframe_to_html_table(
    df: pd.DataFrame,
    max_rows: Optional[int] = None,
    columns: Optional[List[str]] = None,
    css_class: str = "data-table",
) -> str:
    """
    Convert a DataFrame into a simple escaped HTML table.
    """
    if columns is not None:
        display_cols = [col for col in columns if col in df.columns]
        display_df = df.loc[:, display_cols].copy()
    else:
        display_df = df.copy()

    if max_rows is not None:
        display_df = display_df.head(max_rows)

    if display_df.empty:
        return "<p><em>No records available.</em></p>"

    escaped = display_df.copy()

    for col in escaped.columns:
        escaped[col] = escaped[col].apply(lambda x: html.escape(str(x)))

    return escaped.to_html(index=False, escape=False, classes=css_class)


def build_bar_list(
    df: pd.DataFrame,
    label_col: str,
    value_col: str,
    max_value: Optional[int] = None,
) -> str:
    """
    Build a lightweight HTML bar chart using divs.
    """
    if df.empty:
        return "<p><em>No summary available.</em></p>"

    local = df.copy()
    local[value_col] = local[value_col].apply(parse_int)

    if max_value is None:
        max_value = int(local[value_col].max()) if not local.empty else 1

    if max_value <= 0:
        max_value = 1

    bars = []

    for _, row in local.iterrows():
        label = html.escape(str(row[label_col]))
        value = parse_int(row[value_col])
        width = max(2, int((value / max_value) * 100))

        bars.append(
            f"""
            <div class="bar-row">
                <div class="bar-label">{label}</div>
                <div class="bar-track">
                    <div class="bar-fill" style="width:{width}%"></div>
                </div>
                <div class="bar-value">{value}</div>
            </div>
            """
        )

    return "\n".join(bars)


def image_file_to_data_uri(image_path: Path) -> Optional[str]:
    """
    Convert a local PNG image file to a base64 data URI.

    Returns None if the file does not exist.
    """
    if not image_path.exists():
        return None

    encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def build_single_figure_html(
    title: str,
    image_path: Path,
    caption: str,
    embed_images: bool = True,
) -> str:
    """
    Build HTML for one figure.

    If embed_images=True, the image is embedded as a base64 data URI.
    If embed_images=False, a relative/local image path is used.
    """
    title_escaped = html.escape(title)
    caption_escaped = html.escape(caption)
    alt_escaped = html.escape(title, quote=True)

    if not image_path.exists():
        return f"""
        <div class="figure-card missing-figure">
            <h3>{title_escaped}</h3>
            <p><em>Figure not found: {html.escape(str(image_path))}</em></p>
            <p class="figure-caption">{caption_escaped}</p>
        </div>
        """

    if embed_images:
        data_uri = image_file_to_data_uri(image_path)
        src = data_uri if data_uri is not None else str(image_path)
    else:
        src = str(image_path)

    src_escaped = html.escape(src, quote=True)

    return f"""
    <div class="figure-card">
        <h3>{title_escaped}</h3>
        <img src="{src_escaped}" alt="{alt_escaped}" class="report-figure">
        <p class="figure-caption">{caption_escaped}</p>
    </div>
    """


def build_visual_sections(
    figures_dir: Path = DEFAULT_FIGURES_DIR,
    embed_images: bool = True,
) -> str:
    """
    Build all visual sections for the HTML report.
    """
    figure_blocks = []

    for fig_config in FIGURE_CONFIGS:
        figure_path = figures_dir / fig_config["filename"]
        figure_blocks.append(
            build_single_figure_html(
                title=fig_config["title"],
                image_path=figure_path,
                caption=fig_config["caption"],
                embed_images=embed_images,
            )
        )

    return "\n".join(figure_blocks)


def build_report_html(
    project_df: pd.DataFrame,
    modality_df: pd.DataFrame,
    ranking_df: pd.DataFrame,
    figures_dir: Path = DEFAULT_FIGURES_DIR,
    embed_images: bool = True,
) -> str:
    """
    Build the full HTML report.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    program_summary = summarize_programs(project_df)
    priority_summary = summarize_priority_labels(ranking_df)
    modality_summary = summarize_modality_coverage(modality_df)

    total_projects = len(project_df)
    total_cases = int(project_df["case_count"].sum()) if not project_df.empty else 0
    total_files = int(project_df["file_count"].sum()) if not project_df.empty else 0

    excellent_count = (
        int((ranking_df["priority_label"] == "excellent").sum())
        if not ranking_df.empty
        else 0
    )

    top_projects_table = dataframe_to_html_table(
        ranking_df,
        max_rows=20,
        columns=[
            "rank",
            "project_id",
            "program_name",
            "primary_site",
            "case_count",
            "priority_score",
            "priority_label",
            "multiomics_modality_count",
            "priority_rationale",
        ],
    )

    program_table = dataframe_to_html_table(
        program_summary,
        max_rows=30,
        columns=["program_name", "project_count", "case_count", "file_count"],
    )

    priority_table = dataframe_to_html_table(
        priority_summary,
        columns=["priority_label", "project_count"],
    )

    modality_table = dataframe_to_html_table(
        modality_summary,
        columns=["modality", "project_count", "project_fraction"],
    )

    priority_bars = build_bar_list(
        priority_summary,
        label_col="priority_label",
        value_col="project_count",
    )

    modality_bars = build_bar_list(
        modality_summary,
        label_col="modality",
        value_col="project_count",
    )

    visual_sections = build_visual_sections(
        figures_dir=figures_dir,
        embed_images=embed_images,
    )

    html_report = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>OpenMultiOmics-Cancer-Atlas | GDC Project Priority Report</title>
<style>
    body {{
        font-family: Arial, sans-serif;
        margin: 40px;
        color: #222;
        line-height: 1.5;
        background: #ffffff;
    }}

    h1, h2, h3 {{
        color: #1f4e79;
    }}

    .subtitle {{
        color: #555;
        font-size: 15px;
    }}

    .cards {{
        display: grid;
        grid-template-columns: repeat(4, minmax(160px, 1fr));
        gap: 16px;
        margin: 24px 0;
    }}

    .card {{
        border: 1px solid #d7e3ef;
        border-radius: 12px;
        padding: 16px;
        background: #f8fbff;
    }}

    .card-label {{
        color: #555;
        font-size: 13px;
        margin-bottom: 8px;
    }}

    .card-value {{
        color: #1f4e79;
        font-size: 26px;
        font-weight: bold;
    }}

    .section {{
        margin-top: 34px;
        margin-bottom: 20px;
    }}

    table.data-table {{
        border-collapse: collapse;
        width: 100%;
        font-size: 12px;
        margin-top: 12px;
    }}

    table.data-table th {{
        background: #e8f1fa;
        color: #1f4e79;
        border: 1px solid #c8d6e5;
        padding: 7px;
        text-align: left;
    }}

    table.data-table td {{
        border: 1px solid #d8d8d8;
        padding: 6px;
        vertical-align: top;
    }}

    .bar-row {{
        display: grid;
        grid-template-columns: 180px 1fr 70px;
        gap: 10px;
        align-items: center;
        margin: 8px 0;
    }}

    .bar-label {{
        font-size: 13px;
    }}

    .bar-track {{
        background: #edf2f7;
        border-radius: 999px;
        height: 14px;
        overflow: hidden;
    }}

    .bar-fill {{
        background: #2b6cb0;
        height: 14px;
        border-radius: 999px;
    }}

    .bar-value {{
        font-size: 13px;
        text-align: right;
    }}

    .note {{
        border-left: 4px solid #2b6cb0;
        padding: 12px 16px;
        background: #f6f9fc;
        margin: 18px 0;
    }}

    .figure-grid {{
        display: grid;
        grid-template-columns: 1fr;
        gap: 22px;
        margin-top: 16px;
    }}

    .figure-card {{
        border: 1px solid #d7e3ef;
        border-radius: 12px;
        padding: 16px;
        background: #ffffff;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}

    .missing-figure {{
        background: #fff8f0;
    }}

    .report-figure {{
        width: 100%;
        max-width: 1200px;
        display: block;
        margin: 8px auto 4px auto;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
    }}

    .figure-caption {{
        color: #555;
        font-size: 13px;
        margin-top: 8px;
    }}

    .footer {{
        margin-top: 40px;
        font-size: 12px;
        color: #666;
    }}
</style>
</head>

<body>
<h1>OpenMultiOmics-Cancer-Atlas</h1>
<p class="subtitle">GDC Project Priority Report | Generated {html.escape(now)}</p>

<div class="note">
    This report summarizes public GDC project metadata, modality availability,
    project priority scores, and static visual outputs for cancer multi-omics
    atlas construction. Generated outputs are local analysis artifacts and are
    not committed by default.
</div>

<div class="cards">
    <div class="card">
        <div class="card-label">GDC projects</div>
        <div class="card-value">{total_projects}</div>
    </div>
    <div class="card">
        <div class="card-label">Total cases</div>
        <div class="card-value">{total_cases:,}</div>
    </div>
    <div class="card">
        <div class="card-label">Total files</div>
        <div class="card-value">{total_files:,}</div>
    </div>
    <div class="card">
        <div class="card-label">Excellent-priority projects</div>
        <div class="card-value">{excellent_count}</div>
    </div>
</div>

<div class="section">
<h2>Visual overview</h2>
<div class="figure-grid">
{visual_sections}
</div>
</div>

<div class="section">
<h2>Priority label distribution</h2>
{priority_bars}
{priority_table}
</div>

<div class="section">
<h2>Modality coverage across projects</h2>
{modality_bars}
{modality_table}
</div>

<div class="section">
<h2>Top-ranked projects</h2>
{top_projects_table}
</div>

<div class="section">
<h2>Program summary</h2>
{program_table}
</div>

<div class="section">
<h2>Interpretation notes</h2>
<ul>
    <li>Priority scores reflect public metadata availability, not biological quality or suitability for a specific hypothesis.</li>
    <li>Projects with transcriptomics, genomics, clinical metadata, and proteomics receive higher multi-omics priority.</li>
    <li>Controlled-access files are counted but not downloaded or processed by this report.</li>
    <li>Visuals are generated locally from public summary tables and embedded into this HTML report when available.</li>
</ul>
</div>

<div class="footer">
    OpenMultiOmics-Cancer-Atlas | Public-data-first cancer multi-omics atlas scaffold.
</div>

</body>
</html>
"""

    return html_report


def generate_gdc_priority_report(
    project_inventory_path: Path = DEFAULT_PROJECT_INVENTORY,
    modality_matrix_path: Path = DEFAULT_MODALITY_MATRIX,
    priority_ranking_path: Path = DEFAULT_PRIORITY_RANKING,
    figures_dir: Path = DEFAULT_FIGURES_DIR,
    output_path: Path = DEFAULT_OUTPUT,
    embed_images: bool = True,
) -> str:
    """
    Read inputs, generate HTML, write report, and return HTML string.
    """
    project_df = read_tsv(
        project_inventory_path,
        required_columns=PROJECT_REQUIRED_COLUMNS,
        name="project inventory",
    )
    modality_df = read_tsv(
        modality_matrix_path,
        required_columns=MODALITY_REQUIRED_COLUMNS,
        name="modality matrix",
    )
    ranking_df = read_tsv(
        priority_ranking_path,
        required_columns=RANKING_REQUIRED_COLUMNS,
        name="priority ranking",
    )

    project_df = clean_project_inventory(project_df)
    modality_df = clean_modality_matrix(modality_df)
    ranking_df = clean_priority_ranking(ranking_df)

    html_report = build_report_html(
        project_df=project_df,
        modality_df=modality_df,
        ranking_df=ranking_df,
        figures_dir=figures_dir,
        embed_images=embed_images,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_report, encoding="utf-8")

    return html_report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate an HTML report for GDC project priority ranking."
    )

    parser.add_argument(
        "--project-inventory",
        type=Path,
        default=DEFAULT_PROJECT_INVENTORY,
        help=f"Input GDC project inventory TSV. Default: {DEFAULT_PROJECT_INVENTORY}",
    )

    parser.add_argument(
        "--modality-matrix",
        type=Path,
        default=DEFAULT_MODALITY_MATRIX,
        help=f"Input GDC project modality matrix TSV. Default: {DEFAULT_MODALITY_MATRIX}",
    )

    parser.add_argument(
        "--priority-ranking",
        type=Path,
        default=DEFAULT_PRIORITY_RANKING,
        help=f"Input GDC priority ranking TSV. Default: {DEFAULT_PRIORITY_RANKING}",
    )

    parser.add_argument(
        "--figures-dir",
        type=Path,
        default=DEFAULT_FIGURES_DIR,
        help=f"Input figures directory. Default: {DEFAULT_FIGURES_DIR}",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output HTML report path. Default: {DEFAULT_OUTPUT}",
    )

    parser.add_argument(
        "--link-images",
        action="store_true",
        help="Link to local image paths instead of embedding images as base64.",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        html_report = generate_gdc_priority_report(
            project_inventory_path=args.project_inventory,
            modality_matrix_path=args.modality_matrix,
            priority_ranking_path=args.priority_ranking,
            figures_dir=args.figures_dir,
            output_path=args.output,
            embed_images=not args.link_images,
        )
    except Exception as exc:
        print(f"ERROR: Failed to generate GDC priority report: {exc}", file=sys.stderr)
        return 1

    print("GDC priority report complete.")
    print(f"Output: {args.output}")
    print(f"HTML characters: {len(html_report)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
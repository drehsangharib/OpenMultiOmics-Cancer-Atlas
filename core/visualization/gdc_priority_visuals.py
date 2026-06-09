#!/usr/bin/env python3

"""
GDC Priority Visual Outputs

Project:
    OpenMultiOmics-Cancer-Atlas

Purpose:
    Generate audience-friendly static visual summaries from GDC project priority
    ranking, project modality matrix, and optional GDC file-count summaries.

Inputs:
    outputs/ranked_datasets/gdc_project_priority_ranking.tsv
    outputs/dataset_inventory/gdc_project_modality_matrix.tsv
    outputs/dataset_inventory/gdc_file_counts_by_project.tsv, optional

Outputs:
    outputs/figures/gdc_priority_label_distribution.png
    outputs/figures/gdc_modality_coverage_barplot.png
    outputs/figures/gdc_project_modality_heatmap_top30.png
    outputs/figures/gdc_project_modality_heatmap_top30_binary.png
    outputs/figures/gdc_project_modality_heatmap_all_binary.png
    outputs/figures/gdc_project_modality_filecount_heatmap_top30.png
    outputs/figures/gdc_pipeline_schematic.png

Example:
    python -m core.visualization.gdc_priority_visuals
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import ListedColormap


DEFAULT_PRIORITY_RANKING = Path("outputs/ranked_datasets/gdc_project_priority_ranking.tsv")
DEFAULT_MODALITY_MATRIX = Path("outputs/dataset_inventory/gdc_project_modality_matrix.tsv")
DEFAULT_FILE_COUNTS = Path("outputs/dataset_inventory/gdc_file_counts_by_project.tsv")
DEFAULT_FIGURES_DIR = Path("outputs/figures")

PRIORITY_LABEL_ORDER = ["excellent", "high", "medium", "low", "very_low"]

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

MODALITY_FILECOUNT_COLUMNS = [
    "transcriptomics",
    "methylation",
    "snv",
    "cnv",
    "structural_variation",
    "clinical",
    "biospecimen",
    "proteomics",
    "slide_images",
    "sequencing_reads",
]

MODALITY_FILECOUNT_DISPLAY_NAMES = {
    "transcriptomics": "Transcriptomics",
    "methylation": "DNA methylation",
    "snv": "SNV",
    "cnv": "CNV",
    "structural_variation": "Structural variation",
    "clinical": "Clinical",
    "biospecimen": "Biospecimen",
    "proteomics": "Proteomics",
    "slide_images": "Slide images",
    "sequencing_reads": "Sequencing reads",
}

RANKING_REQUIRED_COLUMNS = [
    "rank",
    "project_id",
    "priority_score",
    "priority_label",
    "multiomics_modality_count",
]

MODALITY_REQUIRED_COLUMNS = ["project_id"] + MODALITY_FLAG_COLUMNS

FILE_COUNTS_REQUIRED_COLUMNS = [
    "project_id",
    "data_category",
    "data_type",
    "experimental_strategy",
    "workflow_type",
    "data_format",
    "access",
    "file_count",
]


def parse_bool(value: object) -> bool:
    """
    Convert common bool-like values to Python booleans.
    """
    if isinstance(value, bool):
        return value

    if pd.isna(value):
        return False

    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y"}


def parse_int(value: object) -> int:
    """
    Convert values to integer. Invalid values become zero.
    """
    try:
        if pd.isna(value):
            return 0
        return int(float(value))
    except Exception:
        return 0


def normalize_lower(value: object) -> str:
    """
    Normalize text for robust matching.
    """
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


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


def clean_priority_ranking(ranking_df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean priority ranking table.
    """
    out = ranking_df.copy()

    out["rank"] = out["rank"].apply(parse_int)
    out["project_id"] = out["project_id"].fillna("").astype(str)
    out["priority_score"] = out["priority_score"].apply(parse_int)
    out["priority_label"] = out["priority_label"].fillna("").astype(str)
    out["multiomics_modality_count"] = out["multiomics_modality_count"].apply(parse_int)

    return out.sort_values("rank", ascending=True).reset_index(drop=True)


def clean_modality_matrix(modality_df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean modality matrix table.
    """
    out = modality_df.copy()
    out["project_id"] = out["project_id"].fillna("").astype(str)

    for col in MODALITY_FLAG_COLUMNS:
        out[col] = out[col].apply(parse_bool)

    return out


def clean_file_counts(file_counts_df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean file-count table.
    """
    out = file_counts_df.copy()

    for col in [
        "project_id",
        "data_category",
        "data_type",
        "experimental_strategy",
        "workflow_type",
        "data_format",
        "access",
    ]:
        out[col] = out[col].fillna("").astype(str)

    out["file_count"] = out["file_count"].apply(parse_int)

    return out


def summarize_priority_labels(ranking_df: pd.DataFrame) -> pd.DataFrame:
    """
    Count projects by priority label.
    """
    counts = (
        ranking_df["priority_label"]
        .value_counts()
        .reindex(PRIORITY_LABEL_ORDER, fill_value=0)
        .reset_index()
    )
    counts.columns = ["priority_label", "project_count"]
    return counts


def summarize_modality_coverage(modality_df: pd.DataFrame) -> pd.DataFrame:
    """
    Count projects with each modality available.
    """
    rows: List[Dict[str, object]] = []

    for col in MODALITY_FLAG_COLUMNS:
        rows.append(
            {
                "modality": MODALITY_DISPLAY_NAMES[col],
                "project_count": int(modality_df[col].sum()),
            }
        )

    out = pd.DataFrame(rows)
    out = out.sort_values("project_count", ascending=True).reset_index(drop=True)
    return out


def build_top_project_heatmap_matrix(
    ranking_df: pd.DataFrame,
    modality_df: pd.DataFrame,
    top_n: int = 30,
) -> pd.DataFrame:
    """
    Build a project × modality binary matrix for top-ranked projects.
    """
    top_projects = ranking_df.sort_values("rank", ascending=True).head(top_n)

    merged = top_projects[["project_id", "rank"]].merge(
        modality_df[["project_id"] + MODALITY_FLAG_COLUMNS],
        on="project_id",
        how="left",
    )

    merged = merged.sort_values("rank", ascending=True)

    heatmap_df = merged.set_index("project_id")[MODALITY_FLAG_COLUMNS].copy()
    heatmap_df = heatmap_df.fillna(False)

    heatmap_df.columns = [MODALITY_DISPLAY_NAMES[col] for col in heatmap_df.columns]
    heatmap_df = heatmap_df.astype(int)

    return heatmap_df


def build_all_project_heatmap_matrix(
    ranking_df: pd.DataFrame,
    modality_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build a project × modality binary matrix for all ranked projects.

    Projects are sorted by multi-omics richness, priority score, and rank.
    """
    ranked_projects = ranking_df.sort_values(
        by=["multiomics_modality_count", "priority_score", "rank"],
        ascending=[False, False, True],
        kind="stable",
    )

    merged = ranked_projects[["project_id", "rank"]].merge(
        modality_df[["project_id"] + MODALITY_FLAG_COLUMNS],
        on="project_id",
        how="left",
    )

    heatmap_df = merged.set_index("project_id")[MODALITY_FLAG_COLUMNS].copy()
    heatmap_df = heatmap_df.fillna(False)

    heatmap_df.columns = [MODALITY_DISPLAY_NAMES[col] for col in heatmap_df.columns]
    heatmap_df = heatmap_df.astype(int)

    return heatmap_df


def classify_file_count_modality(row: pd.Series) -> Optional[str]:
    """
    Classify a file-count row into one broad modality.

    The mapping is intentionally aligned with gdc_project_modality_matrix.py.
    """
    data_category = normalize_lower(row.get("data_category", ""))
    data_type = normalize_lower(row.get("data_type", ""))
    experimental_strategy = normalize_lower(row.get("experimental_strategy", ""))

    if data_category == "transcriptome profiling":
        return "transcriptomics"

    if data_category == "dna methylation":
        return "methylation"

    if data_category == "simple nucleotide variation":
        return "snv"

    if data_category == "copy number variation":
        return "cnv"

    if data_category in {"structural variation", "somatic structural variation"}:
        return "structural_variation"

    if data_category == "clinical":
        return "clinical"

    if data_category == "biospecimen":
        if data_type == "slide image":
            return "slide_images"
        return "biospecimen"

    if data_category == "proteome profiling":
        return "proteomics"

    if data_category == "sequencing reads":
        return "sequencing_reads"

    if experimental_strategy in {"rna-seq", "mirna-seq"}:
        return "transcriptomics"

    if experimental_strategy == "methylation array":
        return "methylation"

    if experimental_strategy in {"wxs", "wgs"} and "mutation" in data_type:
        return "snv"

    return None


def build_filecount_modality_matrix(
    ranking_df: pd.DataFrame,
    file_counts_df: pd.DataFrame,
    top_n: int = 30,
) -> pd.DataFrame:
    """
    Build a project × modality quantitative matrix using file counts.

    Values are raw file counts. The plotting function applies log10(count + 1).
    """
    df = file_counts_df.copy()
    df["modality"] = df.apply(classify_file_count_modality, axis=1)
    df = df[df["modality"].notna()].copy()

    if df.empty:
        return pd.DataFrame(columns=list(MODALITY_FILECOUNT_DISPLAY_NAMES.values()))

    grouped = (
        df.groupby(["project_id", "modality"], dropna=False)["file_count"]
        .sum()
        .reset_index()
    )

    top_projects = ranking_df.sort_values("rank", ascending=True).head(top_n)
    project_order = top_projects["project_id"].tolist()

    pivot = grouped.pivot_table(
        index="project_id",
        columns="modality",
        values="file_count",
        aggfunc="sum",
        fill_value=0,
    )

    for modality in MODALITY_FILECOUNT_COLUMNS:
        if modality not in pivot.columns:
            pivot[modality] = 0

    existing_project_order = [project for project in project_order if project in pivot.index]
    pivot = pivot.loc[existing_project_order, MODALITY_FILECOUNT_COLUMNS]

    pivot = pivot.reindex(existing_project_order).fillna(0).astype(int)
    pivot.columns = [MODALITY_FILECOUNT_DISPLAY_NAMES[col] for col in pivot.columns]

    return pivot


def save_figure(fig: plt.Figure, output_path: Path, dpi: int = 180) -> None:
    """
    Save a matplotlib figure and close it.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def plot_priority_label_distribution(
    ranking_df: pd.DataFrame,
    output_path: Path,
) -> Path:
    """
    Plot count of projects by priority label.
    """
    summary = summarize_priority_labels(ranking_df)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(summary["priority_label"], summary["project_count"])

    ax.set_title("GDC Project Priority Label Distribution")
    ax.set_xlabel("Priority label")
    ax.set_ylabel("Number of projects")

    for index, value in enumerate(summary["project_count"]):
        ax.text(index, value, str(value), ha="center", va="bottom", fontsize=9)

    save_figure(fig, output_path)
    return output_path


def plot_modality_coverage(
    modality_df: pd.DataFrame,
    output_path: Path,
) -> Path:
    """
    Plot number of GDC projects with each modality available.
    """
    summary = summarize_modality_coverage(modality_df)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(summary["modality"], summary["project_count"])

    ax.set_title("GDC Project Modality Coverage")
    ax.set_xlabel("Number of projects")
    ax.set_ylabel("Modality")

    for index, value in enumerate(summary["project_count"]):
        ax.text(value, index, f" {value}", va="center", fontsize=9)

    save_figure(fig, output_path)
    return output_path


def plot_binary_modality_heatmap(
    matrix: pd.DataFrame,
    output_path: Path,
    title: str,
    show_project_labels: bool = True,
    show_checkmarks: bool = True,
) -> Path:
    """
    Plot a clean binary modality heatmap with a clear absent/present legend.
    """
    cmap = ListedColormap(["#f1f5f9", "#2563eb"])

    fig_width = max(8, len(matrix.columns) * 0.9)
    fig_height = max(6, len(matrix.index) * 0.26)

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.imshow(
        matrix.values,
        aspect="auto",
        interpolation="nearest",
        cmap=cmap,
        vmin=0,
        vmax=1,
    )

    ax.set_title(title)
    ax.set_xlabel("Modality")
    ax.set_ylabel("Project")

    ax.set_xticks(range(len(matrix.columns)))
    ax.set_xticklabels(matrix.columns, rotation=45, ha="right")

    ax.set_yticks(range(len(matrix.index)))
    if show_project_labels:
        ax.set_yticklabels(matrix.index)
    else:
        ax.set_yticklabels([])

    if show_checkmarks:
        for row_idx in range(matrix.shape[0]):
            for col_idx in range(matrix.shape[1]):
                value = matrix.values[row_idx, col_idx]
                ax.text(
                    col_idx,
                    row_idx,
                    "✓" if value == 1 else "",
                    ha="center",
                    va="center",
                    fontsize=7,
                    color="white" if value == 1 else "#334155",
                )

    ax.text(
        1.01,
        0.95,
        "Blue = available\nGray = not available",
        transform=ax.transAxes,
        va="top",
        fontsize=9,
        bbox={
            "boxstyle": "round,pad=0.4",
            "facecolor": "white",
            "edgecolor": "#cbd5e1",
        },
    )

    ax.set_xticks([x - 0.5 for x in range(1, len(matrix.columns))], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, len(matrix.index))], minor=True)
    ax.grid(which="minor", color="white", linestyle="-", linewidth=0.8)
    ax.tick_params(which="minor", bottom=False, left=False)

    save_figure(fig, output_path)
    return output_path


def plot_project_modality_heatmap(
    ranking_df: pd.DataFrame,
    modality_df: pd.DataFrame,
    output_path: Path,
    top_n: int = 30,
) -> Path:
    """
    Backward-compatible top-ranked binary modality heatmap.

    This replaces the older continuous-looking heatmap with a clear binary design.
    """
    matrix = build_top_project_heatmap_matrix(
        ranking_df=ranking_df,
        modality_df=modality_df,
        top_n=top_n,
    )

    return plot_binary_modality_heatmap(
        matrix=matrix,
        output_path=output_path,
        title=f"Top {len(matrix)} GDC Projects × Modality Availability",
        show_project_labels=True,
        show_checkmarks=True,
    )


def plot_all_project_modality_heatmap(
    ranking_df: pd.DataFrame,
    modality_df: pd.DataFrame,
    output_path: Path,
) -> Path:
    """
    Plot binary modality availability for all ranked projects.
    """
    matrix = build_all_project_heatmap_matrix(
        ranking_df=ranking_df,
        modality_df=modality_df,
    )

    return plot_binary_modality_heatmap(
        matrix=matrix,
        output_path=output_path,
        title=f"All {len(matrix)} GDC Projects × Modality Availability",
        show_project_labels=True,
        show_checkmarks=False,
    )


def plot_filecount_modality_heatmap(
    ranking_df: pd.DataFrame,
    file_counts_df: pd.DataFrame,
    output_path: Path,
    top_n: int = 30,
) -> Path:
    """
    Plot top-ranked projects by modality file counts using log10(file_count + 1).
    """
    matrix = build_filecount_modality_matrix(
        ranking_df=ranking_df,
        file_counts_df=file_counts_df,
        top_n=top_n,
    )

    log_matrix = matrix.map(lambda x: math.log10(parse_int(x) + 1))

    fig_width = max(8, len(log_matrix.columns) * 0.9)
    fig_height = max(6, len(log_matrix.index) * 0.30)

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    image = ax.imshow(log_matrix.values, aspect="auto", interpolation="nearest")

    ax.set_title(f"Top {len(log_matrix)} GDC Projects × Modality File Counts")
    ax.set_xlabel("Modality")
    ax.set_ylabel("Project")

    ax.set_xticks(range(len(log_matrix.columns)))
    ax.set_xticklabels(log_matrix.columns, rotation=45, ha="right")

    ax.set_yticks(range(len(log_matrix.index)))
    ax.set_yticklabels(log_matrix.index)

    for row_idx in range(matrix.shape[0]):
        for col_idx in range(matrix.shape[1]):
            raw_value = parse_int(matrix.values[row_idx, col_idx])
            label = "" if raw_value == 0 else str(raw_value)
            ax.text(
                col_idx,
                row_idx,
                label,
                ha="center",
                va="center",
                fontsize=6,
                color="white" if log_matrix.values[row_idx, col_idx] > 2.5 else "black",
            )

    fig.colorbar(image, ax=ax, fraction=0.025, pad=0.02, label="log10(file count + 1)")

    save_figure(fig, output_path)
    return output_path


def plot_pipeline_schematic(output_path: Path) -> Path:
    """
    Plot a simple schematic of the current GDC metadata pipeline.
    """
    steps = [
        "GDC API\nprojects/files",
        "Project\ninventory",
        "File counts\nby project",
        "Project × modality\nmatrix",
        "Priority\nranking",
        "HTML report\n+ visuals",
    ]

    fig, ax = plt.subplots(figsize=(12, 3.2))
    ax.axis("off")

    x_positions = [i for i in range(len(steps))]
    y = 0.5

    for idx, (x, label) in enumerate(zip(x_positions, steps)):
        ax.text(
            x,
            y,
            label,
            ha="center",
            va="center",
            fontsize=10,
            bbox={
                "boxstyle": "round,pad=0.5",
                "facecolor": "#f8fbff",
                "edgecolor": "#2b6cb0",
                "linewidth": 1.5,
            },
        )

        if idx < len(steps) - 1:
            ax.annotate(
                "",
                xy=(x + 0.72, y),
                xytext=(x + 0.28, y),
                arrowprops={"arrowstyle": "->", "linewidth": 1.5},
            )

    ax.set_xlim(-0.7, len(steps) - 0.3)
    ax.set_ylim(0, 1)

    ax.set_title("OpenMultiOmics-Cancer-Atlas: GDC Metadata Pipeline", fontsize=13)

    save_figure(fig, output_path)
    return output_path


def generate_gdc_priority_visuals(
    priority_ranking_path: Path = DEFAULT_PRIORITY_RANKING,
    modality_matrix_path: Path = DEFAULT_MODALITY_MATRIX,
    file_counts_path: Path = DEFAULT_FILE_COUNTS,
    figures_dir: Path = DEFAULT_FIGURES_DIR,
    top_n: int = 30,
) -> Dict[str, Path]:
    """
    Generate all GDC priority visual outputs.
    """
    ranking_df = read_tsv(
        priority_ranking_path,
        required_columns=RANKING_REQUIRED_COLUMNS,
        name="priority ranking",
    )
    modality_df = read_tsv(
        modality_matrix_path,
        required_columns=MODALITY_REQUIRED_COLUMNS,
        name="modality matrix",
    )

    ranking_df = clean_priority_ranking(ranking_df)
    modality_df = clean_modality_matrix(modality_df)

    figures_dir.mkdir(parents=True, exist_ok=True)

    outputs: Dict[str, Path] = {
        "priority_label_distribution": figures_dir
        / "gdc_priority_label_distribution.png",
        "modality_coverage": figures_dir / "gdc_modality_coverage_barplot.png",
        "project_modality_heatmap": figures_dir
        / f"gdc_project_modality_heatmap_top{top_n}.png",
        "pipeline_schematic": figures_dir / "gdc_pipeline_schematic.png",
        "project_modality_heatmap_top_binary": figures_dir
        / f"gdc_project_modality_heatmap_top{top_n}_binary.png",
        "project_modality_heatmap_all_binary": figures_dir
        / "gdc_project_modality_heatmap_all_binary.png",
    }

    plot_priority_label_distribution(
        ranking_df=ranking_df,
        output_path=outputs["priority_label_distribution"],
    )

    plot_modality_coverage(
        modality_df=modality_df,
        output_path=outputs["modality_coverage"],
    )

    plot_project_modality_heatmap(
        ranking_df=ranking_df,
        modality_df=modality_df,
        output_path=outputs["project_modality_heatmap"],
        top_n=top_n,
    )

    plot_pipeline_schematic(
        output_path=outputs["pipeline_schematic"],
    )

    plot_project_modality_heatmap(
        ranking_df=ranking_df,
        modality_df=modality_df,
        output_path=outputs["project_modality_heatmap_top_binary"],
        top_n=top_n,
    )

    plot_all_project_modality_heatmap(
        ranking_df=ranking_df,
        modality_df=modality_df,
        output_path=outputs["project_modality_heatmap_all_binary"],
    )

    if file_counts_path.exists():
        file_counts_df = read_tsv(
            file_counts_path,
            required_columns=FILE_COUNTS_REQUIRED_COLUMNS,
            name="file counts",
        )
        file_counts_df = clean_file_counts(file_counts_df)

        filecount_heatmap_path = (
            figures_dir / f"gdc_project_modality_filecount_heatmap_top{top_n}.png"
        )

        plot_filecount_modality_heatmap(
            ranking_df=ranking_df,
            file_counts_df=file_counts_df,
            output_path=filecount_heatmap_path,
            top_n=top_n,
        )

        outputs["project_modality_filecount_heatmap"] = filecount_heatmap_path

    return outputs


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate GDC project priority visual outputs."
    )

    parser.add_argument(
        "--priority-ranking",
        type=Path,
        default=DEFAULT_PRIORITY_RANKING,
        help=f"Input priority ranking TSV. Default: {DEFAULT_PRIORITY_RANKING}",
    )

    parser.add_argument(
        "--modality-matrix",
        type=Path,
        default=DEFAULT_MODALITY_MATRIX,
        help=f"Input modality matrix TSV. Default: {DEFAULT_MODALITY_MATRIX}",
    )

    parser.add_argument(
        "--file-counts",
        type=Path,
        default=DEFAULT_FILE_COUNTS,
        help=f"Optional input file-count TSV. Default: {DEFAULT_FILE_COUNTS}",
    )

    parser.add_argument(
        "--figures-dir",
        type=Path,
        default=DEFAULT_FIGURES_DIR,
        help=f"Output figures directory. Default: {DEFAULT_FIGURES_DIR}",
    )

    parser.add_argument(
        "--top-n",
        type=int,
        default=30,
        help="Number of top projects to include in top-project heatmaps.",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        outputs = generate_gdc_priority_visuals(
            priority_ranking_path=args.priority_ranking,
            modality_matrix_path=args.modality_matrix,
            file_counts_path=args.file_counts,
            figures_dir=args.figures_dir,
            top_n=args.top_n,
        )
    except Exception as exc:
        print(f"ERROR: Failed to generate GDC priority visuals: {exc}", file=sys.stderr)
        return 1

    print("GDC priority visuals complete.")
    for name, path in outputs.items():
        print(f"  {name}: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
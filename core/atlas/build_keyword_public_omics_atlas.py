#!/usr/bin/env python3#!/usr/bin/env__ import annotations

import argparse
import html
import sys
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd


DEFAULT_INPUT = Path("outputs/dataset_inventory/unified_public_cancer_omics_inventory.tsv")
DEFAULT_OUTPUT_ROOT = Path("outputs/atlases")
DEFAULT_REPORT_ROOT = Path("outputs/reports")

SEARCH_COLUMNS = [
    "record_id",
    "record_name",
    "project_id",
    "dataset_id",
    "primary_site",
    "disease_type",
    "cancer_scope",
    "resource_family",
]


DISPLAY_COLUMNS = [
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
    "atlas_match_terms",
]


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def read_unified_inventory(input_path: Path = DEFAULT_INPUT) -> pd.DataFrame:
    if not input_path.exists():
        raise FileNotFoundError(
            f"Unified inventory not found: {input_path}. "
            "Run python -m core.pipelines.run_unified_public_omics_qc_pipeline "
            "--refresh-xena --xena-recommended-only --make-report --make-qc-report first."
        )

    return pd.read_csv(input_path, sep="\t")


def collect_match_terms(
    row: pd.Series,
    keywords: Iterable[str],
    search_columns: Iterable[str] = SEARCH_COLUMNS,
) -> List[str]:
    text_parts = []

    for column in search_columns:
        if column in row.index:
            text_parts.append(normalize_text(row[column]))

    combined = " ".join(text_parts)

    matches = []
    for keyword in keywords:
        keyword_text = normalize_text(keyword)
        if keyword_text and keyword_text in combined:
            matches.append(keyword_text)

    return sorted(set(matches))


def filter_keyword_relevant_records(
    df: pd.DataFrame,
    keywords: Iterable[str],
    min_priority: Optional[int] = None,
    allowed_sources: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    if df.empty:
        out = df.copy()
        out["atlas_match_terms"] = ""
        return out

    allowed_source_set = None
    if allowed_sources:
        allowed_source_set = {normalize_text(x) for x in allowed_sources if normalize_text(x)}

    records = []

    for _, row in df.iterrows():
        if allowed_source_set is not None and "source_id" in row.index:
            if normalize_text(row["source_id"]) not in allowed_source_set:
                continue

        if min_priority is not None and "priority_for_atlas" in row.index:
            priority_value = pd.to_numeric(pd.Series([row["priority_for_atlas"]]), errors="coerce").iloc[0]
            if pd.isna(priority_value) or int(priority_value) < int(min_priority):
                continue

        match_terms = collect_match_terms(row, keywords=keywords)

        if match_terms:
            item = row.to_dict()
            item["atlas_match_terms"] = ";".join(match_terms)
            records.append(item)

    if not records:
        return pd.DataFrame(columns=list(df.columns) + ["atlas_match_terms"])

    out = pd.DataFrame(records)

    if "priority_for_atlas" in out.columns:
        out["priority_for_atlas"] = pd.to_numeric(
            out["priority_for_atlas"],
            errors="coerce",
        ).fillna(3).astype(int)
    else:
        out["priority_for_atlas"] = 3

    sort_columns = [
        "priority_for_atlas",
        "source_id",
        "source_record_type",
        "omics_modality",
        "record_id",
    ]
    existing_sort_columns = [column for column in sort_columns if column in out.columns]

    if existing_sort_columns:
        ascending = [
            False if column == "priority_for_atlas" else True
            for column in existing_sort_columns
        ]
        out = out.sort_values(
            by=existing_sort_columns,
            ascending=ascending,
            kind="stable",
        ).reset_index(drop=True)

    return out


def value_counts_table(df: pd.DataFrame, column: str, max_rows: Optional[int] = None) -> pd.DataFrame:
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


def escape_html(value: object) -> str:
    if value is None:
        return ""
    return html.escape(str(value))


def dataframe_to_html_table(df: pd.DataFrame, max_rows: Optional[int] = None) -> str:
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


def select_display_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=DISPLAY_COLUMNS)

    out = df.copy()

    for column in DISPLAY_COLUMNS:
        if column not in out.columns:
            out[column] = ""

    return out.loc[:, DISPLAY_COLUMNS]


def build_keyword_public_omics_atlas_report_html(
    atlas_df: pd.DataFrame,
    atlas_name: str,
    title: Optional[str] = None,
) -> str:
    if title is None:
        title = f"{atlas_name.upper()} Public Omics Atlas Inventory Report"

    total_rows = int(len(atlas_df))
    source_count = int(atlas_df["source_id"].nunique()) if "source_id" in atlas_df.columns and not atlas_df.empty else 0
    record_type_count = int(atlas_df["source_record_type"].nunique()) if "source_record_type" in atlas_df.columns and not atlas_df.empty else 0
    modality_count = int(atlas_df["omics_modality"].nunique()) if "omics_modality" in atlas_df.columns and not atlas_df.empty else 0

    source_counts = value_counts_table(atlas_df, "source_id")
    record_type_counts = value_counts_table(atlas_df, "source_record_type")
    modality_counts = value_counts_table(atlas_df, "omics_modality")
    data_category_counts = value_counts_table(atlas_df, "data_category", max_rows=30)
    match_term_counts = value_counts_table(atlas_df, "atlas_match_terms", max_rows=30)
    examples = select_display_columns(atlas_df)

    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        f"<title>{escape_html(title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{escape_html(title)}</h1>",
        f"<p>This report summarizes keyword-matched public omics records for the <strong>{escape_html(atlas_name)}</strong> atlas slice.</p>",
        "<p><strong>Scope:</strong> This is a metadata-only atlas slice. Molecular matrices are not downloaded.</p>",
        "<h2>Summary</h2>",
        "<ul>",
        f"<li>Total atlas rows: {total_rows}</li>",
        f"<li>Sources: {source_count}</li>",
        f"<li>Record types: {record_type_count}</li>",
        f"<li>Modalities: {modality_count}</li>",
        "</ul>",
        "<h2>Rows by source</h2>",
        dataframe_to_html_table(source_counts),
        "<h2>Rows by record type</h2>",
        dataframe_to_html_table(record_type_counts),
        "<h2>Rows by modality</h2>",
        dataframe_to_html_table(modality_counts),
        "<h2>Rows by data category</h2>",
        dataframe_to_html_table(data_category_counts),
        "<h2>Rows by atlas match terms</h2>",
        dataframe_to_html_table(match_term_counts),
        "<h2>Atlas inventory examples</h2>",
        dataframe_to_html_table(examples, max_rows=150),
        "</body>",
        "</html>",
    ]

    return "\n".join(html_parts)


def default_output_path(atlas_name: str) -> Path:
    return DEFAULT_OUTPUT_ROOT / atlas_name / f"{atlas_name}_public_omics_atlas_inventory.tsv"


def default_report_path(atlas_name: str) -> Path:
    return DEFAULT_REPORT_ROOT / f"{atlas_name}_public_omics_atlas_report.html"


def build_keyword_public_omics_atlas(
    atlas_name: str,
    keywords: Iterable[str],
    input_path: Path = DEFAULT_INPUT,
    output_path: Optional[Path] = None,
    report_path: Optional[Path] = None,
    make_report: bool = True,
    report_title: Optional[str] = None,
    min_priority: Optional[int] = None,
    allowed_sources: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    unified_df = read_unified_inventory(input_path)

    atlas_df = filter_keyword_relevant_records(
        unified_df,
        keywords=keywords,
        min_priority=min_priority,
        allowed_sources=allowed_sources,
    )

    if output_path is None:
        output_path = default_output_path(atlas_name)

    if report_path is None:
        report_path = default_report_path(atlas_name)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    atlas_df.to_csv(output_path, sep="\t", index=False)

    if make_report:
        report_html = build_keyword_public_omics_atlas_report_html(
            atlas_df,
            atlas_name=atlas_name,
            title=report_title,
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_html, encoding="utf-8")

    return atlas_df


def print_summary(
    atlas_df: pd.DataFrame,
    atlas_name: str,
    output_path: Path,
    report_path: Path,
    make_report: bool,
) -> None:
    print(f"{atlas_name.upper()} public omics atlas slice complete.")
    print(f"Rows: {len(atlas_df)}")
    print(f"Output: {output_path}")

    if make_report:
        print(f"Report: {report_path}")

    if not atlas_df.empty and "source_id" in atlas_df.columns:
        print("\nRows by source:")
        for name, count in atlas_df["source_id"].fillna("").astype(str).value_counts().items():
            print(f"  {name}: {count}")

    if not atlas_df.empty and "omics_modality" in atlas_df.columns:
        print("\nRows by modality:")
        modality_counts = atlas_df["omics_modality"].fillna("").astype(str).value_counts().head(12)
        for name, count in modality_counts.items():
            print(f"  {name}: {count}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a keyword-driven public omics atlas slice from unified inventory."
    )

    parser.add_argument(
        "--atlas-name",
        required=True,
        help="Atlas name, e.g. gbm, luad, brca.",
    )

    parser.add_argument(
        "--keywords",
        nargs="+",
        required=True,
        help="Keyword list used to match rows in the unified inventory.",
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
        default=None,
        help="Optional atlas inventory TSV output path.",
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Optional atlas HTML report output path.",
    )

    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Disable atlas HTML report generation.",
    )

    parser.add_argument(
        "--report-title",
        default=None,
        help="Optional custom HTML report title.",
    )

    parser.add_argument(
        "--min-priority",
        type=int,
        default=None,
        help="Optional minimum priority_for_atlas threshold.",
    )

    parser.add_argument(
        "--sources",
        nargs="*",
        default=None,
        help="Optional allowed source_id values, e.g. gdc xena.",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    output_path = args.output if args.output is not None else default_output_path(args.atlas_name)
    report_path = args.report if args.report is not None else default_report_path(args.atlas_name)

    try:
        atlas_df = build_keyword_public_omics_atlas(
            atlas_name=args.atlas_name,
            keywords=args.keywords,
            input_path=args.input,
            output_path=output_path,
            report_path=report_path,
            make_report=not args.no_report,
            report_title=args.report_title,
            min_priority=args.min_priority,
            allowed_sources=args.sources,
        )
    except Exception as exc:
        print(f"ERROR: Failed to build keyword atlas slice: {exc}", file=sys.stderr)
        return 1

    print_summary(
        atlas_df=atlas_df,
        atlas_name=args.atlas_name,
        output_path=output_path,
        report_path=report_path,
        make_report=not args.no_report,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())



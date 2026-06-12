from pathlib import Path

import pandas as pd

from core.pipelines.run_xena_metadata_pipeline import (
    build_arg_parser,
    build_xena_pipeline_summary_table,
    format_seconds,
    run_xena_metadata_pipeline,
    safe_count_by_column,
    write_xena_pipeline_summary,
)


def make_inventory_df():
    return pd.DataFrame(
        [
            {
                "hub_id": "gdc_xena",
                "omics_modality": "transcriptomics",
                "data_category": "gene expression",
                "integration_stage": "live_inventory",
                "dataset_id": "TCGA-GBM.star_tpm.tsv",
            },
            {
                "hub_id": "gdc_xena",
                "omics_modality": "clinical_annotation",
                "data_category": "clinical phenotype",
                "integration_stage": "live_inventory",
                "dataset_id": "TCGA-GBM.clinical.tsv",
            },
            {
                "hub_id": "tcga_xena",
                "omics_modality": "cnv",
                "data_category": "copy number",
                "integration_stage": "live_inventory",
                "dataset_id": "TCGA.GBM.sampleMap/Gistic2_CopyNumber",
            },
        ]
    )


def test_format_seconds():
    assert format_seconds(1.23) == "1.2s"
    assert format_seconds(65.0) == "1m 5.0s"
    assert format_seconds(3665.0) == "1h 1m 5.0s"


def test_safe_count_by_column():
    df = make_inventory_df()
    counts = safe_count_by_column(df, "hub_id")

    assert list(counts.columns) == ["summary_type", "name", "count"]
    assert "gdc_xena" in set(counts["name"])
    assert int(counts.loc[counts["name"] == "gdc_xena", "count"].iloc[0]) == 2


def test_build_xena_pipeline_summary_table():
    df = make_inventory_df()
    summary = build_xena_pipeline_summary_table(df, elapsed_seconds=1.23456)

    assert not summary.empty
    assert "pipeline_metric" in set(summary["summary_type"])
    assert "hub_id" in set(summary["summary_type"])
    assert "omics_modality" in set(summary["summary_type"])
    assert "total_dataset_rows" in set(summary["name"])


def test_write_xena_pipeline_summary(tmp_path: Path):
    df = make_inventory_df()
    output_path = tmp_path / "summary.tsv"

    summary = write_xena_pipeline_summary(
        inventory_df=df,
        summary_path=output_path,
        elapsed_seconds=1.0,
    )

    assert output_path.exists()
    loaded = pd.read_csv(output_path, sep="\t")
    assert loaded.shape[0] == summary.shape[0]
    assert "summary_type" in loaded.columns


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--hub-id", "gdc_xena", "--recommended-only"])

    assert args.hub_id == ["gdc_xena"]
    assert args.recommended_only is True


def test_run_xena_metadata_pipeline_with_monkeypatch(tmp_path: Path, monkeypatch):
    inventory_output = tmp_path / "xena_dataset_inventory.tsv"
    summary_output = tmp_path / "xena_metadata_pipeline_summary.tsv"

    def fake_write_xena_dataset_inventory(
        output_path,
        hub_ids=None,
        recommended_only=False,
        min_priority=None,
        timeout=60,
        sleep_seconds=0.0,
        allow_failures=True,
    ):
        df = make_inventory_df()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, sep="\t", index=False)
        return df

    monkeypatch.setattr(
        "core.pipelines.run_xena_metadata_pipeline.write_xena_dataset_inventory",
        fake_write_xena_dataset_inventory,
    )

    inventory_df, summary_df = run_xena_metadata_pipeline(
        output_path=inventory_output,
        summary_path=summary_output,
        hub_ids=["gdc_xena"],
        recommended_only=False,
    )

    assert inventory_output.exists()
    assert summary_output.exists()
    assert inventory_df.shape[0] == 3
    assert not summary_df.empty



def test_build_arg_parser_report_flags():
    parser = build_arg_parser()
    args = parser.parse_args(
        [
            "--recommended-only",
            "--make-report",
            "--open-report",
            "--report-title",
            "Demo Xena Report",
        ]
    )

    assert args.recommended_only is True
    assert args.make_report is True
    assert args.open_report is True
    assert args.report_title == "Demo Xena Report"


def test_run_xena_metadata_pipeline_make_report_with_monkeypatch(tmp_path: Path, monkeypatch):
    inventory_output = tmp_path / "xena_dataset_inventory.tsv"
    summary_output = tmp_path / "xena_metadata_pipeline_summary.tsv"
    report_output = tmp_path / "xena_dataset_inventory_report.html"

    def fake_write_xena_dataset_inventory(
        output_path,
        hub_ids=None,
        recommended_only=False,
        min_priority=None,
        timeout=60,
        sleep_seconds=0.0,
        allow_failures=True,
    ):
        df = make_inventory_df()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, sep="\t", index=False)
        return df

    def fake_generate_report(input_path, output_path, title):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(f"<html><title>{title}</title></html>", encoding="utf-8")
        return output_path.read_text(encoding="utf-8")

    monkeypatch.setattr(
        "core.pipelines.run_xena_metadata_pipeline.write_xena_dataset_inventory",
        fake_write_xena_dataset_inventory,
    )

    monkeypatch.setattr(
        "core.pipelines.run_xena_metadata_pipeline.generate_xena_dataset_inventory_report",
        fake_generate_report,
    )

    inventory_df, summary_df = run_xena_metadata_pipeline(
        output_path=inventory_output,
        summary_path=summary_output,
        report_path=report_output,
        report_title="Demo Xena Report",
        recommended_only=True,
        make_report=True,
        open_report=False,
    )

    assert inventory_output.exists()
    assert summary_output.exists()
    assert report_output.exists()
    assert inventory_df.shape[0] == 3
    assert "report_generated" in set(summary_df["name"])
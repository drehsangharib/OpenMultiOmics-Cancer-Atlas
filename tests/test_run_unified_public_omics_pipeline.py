from pathlib import Path

import pandas as pd

from core.pipelines.run_unified_public_omics_pipeline import (
    build_arg_parser,
    build_unified_pipeline_summary_table,
    format_seconds,
    run_unified_public_omics_pipeline,
    safe_count_by_column,
    write_unified_pipeline_summary,
)


def make_unified_df():
    return pd.DataFrame(
        [
            {
                "source_id": "gdc",
                "source_record_type": "gdc_project",
                "record_id": "TCGA-GBM",
                "omics_modality": "clinical_annotation;snv;transcriptomics",
                "data_category": "GDC project metadata",
                "cancer_scope": "GDC project/cohort",
                "priority_for_atlas": 5,
            },
            {
                "source_id": "xena",
                "source_record_type": "xena_dataset",
                "record_id": "TCGA-GBM.star_tpm.tsv",
                "omics_modality": "transcriptomics",
                "data_category": "gene expression",
                "cancer_scope": "TCGA cancer cohorts",
                "priority_for_atlas": 5,
            },
            {
                "source_id": "xena",
                "source_record_type": "xena_dataset",
                "record_id": "unknown_dataset.txt",
                "omics_modality": "unknown",
                "data_category": "unknown",
                "cancer_scope": "pan-cancer",
                "priority_for_atlas": 4,
            },
        ]
    )


def test_format_seconds():
    assert format_seconds(1.23) == "1.2s"
    assert format_seconds(65.0) == "1m 5.0s"
    assert format_seconds(3665.0) == "1h 1m 5.0s"


def test_safe_count_by_column():
    counts = safe_count_by_column(make_unified_df(), "source_id")

    assert list(counts.columns) == ["summary_type", "name", "count"]
    assert "xena" in set(counts["name"])


def test_build_unified_pipeline_summary_table():
    summary = build_unified_pipeline_summary_table(
        make_unified_df(),
        elapsed_seconds=1.234,
        xena_refreshed=True,
        report_generated=True,
        unified_output_path=Path("unified.tsv"),
        summary_output_path=Path("summary.tsv"),
        report_output_path=Path("report.html"),
    )

    assert not summary.empty
    assert "total_unified_rows" in set(summary["name"])
    assert "report_generated" in set(summary["name"])
    assert "xena_refreshed" in set(summary["name"])
    assert "source_id" in set(summary["summary_type"])


def test_write_unified_pipeline_summary(tmp_path: Path):
    output_path = tmp_path / "summary.tsv"

    summary = write_unified_pipeline_summary(
        unified_df=make_unified_df(),
        summary_output_path=output_path,
        elapsed_seconds=1.0,
        xena_refreshed=False,
        report_generated=False,
    )

    assert output_path.exists()
    loaded = pd.read_csv(output_path, sep="\t")
    assert loaded.shape[0] == summary.shape[0]
    assert "summary_type" in loaded.columns


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(
        [
            "--refresh-xena",
            "--xena-recommended-only",
            "--make-report",
            "--open-report",
            "--report-title",
            "Demo Unified Report",
        ]
    )

    assert args.refresh_xena is True
    assert args.xena_recommended_only is True
    assert args.make_report is True
    assert args.open_report is True
    assert args.report_title == "Demo Unified Report"


def test_run_unified_public_omics_pipeline_with_monkeypatch(tmp_path: Path, monkeypatch):
    unified_output = tmp_path / "unified.tsv"
    summary_output = tmp_path / "summary.tsv"
    report_output = tmp_path / "report.html"

    def fake_write_unified_public_cancer_omics_inventory(
        output_path,
        gdc_input=None,
        xena_input=None,
        allow_missing_inputs=True,
    ):
        df = make_unified_df()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, sep="\t", index=False)
        return df

    def fake_generate_report(input_path, output_path, title):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(f"<html><title>{title}</title></html>", encoding="utf-8")
        return output_path.read_text(encoding="utf-8")

    monkeypatch.setattr(
        "core.pipelines.run_unified_public_omics_pipeline.write_unified_public_cancer_omics_inventory",
        fake_write_unified_public_cancer_omics_inventory,
    )

    monkeypatch.setattr(
        "core.pipelines.run_unified_public_omics_pipeline.generate_unified_public_cancer_omics_inventory_report",
        fake_generate_report,
    )

    unified_df, summary_df = run_unified_public_omics_pipeline(
        unified_output_path=unified_output,
        summary_output_path=summary_output,
        report_output_path=report_output,
        report_title="Demo Unified Report",
        make_report=True,
        open_report=False,
    )

    assert unified_output.exists()
    assert summary_output.exists()
    assert report_output.exists()
    assert unified_df.shape[0] == 3
    assert not summary_df.empty


def test_run_unified_public_omics_pipeline_refresh_xena_with_monkeypatch(tmp_path: Path, monkeypatch):
    unified_output = tmp_path / "unified.tsv"
    summary_output = tmp_path / "summary.tsv"
    xena_output = tmp_path / "xena.tsv"

    events = {"xena_refreshed": False}

    def fake_run_xena_metadata_pipeline(
        output_path,
        recommended_only=False,
        min_priority=None,
        timeout=60,
        sleep_seconds=0.0,
        strict=False,
        make_report=False,
        open_report=False,
    ):
        events["xena_refreshed"] = True
        xena_output.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"dataset_id": ["demo"]}).to_csv(output_path, sep="\t", index=False)
        return pd.DataFrame({"dataset_id": ["demo"]}), pd.DataFrame({"summary_type": []})

    def fake_write_unified_public_cancer_omics_inventory(
        output_path,
        gdc_input=None,
        xena_input=None,
        allow_missing_inputs=True,
    ):
        df = make_unified_df()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, sep="\t", index=False)
        return df

    monkeypatch.setattr(
        "core.pipelines.run_unified_public_omics_pipeline.run_xena_metadata_pipeline",
        fake_run_xena_metadata_pipeline,
    )

    monkeypatch.setattr(
        "core.pipelines.run_unified_public_omics_pipeline.write_unified_public_cancer_omics_inventory",
        fake_write_unified_public_cancer_omics_inventory,
    )

    run_unified_public_omics_pipeline(
        unified_output_path=unified_output,
        summary_output_path=summary_output,
        xena_input=xena_output,
        refresh_xena=True,
        xena_recommended_only=True,
    )

    assert events["xena_refreshed"] is True
    assert unified_output.exists()
    assert summary_output.exists()
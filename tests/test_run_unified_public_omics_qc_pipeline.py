from pathlib import Path

import pandas as pd

from core.pipelines.run_unified_public_omics_qc_pipeline import (
    build_arg_parser,
    run_unified_public_omics_qc_pipeline,
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
        ]
    )


def test_build_arg_parser_qc_flags():
    parser = build_arg_parser()
    args = parser.parse_args(
        [
            "--refresh-xena",
            "--xena-recommended-only",
            "--make-report",
            "--make-qc-report",
            "--open-qc-report",
            "--qc-report-title",
            "Demo QC Report",
        ]
    )

    assert args.refresh_xena is True
    assert args.xena_recommended_only is True
    assert args.make_report is True
    assert args.make_qc_report is True
    assert args.open_qc_report is True
    assert args.qc_report_title == "Demo QC Report"


def test_run_unified_public_omics_qc_pipeline_with_monkeypatch(tmp_path: Path, monkeypatch):
    unified_output = tmp_path / "unified.tsv"
    summary_output = tmp_path / "summary.tsv"
    report_output = tmp_path / "report.html"
    qc_report_output = tmp_path / "qc_report.html"

    def fake_run_unified_public_omics_pipeline(
        unified_output_path,
        summary_output_path,
        report_output_path,
        report_title,
        gdc_input=None,
        xena_input=None,
        strict_inputs=False,
        refresh_xena=False,
        xena_recommended_only=False,
        xena_min_priority=None,
        xena_timeout=60,
        xena_sleep_seconds=0.0,
        xena_strict=False,
        make_report=False,
        open_report=False,
    ):
        df = make_unified_df()
        summary_df = pd.DataFrame(
            [
                {
                    "summary_type": "pipeline_metric",
                    "name": "total_unified_rows",
                    "count": len(df),
                }
            ]
        )

        unified_output_path.parent.mkdir(parents=True, exist_ok=True)
        summary_output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(unified_output_path, sep="\t", index=False)
        summary_df.to_csv(summary_output_path, sep="\t", index=False)

        if make_report:
            report_output_path.parent.mkdir(parents=True, exist_ok=True)
            report_output_path.write_text("<html>report</html>", encoding="utf-8")

        return df, summary_df

    def fake_generate_qc_report(input_path, output_path, title):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(f"<html><title>{title}</title></html>", encoding="utf-8")
        return output_path.read_text(encoding="utf-8")

    monkeypatch.setattr(
        "core.pipelines.run_unified_public_omics_qc_pipeline.run_unified_public_omics_pipeline",
        fake_run_unified_public_omics_pipeline,
    )

    monkeypatch.setattr(
        "core.pipelines.run_unified_public_omics_qc_pipeline.generate_unified_public_cancer_omics_qc_report",
        fake_generate_qc_report,
    )

    unified_df, summary_df, qc_html = run_unified_public_omics_qc_pipeline(
        unified_output_path=unified_output,
        summary_output_path=summary_output,
        report_output_path=report_output,
        qc_report_output_path=qc_report_output,
        report_title="Demo Unified Report",
        qc_report_title="Demo QC Report",
        refresh_xena=True,
        xena_recommended_only=True,
        make_report=True,
        make_qc_report=True,
        open_report=False,
        open_qc_report=False,
    )

    assert unified_output.exists()
    assert summary_output.exists()
    assert report_output.exists()
    assert qc_report_output.exists()
    assert unified_df.shape[0] == 2
    assert not summary_df.empty
    assert "Demo QC Report" in qc_html
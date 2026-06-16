from pathlib import Path

import pandas as pd

from atlases.gbm.run_gbm_public_omics_atlas_pipeline import (
    build_arg_parser,
    run_gbm_public_omics_atlas_pipeline,
)


def test_build_arg_parser_flags():
    parser = build_arg_parser()
    args = parser.parse_args(
        [
            "--refresh-xena",
            "--xena-recommended-only",
            "--make-report",
            "--make-qc-report",
            "--open-report",
        ]
    )

    assert args.refresh_xena is True
    assert args.xena_recommended_only is True
    assert args.make_report is True
    assert args.make_qc_report is True
    assert args.open_report is True


def test_run_gbm_public_omics_atlas_pipeline_with_monkeypatch(tmp_path: Path, monkeypatch):
    unified_output = tmp_path / "unified.tsv"
    unified_summary = tmp_path / "unified_summary.tsv"
    unified_report = tmp_path / "unified_report.html"
    unified_qc_report = tmp_path / "unified_qc_report.html"
    gbm_output = tmp_path / "gbm.tsv"
    gbm_report = tmp_path / "gbm_report.html"
    gbm_qc_report = tmp_path / "gbm_qc_report.html"

    def fake_run_unified_public_omics_qc_pipeline(
        unified_output_path,
        summary_output_path,
        report_output_path,
        qc_report_output_path,
        report_title,
        qc_report_title,
        strict_inputs=False,
        refresh_xena=False,
        xena_recommended_only=False,
        xena_min_priority=None,
        xena_timeout=60,
        xena_sleep_seconds=0.0,
        xena_strict=False,
        make_report=False,
        make_qc_report=False,
        open_report=False,
        open_qc_report=False,
    ):
        df = pd.DataFrame(
            [
                {
                    "source_id": "xena",
                    "source_record_type": "xena_dataset",
                    "record_id": "TCGA-GBM.star_tpm.tsv",
                    "record_name": "TCGA GBM STAR TPM",
                    "project_id": "",
                    "dataset_id": "TCGA-GBM.star_tpm.tsv",
                    "hub_id": "gdc_xena",
                    "omics_modality": "transcriptomics",
                    "data_category": "gene expression",
                    "matrix_type": "sample-by-gene expression matrix",
                    "resource_family": "TCGA",
                    "primary_site": "Brain",
                    "disease_type": "Gliomas",
                    "cancer_scope": "TCGA cancer cohorts",
                    "priority_for_atlas": 5,
                    "source_url": "https://gdc.xenahubs.net/",
                    "notes": "GBM",
                }
            ]
        )
        summary_df = pd.DataFrame([{"metric": "total_rows", "value": 1}])

        df.to_csv(unified_output_path, sep="\t", index=False)
        summary_df.to_csv(summary_output_path, sep="\t", index=False)

        if make_report:
            report_output_path.write_text("<html>Unified report</html>", encoding="utf-8")
        if make_qc_report:
            qc_report_output_path.write_text("<html>Unified QC</html>", encoding="utf-8")

        return df, summary_df, "<html>Unified QC</html>"

    def fake_build_gbm_public_omics_atlas(
        input_path,
        output_path,
        report_path,
        make_report=True,
        report_title="GBM Public Omics Atlas Inventory Report",
    ):
        df = pd.DataFrame(
            [
                {
                    "source_id": "xena",
                    "source_record_type": "xena_dataset",
                    "record_id": "TCGA-GBM.star_tpm.tsv",
                    "record_name": "TCGA GBM STAR TPM",
                    "project_id": "",
                    "dataset_id": "TCGA-GBM.star_tpm.tsv",
                    "hub_id": "gdc_xena",
                    "omics_modality": "transcriptomics",
                    "data_category": "gene expression",
                    "matrix_type": "sample-by-gene expression matrix",
                    "resource_family": "TCGA",
                    "primary_site": "Brain",
                    "disease_type": "Gliomas",
                    "cancer_scope": "TCGA cancer cohorts",
                    "priority_for_atlas": 5,
                    "source_url": "https://gdc.xenahubs.net/",
                    "gbm_match_terms": "brain;gbm;glioma",
                }
            ]
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, sep="\t", index=False)

        if make_report:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text("<html>GBM report</html>", encoding="utf-8")

        return df

    def fake_generate_gbm_public_omics_atlas_qc_report(
        input_path,
        output_path,
        title="GBM Public Omics Atlas QC Report",
    ):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("<html>GBM QC report</html>", encoding="utf-8")
        return "<html>GBM QC report</html>"

    monkeypatch.setattr(
        "atlases.gbm.run_gbm_public_omics_atlas_pipeline.run_unified_public_omics_qc_pipeline",
        fake_run_unified_public_omics_qc_pipeline,
    )
    monkeypatch.setattr(
        "atlases.gbm.run_gbm_public_omics_atlas_pipeline.build_gbm_public_omics_atlas",
        fake_build_gbm_public_omics_atlas,
    )
    monkeypatch.setattr(
        "atlases.gbm.run_gbm_public_omics_atlas_pipeline.generate_gbm_public_omics_atlas_qc_report",
        fake_generate_gbm_public_omics_atlas_qc_report,
    )

    unified_df, unified_summary_df, unified_qc_html, gbm_df, gbm_qc_html = run_gbm_public_omics_atlas_pipeline(
        unified_output_path=unified_output,
        unified_summary_path=unified_summary,
        unified_report_path=unified_report,
        unified_qc_report_path=unified_qc_report,
        gbm_output_path=gbm_output,
        gbm_report_path=gbm_report,
        gbm_qc_report_path=gbm_qc_report,
        refresh_xena=True,
        xena_recommended_only=True,
        make_report=True,
        make_qc_report=True,
        open_report=False,
    )

    assert unified_output.exists()
    assert unified_summary.exists()
    assert unified_report.exists()
    assert unified_qc_report.exists()
    assert gbm_output.exists()
    assert gbm_report.exists()
    assert gbm_qc_report.exists()

    assert unified_df.shape[0] == 1
    assert not unified_summary_df.empty
    assert gbm_df.shape[0] == 1
    assert "Unified QC" in unified_qc_html
    assert "GBM QC report" in gbm_qc_html
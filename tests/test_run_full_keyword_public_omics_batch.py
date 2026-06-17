from pathlib import Path

import pandas as pd

from core.atlas.run_full_keyword_public_omics_batch import (
    build_arg_parser,
    run_full_keyword_public_omics_batch,
)


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(
        [
            "--config-dir",
            "configs/atlas_definitions",
            "--atlases",
            "gbm",
            "luad",
            "--open-reports",
        ]
    )

    assert str(args.config_dir).replace("\\", "/").endswith("configs/atlas_definitions")
    assert args.atlases == ["gbm", "luad"]
    assert args.open_reports is True


def test_run_full_keyword_public_omics_batch_with_monkeypatch(tmp_path: Path, monkeypatch):
    build_summary_output = tmp_path / "atlas_batch_summary.tsv"
    qc_summary_output = tmp_path / "atlas_qc_batch_summary.tsv"

    def fake_run_keyword_public_omics_atlas_batch(
        config_dir,
        atlas_names=None,
        summary_output_path=None,
        open_reports=False,
    ):
        df = pd.DataFrame(
            [
                {
                    "atlas_name": "gbm",
                    "rows": 95,
                    "output_path": "outputs/atlases/gbm/gbm_public_omics_atlas_inventory.tsv",
                    "report_path": "outputs/reports/gbm_public_omics_atlas_report.html",
                },
                {
                    "atlas_name": "luad",
                    "rows": 68,
                    "output_path": "outputs/atlases/luad/luad_public_omics_atlas_inventory.tsv",
                    "report_path": "outputs/reports/luad_public_omics_atlas_report.html",
                },
            ]
        )
        summary_output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(summary_output_path, sep="\t", index=False)
        return df

    def fake_run_keyword_public_omics_atlas_qc_batch(
        config_dir,
        atlas_names=None,
        summary_output_path=None,
        open_reports=False,
    ):
        df = pd.DataFrame(
            [
                {
                    "atlas_name": "gbm",
                    "qc_html_characters": 9152,
                    "qc_report_path": "outputs/reports/gbm_public_omics_atlas_qc_report.html",
                },
                {
                    "atlas_name": "luad",
                    "qc_html_characters": 7398,
                    "qc_report_path": "outputs/reports/luad_public_omics_atlas_qc_report.html",
                },
            ]
        )
        summary_output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(summary_output_path, sep="\t", index=False)
        return df

    monkeypatch.setattr(
        "core.atlas.run_full_keyword_public_omics_batch.run_keyword_public_omics_atlas_batch",
        fake_run_keyword_public_omics_atlas_batch,
    )
    monkeypatch.setattr(
        "core.atlas.run_full_keyword_public_omics_batch.run_keyword_public_omics_atlas_qc_batch",
        fake_run_keyword_public_omics_atlas_qc_batch,
    )

    build_summary_df, qc_summary_df = run_full_keyword_public_omics_batch(
        config_dir=Path("configs/atlas_definitions"),
        atlas_names=["gbm", "luad"],
        build_summary_output_path=build_summary_output,
        qc_summary_output_path=qc_summary_output,
        open_reports=False,
    )

    assert build_summary_output.exists()
    assert qc_summary_output.exists()
    assert build_summary_df.shape[0] == 2
    assert qc_summary_df.shape[0] == 2
    assert set(build_summary_df["atlas_name"]) == {"gbm", "luad"}
    assert set(qc_summary_df["atlas_name"]) == {"gbm", "luad"}
from pathlib import Path

import pandas as pd

from core.pipelines.run_gdc_metadata_pipeline import (
    PipelineStepResult,
    build_pipeline_summary_table,
    count_tsv_rows,
    format_seconds,
    print_pipeline_summary,
    run_gdc_metadata_pipeline,
    write_pipeline_summary,
)


def test_format_seconds():
    assert format_seconds(1.23) == "1.2s"
    assert format_seconds(65.0) == "1m 5.0s"
    assert format_seconds(3665.0) == "1h 1m 5.0s"


def test_count_tsv_rows(tmp_path: Path):
    path = tmp_path / "demo.tsv"
    path.write_text("a\tb\n1\t2\n3\t4\n", encoding="utf-8")

    assert count_tsv_rows(path) == 2
    assert count_tsv_rows(tmp_path / "missing.tsv") is None


def test_build_pipeline_summary_table():
    results = [
        PipelineStepResult(
            step_name="step_a",
            status="completed",
            output_path="a.tsv",
            row_count=10,
            elapsed_seconds=1.23456,
        )
    ]

    summary = build_pipeline_summary_table(results)

    assert summary.shape[0] == 1
    assert summary.iloc[0]["step_name"] == "step_a"
    assert summary.iloc[0]["elapsed_seconds"] == 1.235


def test_write_pipeline_summary(tmp_path: Path):
    results = [
        PipelineStepResult(
            step_name="step_a",
            status="completed",
            output_path="a.tsv",
            row_count=10,
            elapsed_seconds=1.0,
        )
    ]

    output_path = tmp_path / "summary.tsv"
    write_pipeline_summary(results, output_path)

    assert output_path.exists()
    df = pd.read_csv(output_path, sep="\t")
    assert df.iloc[0]["step_name"] == "step_a"


def test_print_pipeline_summary(capsys):
    results = [
        PipelineStepResult(
            step_name="step_a",
            status="completed",
            output_path="a.tsv",
            row_count=10,
            elapsed_seconds=1.0,
        )
    ]

    print_pipeline_summary(results)
    captured = capsys.readouterr()

    assert "GDC metadata pipeline summary" in captured.out
    assert "step_a" in captured.out


def test_run_gdc_metadata_pipeline_report_only_with_monkeypatch(tmp_path: Path, monkeypatch):
    project_inventory = tmp_path / "project_inventory.tsv"
    file_counts = tmp_path / "file_counts.tsv"
    modality_matrix = tmp_path / "modality_matrix.tsv"
    priority_ranking = tmp_path / "priority_ranking.tsv"
    figures_dir = tmp_path / "figures"
    report = tmp_path / "report.html"
    summary = tmp_path / "summary.tsv"

    project_inventory.write_text("project_id\nTCGA-GBM\n", encoding="utf-8")
    file_counts.write_text("project_id\nTCGA-GBM\n", encoding="utf-8")

    def fake_modality_step(input_path, output_path):
        output_path.write_text("project_id\nTCGA-GBM\n", encoding="utf-8")
        return PipelineStepResult(
            step_name="project_modality_matrix",
            status="completed",
            output_path=str(output_path),
            row_count=1,
            elapsed_seconds=0.1,
        )

    def fake_ranking_step(project_inventory_path, modality_matrix_path, output_path):
        output_path.write_text("project_id\nTCGA-GBM\n", encoding="utf-8")
        return PipelineStepResult(
            step_name="project_priority_ranking",
            status="completed",
            output_path=str(output_path),
            row_count=1,
            elapsed_seconds=0.1,
        )

    def fake_visuals_step(
        priority_ranking_path,
        modality_matrix_path,
        file_counts_path,
        figures_dir,
        top_n,
    ):
        figures_dir.mkdir(parents=True, exist_ok=True)
        (figures_dir / "demo.png").write_bytes(b"demo")
        return PipelineStepResult(
            step_name="priority_visuals",
            status="completed",
            output_path=str(figures_dir),
            row_count=1,
            elapsed_seconds=0.1,
        )

    def fake_report_step(
        project_inventory_path,
        modality_matrix_path,
        priority_ranking_path,
        figures_dir,
        output_path,
        embed_images,
    ):
        output_path.write_text("<html>demo</html>", encoding="utf-8")
        return PipelineStepResult(
            step_name="priority_html_report",
            status="completed",
            output_path=str(output_path),
            row_count=17,
            elapsed_seconds=0.1,
        )

    monkeypatch.setattr(
        "core.pipelines.run_gdc_metadata_pipeline.run_modality_matrix_step",
        fake_modality_step,
    )
    monkeypatch.setattr(
        "core.pipelines.run_gdc_metadata_pipeline.run_priority_ranking_step",
        fake_ranking_step,
    )
    monkeypatch.setattr(
        "core.pipelines.run_gdc_metadata_pipeline.run_visuals_step",
        fake_visuals_step,
    )
    monkeypatch.setattr(
        "core.pipelines.run_gdc_metadata_pipeline.run_report_step",
        fake_report_step,
    )

    results = run_gdc_metadata_pipeline(
        project_inventory_path=project_inventory,
        file_counts_path=file_counts,
        modality_matrix_path=modality_matrix,
        priority_ranking_path=priority_ranking,
        figures_dir=figures_dir,
        report_path=report,
        summary_path=summary,
        report_only=True,
    )

    assert len(results) == 6
    assert report.exists()
    assert summary.exists()
    assert results[0].status == "skipped_existing"
    assert results[1].status == "skipped_existing"
    assert results[-1].step_name == "priority_html_report"
def test_apply_dev_output_paths():
    from core.pipelines.run_gdc_metadata_pipeline import (
        apply_dev_output_paths,
        build_arg_parser,
    )

    parser = build_arg_parser()
    args = parser.parse_args(["--dev-output"])

    updated = apply_dev_output_paths(args)

    assert updated.project_inventory.as_posix() == "outputs/dev/gdc_project_inventory.tsv"
    assert updated.file_counts.as_posix() == "outputs/dev/gdc_file_counts_by_project.tsv"
    assert updated.modality_matrix.as_posix() == "outputs/dev/gdc_project_modality_matrix.tsv"
    assert updated.priority_ranking.as_posix() == "outputs/dev/gdc_project_priority_ranking.tsv"
    assert updated.figures_dir.as_posix() == "outputs/dev/figures"
    assert updated.report.as_posix() == "outputs/dev/gdc_project_priority_report.html"
    assert updated.summary.as_posix() == "outputs/dev/gdc_metadata_pipeline_summary.tsv"

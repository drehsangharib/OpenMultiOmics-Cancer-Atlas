from pathlib import Path

import pandas as pd

from core.pipelines.export_gdc_cancer_subset import (
    build_subset_output_paths,
    build_subset_summary_markdown,
    export_gdc_cancer_subset,
    format_count_section,
    format_top_projects_table,
    modality_counts,
    sanitize_subset_name,
    value_counts_dict,
    write_subset_summary,
)


def make_subset_df():
    return pd.DataFrame(
        [
            {
                "rank": 1,
                "project_id": "TCGA-GBM",
                "project_name": "Glioblastoma Multiforme",
                "program_name": "TCGA",
                "primary_site": "Brain",
                "disease_type": "Gliomas",
                "case_count": 617,
                "file_count": 30326,
                "priority_score": 35,
                "priority_label": "excellent",
                "multiomics_modality_count": 10,
                "has_transcriptomics": True,
                "has_methylation": True,
                "has_snv": True,
                "has_cnv": True,
                "has_structural_variation": True,
                "has_clinical": True,
                "has_biospecimen": True,
                "has_proteomics": True,
                "has_slide_images": True,
                "has_sequencing_reads": True,
                "subset_query": "primary_site_exact=Brain",
            },
            {
                "rank": 2,
                "project_id": "TCGA-LGG",
                "project_name": "Lower Grade Glioma",
                "program_name": "TCGA",
                "primary_site": "Brain",
                "disease_type": "Gliomas",
                "case_count": 516,
                "file_count": 33453,
                "priority_score": 35,
                "priority_label": "excellent",
                "multiomics_modality_count": 10,
                "has_transcriptomics": True,
                "has_methylation": True,
                "has_snv": True,
                "has_cnv": True,
                "has_structural_variation": True,
                "has_clinical": True,
                "has_biospecimen": True,
                "has_proteomics": True,
                "has_slide_images": True,
                "has_sequencing_reads": True,
                "subset_query": "primary_site_exact=Brain",
            },
        ]
    )


def test_sanitize_subset_name():
    assert sanitize_subset_name("Brain Exact") == "brain_exact"
    assert sanitize_subset_name("GBM/Brain!!") == "gbm_brain"
    assert sanitize_subset_name("   ") == "gdc_subset"


def test_build_subset_output_paths(tmp_path: Path):
    paths = build_subset_output_paths(
        subset_name="Brain Exact",
        subsets_dir=tmp_path,
    )

    assert paths["subset_dir"] == tmp_path / "brain_exact"
    assert paths["subset_tsv"] == tmp_path / "brain_exact" / "gdc_project_subset.tsv"
    assert paths["summary_md"] == tmp_path / "brain_exact" / "gdc_project_subset_summary.md"


def test_value_counts_dict():
    counts = value_counts_dict(make_subset_df(), "priority_label")
    assert counts == {"excellent": 2}


def test_modality_counts():
    counts = modality_counts(make_subset_df())
    assert counts["Transcriptomics"] == 2
    assert counts["Proteomics"] == 2


def test_format_count_section():
    text = format_count_section("Priority labels", {"excellent": 2})
    assert "## Priority labels" in text
    assert "- excellent: 2" in text


def test_format_top_projects_table():
    table = format_top_projects_table(make_subset_df())
    assert "## Top projects" in table
    assert "TCGA-GBM" in table
    assert "TCGA-LGG" in table


def test_build_subset_summary_markdown():
    summary = build_subset_summary_markdown(
        subset_df=make_subset_df(),
        subset_name="brain_exact",
        subset_query="primary_site_exact=Brain",
    )

    assert "# GDC Project Subset Summary: brain_exact" in summary
    assert "Project count: 2" in summary
    assert "Total cases: 1133" in summary
    assert "primary_site_exact=Brain" in summary
    assert "TCGA-GBM" in summary


def test_write_subset_summary(tmp_path: Path):
    summary_path = tmp_path / "summary.md"

    markdown = write_subset_summary(
        subset_df=make_subset_df(),
        subset_name="brain_exact",
        summary_path=summary_path,
    )

    assert summary_path.exists()
    assert "brain_exact" in markdown
    assert "TCGA-LGG" in summary_path.read_text(encoding="utf-8")


def test_export_gdc_cancer_subset_with_monkeypatch(tmp_path: Path, monkeypatch):
    def fake_build_gdc_project_subset(
        project_inventory_path,
        modality_matrix_path,
        priority_ranking_path,
        output_path,
        project_ids=None,
        programs=None,
        primary_sites=None,
        primary_sites_exact=None,
        disease_types=None,
        disease_types_exact=None,
        priority_labels=None,
        required_modalities=None,
        min_case_count=None,
        min_priority_score=None,
        min_modality_count=None,
        top_n=None,
    ):
        df = make_subset_df()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, sep="\t", index=False)
        return df

    monkeypatch.setattr(
        "core.pipelines.export_gdc_cancer_subset.build_gdc_project_subset",
        fake_build_gdc_project_subset,
    )

    paths = export_gdc_cancer_subset(
        subset_name="Brain Exact",
        project_inventory_path=tmp_path / "project.tsv",
        modality_matrix_path=tmp_path / "modality.tsv",
        priority_ranking_path=tmp_path / "ranking.tsv",
        subsets_dir=tmp_path / "subsets",
        primary_sites_exact=["Brain"],
    )

    assert paths["subset_tsv"].exists()
    assert paths["summary_md"].exists()

    summary = paths["summary_md"].read_text(encoding="utf-8")
    assert "brain_exact" in summary
    assert "TCGA-GBM" in summary
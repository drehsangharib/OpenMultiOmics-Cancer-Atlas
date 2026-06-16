from pathlib import Path


def test_project_quickstart_workflows_doc_exists_and_mentions_core_commands():
    path = Path("docs/project_quickstart_workflows.md")

    assert path.exists()

    text = path.read_text(encoding="utf-8")

    assert "python -m core.pipelines.run_xena_metadata_pipeline --recommended-only --make-report" in text
    assert "python -m core.pipelines.run_unified_public_omics_pipeline --make-report" in text
    assert "outputs/dataset_inventory/unified_public_cancer_omics_inventory.tsv" in text
    assert "outputs/reports/unified_public_cancer_omics_inventory_report.html" in text
    assert "metadata-only" in text.lower()


def test_readme_contains_workflow_section():
    path = Path("README.md")

    assert path.exists()

    text = path.read_text(encoding="utf-8")

    assert "<!-- OPENMULTIOMICS_WORKFLOWS_START -->" in text
    assert "<!-- OPENMULTIOMICS_WORKFLOWS_END -->" in text
    assert "Quickstart Workflows" in text
    assert "python -m core.pipelines.run_xena_metadata_pipeline --recommended-only --make-report" in text
    assert "python -m core.pipelines.run_unified_public_omics_pipeline --make-report" in text
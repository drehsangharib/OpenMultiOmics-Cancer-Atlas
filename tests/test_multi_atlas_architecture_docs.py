from pathlib import Path


def test_multi_atlas_architecture_doc_exists_and_mentions_core_layers():
    path = Path("docs/multi_atlas_architecture.md")

    assert path.exists()

    text = path.read_text(encoding="utf-8")

    assert "Layer A" in text
    assert "Layer B" in text
    assert "Layer C" in text
    assert "Layer D" in text

    assert "core.atlas.build_keyword_public_omics_atlas" in text
    assert "core.atlas.report_keyword_public_omics_atlas_qc" in text
    assert "core.atlas.build_keyword_public_omics_atlas_from_config" in text
    assert "core.atlas.run_keyword_public_omics_atlas_batch" in text


def test_project_roadmap_doc_exists_and_mentions_v0_2_0():
    path = Path("docs/project_roadmap_to_v0_2_0.md")

    assert path.exists()

    text = path.read_text(encoding="utf-8")

    assert "v0.2.0" in text
    assert "Reusable public cancer metadata atlas framework" in text
    assert "1I.1" in text
    assert "1I.2" in text
    assert "1I.3" in text
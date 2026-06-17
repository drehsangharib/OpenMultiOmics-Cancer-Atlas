from pathlib import Path


def test_v0_2_0_release_checklist_exists_and_mentions_core_criteria():
    path = Path("docs/v0_2_0_release_checklist.md")

    assert path.exists()

    text = path.read_text(encoding="utf-8")

    assert "v0.2.0 = Reusable public cancer metadata atlas framework" in text
    assert "Unified GDC + Xena public cancer omics inventory exists" in text
    assert "Generalized keyword atlas builder exists" in text
    assert "Atlas definition schema validation exists" in text
    assert "python -m pytest -q" in text
    assert "python -m core.atlas.run_full_keyword_public_omics_batch --atlases gbm luad" in text


def test_v0_2_0_release_summary_exists_and_mentions_release_scope():
    path = Path("docs/v0_2_0_release_summary.md")

    assert path.exists()

    text = path.read_text(encoding="utf-8")

    assert "v0.2.0 = Reusable public cancer metadata atlas framework" in text
    assert "Generalized keyword atlas builder" in text
    assert "Registry-driven atlas QC wrapper" in text
    assert "Atlas definition schema validation" in text
    assert "metadata-only" in text.lower()
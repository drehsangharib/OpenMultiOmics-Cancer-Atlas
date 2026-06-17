from pathlib import Path

import core.atlas.validate_atlas_definition as validator


def test_brca_definition_is_valid():
    path = Path("configs/atlas_definitions/brca.yaml")

    assert path.exists()

    config = validator.validate_config_file(path)

    assert config["atlas_name"] == "brca"
    assert "brca" in config["keywords"]
    assert "breast" in config["keywords"]
    assert "tcga-brca" in config["keywords"]
    assert config["make_report"] is True
    assert config["allowed_sources"] == ["gdc", "xena"]


def test_lgg_definition_is_valid():
    path = Path("configs/atlas_definitions/lgg.yaml")

    assert path.exists()

    config = validator.validate_config_file(path)

    assert config["atlas_name"] == "lgg"
    assert "lgg" in config["keywords"]
    assert "glioma" in config["keywords"]
    assert "brain" in config["keywords"]
    assert "tcga-lgg" in config["keywords"]
    assert config["make_report"] is True
    assert config["allowed_sources"] == ["gdc", "xena"]
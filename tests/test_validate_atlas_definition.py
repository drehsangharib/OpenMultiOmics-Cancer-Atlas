from pathlib import Path

import pytest
import yaml

import core.atlas.validate_atlas_definition as validator


def write_yaml(path: Path, data):
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)


def test_load_yaml_mapping(tmp_path: Path):
    config_path = tmp_path / "gbm.yaml"
    data = {
        "atlas_name": "gbm",
        "keywords": ["gbm", "glioblastoma", "brain"],
    }

    write_yaml(config_path, data)

    loaded = validator.load_yaml_mapping(config_path)

    assert loaded["atlas_name"] == "gbm"
    assert loaded["keywords"] == ["gbm", "glioblastoma", "brain"]


def test_validate_atlas_definition_data_good():
    data = {
        "atlas_name": "gbm",
        "keywords": ["gbm", "glioblastoma", "brain"],
        "min_priority": 3,
        "allowed_sources": ["gdc", "xena"],
        "make_report": True,
    }

    validated = validator.validate_atlas_definition_data(data, source_label="memory")

    assert validated["atlas_name"] == "gbm"
    assert validated["keywords"] == ["gbm", "glioblastoma", "brain"]
    assert validated["min_priority"] == 3
    assert validated["allowed_sources"] == ["gdc", "xena"]
    assert validated["make_report"] is True


def test_validate_atlas_definition_data_missing_atlas_name():
    data = {
        "keywords": ["gbm", "glioblastoma", "brain"],
    }

    with pytest.raises(ValueError):
        validator.validate_atlas_definition_data(data, source_label="memory")


def test_validate_atlas_definition_data_keywords_not_list():
    data = {
        "atlas_name": "gbm",
        "keywords": "gbm",
    }

    with pytest.raises(ValueError):
        validator.validate_atlas_definition_data(data, source_label="memory")


def test_validate_config_file(tmp_path: Path):
    config_path = tmp_path / "gbm.yaml"
    data = {
        "atlas_name": "gbm",
        "keywords": ["gbm", "glioblastoma", "brain"],
        "make_report": True,
    }

    write_yaml(config_path, data)

    validated = validator.validate_config_file(config_path)

    assert validated["atlas_name"] == "gbm"
    assert validated["keywords"] == ["gbm", "glioblastoma", "brain"]


def test_validate_config_dir(tmp_path: Path):
    config_dir = tmp_path / "atlas_definitions"
    config_dir.mkdir(parents=True)

    write_yaml(
        config_dir / "gbm.yaml",
        {
            "atlas_name": "gbm",
            "keywords": ["gbm", "glioblastoma", "brain"],
        },
    )

    write_yaml(
        config_dir / "luad.yaml",
        {
            "atlas_name": "luad",
            "keywords": ["luad", "lung", "adenocarcinoma"],
        },
    )

    summary_output = tmp_path / "validation_summary.tsv"

    summary_df = validator.validate_config_dir(
        config_dir,
        summary_output_path=summary_output,
    )

    assert summary_output.exists()
    assert summary_df.shape[0] == 2
    assert set(summary_df["atlas_name"]) == {"gbm", "luad"}


def test_build_arg_parser():
    parser = validator.build_arg_parser()
    args = parser.parse_args(["--config", "configs/atlas_definitions/gbm.yaml"])

    assert str(args.config).replace("\\", "/").endswith(
        "configs/atlas_definitions/gbm.yaml"
    )

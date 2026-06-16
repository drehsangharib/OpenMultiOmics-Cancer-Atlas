from pathlib import Path

import pandas as pd
import yaml

from core.atlas.run_keyword_public_omics_atlas_batch import (
    build_arg_parser,
    list_yaml_configs,
    run_keyword_public_omics_atlas_batch,
    select_configs,
)


def write_config(path: Path, atlas_name: str):
    config = {
        "atlas_name": atlas_name,
        "keywords": [atlas_name],
        "input": "dummy.tsv",
        "output": f"outputs/atlases/{atlas_name}/{atlas_name}_public_omics_atlas_inventory.tsv",
        "report": f"outputs/reports/{atlas_name}_public_omics_atlas_report.html",
        "make_report": True,
    }

    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, sort_keys=False)


def test_list_yaml_configs(tmp_path: Path):
    config_dir = tmp_path / "atlas_definitions"
    config_dir.mkdir(parents=True)

    write_config(config_dir / "gbm.yaml", "gbm")
    write_config(config_dir / "luad.yaml", "luad")

    configs = list_yaml_configs(config_dir)

    assert len(configs) == 2
    assert str(configs[0]).endswith(".yaml")


def test_select_configs(tmp_path: Path):
    config_dir = tmp_path / "atlas_definitions"
    config_dir.mkdir(parents=True)

    gbm_path = config_dir / "gbm.yaml"
    luad_path = config_dir / "luad.yaml"

    write_config(gbm_path, "gbm")
    write_config(luad_path, "luad")

    selected = select_configs([gbm_path, luad_path], atlas_names=["gbm"])

    assert len(selected) == 1
    assert selected[0].name == "gbm.yaml"


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


def test_run_keyword_public_omics_atlas_batch_with_monkeypatch(tmp_path: Path, monkeypatch):
    config_dir = tmp_path / "atlas_definitions"
    config_dir.mkdir(parents=True)

    gbm_path = config_dir / "gbm.yaml"
    luad_path = config_dir / "luad.yaml"

    write_config(gbm_path, "gbm")
    write_config(luad_path, "luad")

    def fake_build_keyword_public_omics_atlas_from_config(config_path):
        config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
        atlas_name = config["atlas_name"]

        output_path = tmp_path / f"{atlas_name}.tsv"
        report_path = tmp_path / f"{atlas_name}.html"

        df = pd.DataFrame(
            [
                {
                    "atlas_name": atlas_name,
                    "record_id": f"{atlas_name.upper()}-001",
                }
            ]
        )

        df.to_csv(output_path, sep="\t", index=False)
        report_path.write_text("<html>report</html>", encoding="utf-8")

        return df, output_path, report_path, config

    monkeypatch.setattr(
        "core.atlas.run_keyword_public_omics_atlas_batch.build_keyword_public_omics_atlas_from_config",
        fake_build_keyword_public_omics_atlas_from_config,
    )

    summary_output = tmp_path / "batch_summary.tsv"

    summary_df = run_keyword_public_omics_atlas_batch(
        config_dir=config_dir,
        atlas_names=["gbm", "luad"],
        summary_output_path=summary_output,
        open_reports=False,
    )

    assert summary_output.exists()
    assert summary_df.shape[0] == 2
    assert set(summary_df["atlas_name"]) == {"gbm", "luad"}
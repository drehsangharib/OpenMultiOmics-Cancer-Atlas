from pathlib import Path

import yaml

from core.atlas.run_keyword_public_omics_atlas_qc_batch import (
    build_arg_parser,
    list_yaml_configs,
    run_keyword_public_omics_atlas_qc_batch,
    select_configs,
)


def write_config(path: Path, atlas_name: str):
    config = {
        "atlas_name": atlas_name,
        "keywords": [atlas_name],
        "output": f"outputs/atlases/{atlas_name}/{atlas_name}_public_omics_atlas_inventory.tsv",
        "qc_report": f"outputs/reports/{atlas_name}_public_omics_atlas_qc_report.html",
        "qc_report_title": f"{atlas_name.upper()} Public Omics Atlas QC Report",
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


def test_run_keyword_public_omics_atlas_qc_batch_with_monkeypatch(tmp_path: Path, monkeypatch):
    config_dir = tmp_path / "atlas_definitions"
    config_dir.mkdir(parents=True)

    gbm_path = config_dir / "gbm.yaml"
    luad_path = config_dir / "luad.yaml"

    write_config(gbm_path, "gbm")
    write_config(luad_path, "luad")

    def fake_report_keyword_public_omics_atlas_qc_from_config(config_path):
        config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
        atlas_name = config["atlas_name"]

        output_path = tmp_path / f"{atlas_name}_qc.html"
        output_path.write_text("<html>QC report</html>", encoding="utf-8")
        report_html = f"<html>{atlas_name.upper()} QC report</html>"

        return report_html, output_path, config

    monkeypatch.setattr(
        "core.atlas.run_keyword_public_omics_atlas_qc_batch.report_keyword_public_omics_atlas_qc_from_config",
        fake_report_keyword_public_omics_atlas_qc_from_config,
    )

    summary_output = tmp_path / "atlas_qc_batch_summary.tsv"

    summary_df = run_keyword_public_omics_atlas_qc_batch(
        config_dir=config_dir,
        atlas_names=["gbm", "luad"],
        summary_output_path=summary_output,
        open_reports=False,
    )

    assert summary_output.exists()
    assert summary_df.shape[0] == 2
    assert set(summary_df["atlas_name"]) == {"gbm", "luad"}
    assert "qc_report_path" in summary_df.columns
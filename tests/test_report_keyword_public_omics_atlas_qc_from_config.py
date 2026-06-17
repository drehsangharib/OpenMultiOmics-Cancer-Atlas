from pathlib import Path

import yaml

from core.atlas.report_keyword_public_omics_atlas_qc_from_config import (
    build_arg_parser,
    report_keyword_public_omics_atlas_qc_from_config,
    resolve_qc_input_path,
    resolve_qc_output_path,
    resolve_qc_title,
)


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--config", "configs/atlas_definitions/gbm.yaml"])

    assert str(args.config).replace("\\", "/").endswith(
        "configs/atlas_definitions/gbm.yaml"
    )


def test_resolve_paths_and_title():
    config = {
        "atlas_name": "gbm",
        "output": "outputs/atlases/gbm/gbm_public_omics_atlas_inventory.tsv",
        "qc_report": "outputs/reports/gbm_public_omics_atlas_qc_report.html",
        "qc_report_title": "GBM Public Omics Atlas QC Report",
    }

    assert str(resolve_qc_input_path(config)).replace("\\", "/").endswith(
        "outputs/atlases/gbm/gbm_public_omics_atlas_inventory.tsv"
    )
    assert str(resolve_qc_output_path(config)).replace("\\", "/").endswith(
        "outputs/reports/gbm_public_omics_atlas_qc_report.html"
    )
    assert resolve_qc_title(config) == "GBM Public Omics Atlas QC Report"


def test_report_keyword_public_omics_atlas_qc_from_config(tmp_path: Path):
    input_path = tmp_path / "gbm.tsv"
    output_path = tmp_path / "gbm_qc.html"
    config_path = tmp_path / "gbm.yaml"

    input_path.write_text(
        "source_id\tsource_record_type\trecord_id\trecord_name\tproject_id\tdataset_id\thub_id\tomics_modality\tdata_category\tmatrix_type\tresource_family\tprimary_site\tdisease_type\tcancer_scope\tpriority_for_atlas\tsource_url\tatlas_match_terms\n"
        "xena\txena_dataset\tTCGA-GBM.star_tpm.tsv\tTCGA GBM STAR TPM\t\tTCGA-GBM.star_tpm.tsv\tgdc_xena\ttranscriptomics\tgene expression\tsample-by-gene expression matrix\tTCGA\tBrain\tGliomas\tTCGA cancer cohorts\t5\thttps://gdc.xenahubs.net/\tbrain;gbm;glioma\n",
        encoding="utf-8",
    )

    config = {
        "atlas_name": "gbm",
        "keywords": ["gbm", "glioblastoma", "brain"],
        "output": str(input_path),
        "qc_report": str(output_path),
        "qc_report_title": "GBM Public Omics Atlas QC Report",
    }

    with config_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, sort_keys=False)

    report_html, built_output_path, loaded_config = (
        report_keyword_public_omics_atlas_qc_from_config(config_path)
    )

    assert built_output_path.exists()
    assert loaded_config["atlas_name"] == "gbm"
    assert "GBM Public Omics Atlas QC Report" in report_html

    output_html = built_output_path.read_text(encoding="utf-8")
    assert "GBM Public Omics Atlas QC Report" in output_html
    assert "Total records" in output_html
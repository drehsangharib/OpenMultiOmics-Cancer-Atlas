from pathlib import Path

import pandas as pd
import yaml

from core.atlas.build_keyword_public_omics_atlas_from_config import (
    build_keyword_public_omics_atlas_from_config,
    build_arg_parser,
    load_atlas_definition,
    resolve_output_path,
    resolve_report_path,
)


def make_unified_df():
    return pd.DataFrame(
        [
            {
                "source_id": "gdc",
                "source_record_type": "gdc_project",
                "record_id": "TCGA-GBM",
                "record_name": "Glioblastoma Multiforme",
                "project_id": "TCGA-GBM",
                "dataset_id": "",
                "hub_id": "",
                "omics_modality": "clinical_annotation;snv;transcriptomics",
                "data_category": "GDC project metadata",
                "matrix_type": "project-level metadata",
                "resource_family": "TCGA",
                "primary_site": "Brain",
                "disease_type": "Gliomas",
                "cancer_scope": "GDC project/cohort",
                "priority_for_atlas": 5,
                "source_url": "https://portal.gdc.cancer.gov/projects/TCGA-GBM",
                "notes": "GBM project",
            },
            {
                "source_id": "xena",
                "source_record_type": "xena_dataset",
                "record_id": "TCGA-GBM.star_tpm.tsv",
                "record_name": "TCGA GBM STAR TPM",
                "project_id": "",
                "dataset_id": "TCGA-GBM.star_tpm.tsv",
                "hub_id": "gdc_xena",
                "omics_modality": "transcriptomics",
                "data_category": "gene expression",
                "matrix_type": "sample-by-gene expression matrix",
                "resource_family": "TCGA",
                "primary_site": "",
                "disease_type": "",
                "cancer_scope": "TCGA cancer cohorts",
                "priority_for_atlas": 5,
                "source_url": "https://gdc.xenahubs.net/",
                "notes": "GBM dataset",
            },
            {
                "source_id": "xena",
                "source_record_type": "xena_dataset",
                "record_id": "TCGA-LUAD.star_tpm.tsv",
                "record_name": "TCGA LUAD STAR TPM",
                "project_id": "",
                "dataset_id": "TCGA-LUAD.star_tpm.tsv",
                "hub_id": "gdc_xena",
                "omics_modality": "transcriptomics",
                "data_category": "gene expression",
                "matrix_type": "sample-by-gene expression matrix",
                "resource_family": "TCGA",
                "primary_site": "Lung",
                "disease_type": "Adenocarcinoma",
                "cancer_scope": "TCGA cancer cohorts",
                "priority_for_atlas": 4,
                "source_url": "https://gdc.xenahubs.net/",
                "notes": "LUAD dataset",
            },
        ]
    )


def test_load_atlas_definition(tmp_path: Path):
    config_path = tmp_path / "gbm.yaml"
    config = {
        "atlas_name": "gbm",
        "keywords": ["gbm", "glioblastoma", "brain"],
        "make_report": True,
    }

    with config_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, sort_keys=False)

    loaded = load_atlas_definition(config_path)

    assert loaded["atlas_name"] == "gbm"
    assert loaded["keywords"] == ["gbm", "glioblastoma", "brain"]


def test_resolve_paths_defaults():
    config = {
        "atlas_name": "gbm",
        "keywords": ["gbm", "glioblastoma", "brain"],
    }

    assert str(resolve_output_path(config)).replace("\\", "/").endswith(
        "outputs/atlases/gbm/gbm_public_omics_atlas_inventory.tsv"
    )
    assert str(resolve_report_path(config)).replace("\\", "/").endswith(
        "outputs/reports/gbm_public_omics_atlas_report.html"
    )


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--config", "configs/atlas_definitions/gbm.yaml"])

    assert str(args.config).replace("\\", "/").endswith("configs/atlas_definitions/gbm.yaml")


def test_build_keyword_public_omics_atlas_from_config(tmp_path: Path):
    input_path = tmp_path / "unified.tsv"
    output_path = tmp_path / "gbm.tsv"
    report_path = tmp_path / "gbm_report.html"
    config_path = tmp_path / "gbm.yaml"

    make_unified_df().to_csv(input_path, sep="\t", index=False)

    config = {
        "atlas_name": "gbm",
        "keywords": ["gbm", "glioblastoma", "brain"],
        "input": str(input_path),
        "output": str(output_path),
        "report": str(report_path),
        "report_title": "GBM Public Omics Atlas Inventory Report",
        "min_priority": 3,
        "allowed_sources": ["gdc", "xena"],
        "make_report": True,
    }

    with config_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, sort_keys=False)

    atlas_df, built_output_path, built_report_path, loaded_config = build_keyword_public_omics_atlas_from_config(config_path)

    assert built_output_path.exists()
    assert built_report_path.exists()
    assert atlas_df.shape[0] == 2
    assert loaded_config["atlas_name"] == "gbm"

    loaded = pd.read_csv(built_output_path, sep="\t")
    assert loaded.shape[0] == 2
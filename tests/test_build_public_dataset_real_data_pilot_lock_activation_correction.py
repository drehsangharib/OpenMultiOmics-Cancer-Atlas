from pathlib import Path
import pandas as pd
import yaml
from core.data.build_public_dataset_real_data_pilot_lock_activation_correction import (
    build_arg_parser,
    build_public_dataset_real_data_pilot_lock_activation_correction,
)


def test_build_public_dataset_real_data_pilot_lock_activation_correction(tmp_path: Path):
    intake = tmp_path / "intake.tsv"
    schema = tmp_path / "schema.tsv"
    master = tmp_path / "master.tsv"
    prev_selection = tmp_path / "selection.tsv"
    prev_smoke = tmp_path / "smoke.tsv"
    request = tmp_path / "request.yaml"
    out = tmp_path / "out"
    brca_file = tmp_path / "brca.tsv"
    brca_file.write_text("gene_id\tS1\nENSG1\t1.0\n", encoding="utf-8")
    pd.DataFrame([
        {"dataset_id":"tcga_brca_transcriptomics","intake_status":"target_file_present","target_local_path":str(brca_file),"target_local_path_exists_current":1},
        {"dataset_id":"tcga_gbm_epigenome","intake_status":"awaiting_file","target_local_path":str(tmp_path/"gbm.tsv"),"target_local_path_exists_current":0},
        {"dataset_id":"empty_path_dataset","intake_status":"awaiting_file","target_local_path":"","target_local_path_exists_current":""},
    ]).to_csv(intake, sep="\t", index=False)
    pd.DataFrame([
        {"dataset_id":"tcga_brca_transcriptomics","modality":"transcriptomics","schema_validation_status":"validated_modality_schema","schema_file_exists":1,"schema_file_readable":1},
        {"dataset_id":"tcga_gbm_epigenome","modality":"epigenome","schema_validation_status":"skipped_awaiting_file","schema_file_exists":0,"schema_file_readable":0},
        {"dataset_id":"empty_path_dataset","modality":"transcriptomics","schema_validation_status":"skipped_awaiting_file","schema_file_exists":0,"schema_file_readable":0},
    ]).to_csv(schema, sep="\t", index=False)
    pd.DataFrame([
        {"dataset_id":"tcga_brca_transcriptomics","source_id":"gdc_tcga","accession_or_project_id":"TCGA-BRCA","replacement_priority":1,"portal_url":"https://portal.gdc.cancer.gov/projects/TCGA-BRCA"},
        {"dataset_id":"tcga_gbm_epigenome","source_id":"gdc_tcga","accession_or_project_id":"TCGA-GBM","replacement_priority":2,"portal_url":"https://portal.gdc.cancer.gov/projects/TCGA-GBM"},
    ]).to_csv(master, sep="\t", index=False)
    pd.DataFrame([{"dataset_id":"tcga_gbm_epigenome"}]).to_csv(prev_selection, sep="\t", index=False)
    pd.DataFrame([{"dataset_id":"tcga_gbm_epigenome"}]).to_csv(prev_smoke, sep="\t", index=False)
    with request.open("w", encoding="utf-8") as h:
        yaml.safe_dump({"request_id":"test_lock","atlas_name":"test_public","inputs":{"real_file_intake_inventory":str(intake),"modality_schema_validation_table":str(schema),"real_acquisition_master_plan":str(master),"first_real_pilot_selection":str(prev_selection),"real_data_smoke_test_state":str(prev_smoke)},"expected_outputs":{"real_data_pilot_lock_dir":str(out)}}, h, sort_keys=False)
    summary, validated, locked, corrected, audit, paths = build_public_dataset_real_data_pilot_lock_activation_correction(request_path=request)
    assert paths["validated_real_file_inventory"].exists()
    assert paths["locked_pilot"].exists()
    assert paths["corrected_smoke_state"].exists()
    assert paths["correction_audit"].exists()
    assert paths["summary"].exists()
    assert paths["report"].exists()
    assert summary["locked_pilot_dataset_ids"] == ["tcga_brca_transcriptomics"]
    assert summary["activation_ready_count"] == 1
    assert summary["primary_blocking_reason"] == "none"
    assert corrected.loc[0, "blocking_reason"] == "none"
    empty_row = validated[validated["dataset_id"] == "empty_path_dataset"].iloc[0]
    assert int(empty_row["target_file_present"]) == 0


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--request", "request.yaml", "--output-dir", "out"])
    assert str(args.request).endswith("request.yaml")
    assert str(args.output_dir).endswith("out")

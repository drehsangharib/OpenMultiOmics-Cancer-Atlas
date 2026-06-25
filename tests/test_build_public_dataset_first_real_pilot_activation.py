from pathlib import Path
import pandas as pd
import yaml
from core.data.build_public_dataset_first_real_pilot_activation import build_arg_parser, build_public_dataset_first_real_pilot_activation


def test_build_public_dataset_first_real_pilot_activation(tmp_path: Path):
    master = tmp_path / "master.tsv"
    priority = tmp_path / "priority.tsv"
    summary = tmp_path / "summary.yaml"
    request = tmp_path / "request.yaml"
    out = tmp_path / "pilot"
    rows = [
        {"dataset_id":"tcga_brca_transcriptomics","display_name":"TCGA-BRCA","source_id":"gdc_tcga","accession_or_project_id":"TCGA-BRCA","atlas_hint":"brca","modality":"transcriptomics","expected_file_type":"matrix","replacement_priority":1,"target_local_path":str(tmp_path/"brca.tsv"),"portal_url":"https://portal.gdc.cancer.gov/projects/TCGA-BRCA","source_packet_yaml":"packet.yaml","dropzone_dir":"dropzone","command_template":"download","requires_accession_resolution":0,"ready_to_acquire":1,"target_file_present":0,"candidate_file_count":0,"intake_status":"awaiting_file","schema_validation_status":"skipped_awaiting_file","schema_candidate_file":"","acquisition_blocker":"none","operator_next_step":"acquire","post_acquisition_rerun_sequence":"rerun"},
        {"dataset_id":"metabolomics_workbench_cancer_metabolomics","display_name":"MWB","source_id":"metabolomics_workbench","accession_or_project_id":"REPLACE_WITH_STUDY_ACCESSION","atlas_hint":"multi","modality":"metabolomics","expected_file_type":"matrix","replacement_priority":2,"target_local_path":str(tmp_path/"mw.tsv"),"portal_url":"https://www.metabolomicsworkbench.org/data/","source_packet_yaml":"packet2.yaml","dropzone_dir":"dropzone2","command_template":"resolve","requires_accession_resolution":1,"ready_to_acquire":0,"target_file_present":0,"candidate_file_count":0,"intake_status":"awaiting_file","schema_validation_status":"skipped_awaiting_file","schema_candidate_file":"","acquisition_blocker":"placeholder","operator_next_step":"resolve","post_acquisition_rerun_sequence":"rerun"},
    ]
    pd.DataFrame(rows).to_csv(master, sep="\t", index=False)
    pd.DataFrame(rows).to_csv(priority, sep="\t", index=False)
    with summary.open("w", encoding="utf-8") as h:
        yaml.safe_dump({"request_id":"upstream_a33","output_dir":str(tmp_path)}, h, sort_keys=False)
    with request.open("w", encoding="utf-8") as h:
        yaml.safe_dump({"request_id":"test_pilot","atlas_name":"test_public","inputs":{"real_acquisition_master_plan":str(master),"real_acquisition_priority_queue":str(priority),"real_acquisition_summary":str(summary)},"expected_outputs":{"first_real_pilot_activation_dir":str(out)}}, h, sort_keys=False)
    s, pilot, readiness, activation, handoff, paths = build_public_dataset_first_real_pilot_activation(request_path=request)
    assert paths["pilot_selection"].exists()
    assert paths["pilot_readiness"].exists()
    assert paths["activation_plan"].exists()
    assert paths["feature_store_handoff_plan"].exists()
    assert paths["validation_rerun_plan"].exists()
    assert paths["operator_workbook"].exists()
    assert paths["summary"].exists()
    assert paths["report"].exists()
    assert s["selected_pilot_count"] == 1
    assert s["selected_pilot_dataset_ids"] == ["tcga_brca_transcriptomics"]
    assert s["pilot_ready_for_file_placement_count"] == 1
    assert pilot.loc[0, "modality"] == "transcriptomics"


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--request", "request.yaml", "--output-dir", "out"])
    assert str(args.request).endswith("request.yaml")
    assert str(args.output_dir).endswith("out")

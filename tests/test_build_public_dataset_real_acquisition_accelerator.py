from pathlib import Path
import pandas as pd
import yaml
from core.data.build_public_dataset_real_acquisition_accelerator import build_arg_parser, build_public_dataset_real_acquisition_accelerator

def test_build_public_dataset_real_acquisition_accelerator(tmp_path: Path):
    packets=tmp_path/"packets.tsv"; summary=tmp_path/"summary.yaml"; inventory=tmp_path/"inventory.tsv"; request=tmp_path/"request.yaml"; out=tmp_path/"accelerator"
    pd.DataFrame([
        {"dataset_id":"dataset_a","display_name":"Dataset A","source_id":"gdc_tcga","accession_or_project_id":"TCGA-TEST","atlas_hint":"brca","modality":"transcriptomics","expected_file_type":"matrix","replacement_priority":1,"target_local_path":str(tmp_path/"real.tsv"),"portal_url":"https://portal.gdc.cancer.gov/projects/TCGA-TEST","command_template":"download","operator_next_step":"acquire"},
        {"dataset_id":"dataset_b","display_name":"Dataset B","source_id":"metabolomics_workbench","accession_or_project_id":"REPLACE_WITH_STUDY_ACCESSION","atlas_hint":"multi","modality":"metabolomics","expected_file_type":"matrix","replacement_priority":2,"target_local_path":str(tmp_path/"met.tsv"),"portal_url":"https://www.metabolomicsworkbench.org/data/","command_template":"resolve","operator_next_step":"resolve"},
    ]).to_csv(packets,sep="\t",index=False)
    with summary.open("w",encoding="utf-8") as h: yaml.safe_dump({"request_id":"upstream_source","output_dir":str(tmp_path)},h,sort_keys=False)
    pd.DataFrame([{"dataset_id":"dataset_a","source_packet_yaml":str(tmp_path/"a.yaml"),"source_packet_yaml_exists":1}]).to_csv(inventory,sep="\t",index=False)
    with request.open("w",encoding="utf-8") as h:
        yaml.safe_dump({"request_id":"test_accelerator","atlas_name":"test_public","inputs":{"source_access_packets":str(packets),"source_access_summary":str(summary),"source_packet_yaml_inventory":str(inventory)},"expected_outputs":{"real_acquisition_accelerator_dir":str(out)}},h,sort_keys=False)
    s,master,priority,accession,target,paths=build_public_dataset_real_acquisition_accelerator(request_path=request)
    assert paths["master_plan"].exists(); assert paths["priority_queue"].exists(); assert paths["accession_resolution"].exists(); assert paths["validation_rerun_plan"].exists(); assert paths["operator_workbook"].exists(); assert paths["summary"].exists(); assert paths["report"].exists()
    assert s["dataset_count"]==2; assert s["ready_to_acquire_count"]==1; assert s["requires_accession_resolution_count"]==1
    assert not priority.empty; assert not accession.empty; assert not target.empty

def test_build_arg_parser():
    parser=build_arg_parser(); args=parser.parse_args(["--request","request.yaml","--output-dir","out"])
    assert str(args.request).endswith("request.yaml"); assert str(args.output_dir).endswith("out")

from pathlib import Path
import pandas as pd
import yaml
from core.data.build_public_dataset_pilot_execution_orchestrator import build_arg_parser, build_public_dataset_pilot_execution_orchestrator


def test_build_public_dataset_pilot_execution_orchestrator(tmp_path: Path):
    selection = tmp_path / "selection.tsv"
    readiness = tmp_path / "readiness.tsv"
    activation = tmp_path / "activation.tsv"
    handoff = tmp_path / "handoff.tsv"
    summary = tmp_path / "summary.yaml"
    request = tmp_path / "request.yaml"
    out = tmp_path / "orchestrator"
    dataset_id = "tcga_brca_transcriptomics"
    pd.DataFrame([{"dataset_id":dataset_id,"source_id":"gdc_tcga","accession_or_project_id":"TCGA-BRCA","modality":"transcriptomics","target_local_path":str(tmp_path/"brca.tsv"),"pilot_status":"ready_for_real_file_drop"}]).to_csv(selection, sep="\t", index=False)
    pd.DataFrame([{"dataset_id":dataset_id,"readiness_status":"ready_for_file_placement"}]).to_csv(readiness, sep="\t", index=False)
    pd.DataFrame([{"dataset_id":dataset_id,"activation_status":"activation_waiting_for_real_file"}]).to_csv(activation, sep="\t", index=False)
    pd.DataFrame([{"dataset_id":dataset_id,"feature_store_handoff_status":"waiting_for_validated_real_file"}]).to_csv(handoff, sep="\t", index=False)
    with summary.open("w", encoding="utf-8") as h:
        yaml.safe_dump({"request_id":"upstream_a34"}, h, sort_keys=False)
    with request.open("w", encoding="utf-8") as h:
        yaml.safe_dump({"request_id":"test_orchestrator","atlas_name":"test_public","inputs":{"first_real_pilot_selection":str(selection),"first_real_pilot_readiness":str(readiness),"first_real_pilot_activation_plan":str(activation),"first_real_pilot_feature_store_handoff_plan":str(handoff),"first_real_pilot_summary":str(summary)},"expected_outputs":{"pilot_execution_orchestrator_dir":str(out)}}, h, sort_keys=False)
    s, state, gates, activation_q, handoff_q, paths = build_public_dataset_pilot_execution_orchestrator(request_path=request)
    assert paths["orchestrator_state"].exists()
    assert paths["validation_gate_table"].exists()
    assert paths["manifest_activation_queue"].exists()
    assert paths["feature_store_handoff_queue"].exists()
    assert paths["rerun_script"].exists()
    assert paths["operator_runbook"].exists()
    assert paths["summary"].exists()
    assert paths["report"].exists()
    assert s["pilot_dataset_count"] == 1
    assert s["waiting_for_real_file_count"] == 1
    assert state.loc[0, "orchestrator_status"] == "waiting_for_real_file"
    assert not gates.empty
    assert not activation_q.empty
    assert not handoff_q.empty


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--request", "request.yaml", "--output-dir", "out"])
    assert str(args.request).endswith("request.yaml")
    assert str(args.output_dir).endswith("out")

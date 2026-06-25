from pathlib import Path
import pandas as pd
import yaml
from core.data.build_public_dataset_real_data_smoke_test_activation import build_arg_parser, build_public_dataset_real_data_smoke_test_activation


def test_build_public_dataset_real_data_smoke_test_activation(tmp_path: Path):
    state = tmp_path / "state.tsv"
    pilot_summary = tmp_path / "summary.yaml"
    request = tmp_path / "request.yaml"
    out = tmp_path / "smoke"
    dataset_id = "tcga_brca_transcriptomics"
    pd.DataFrame([{"dataset_id":dataset_id,"source_id":"gdc_tcga","modality":"transcriptomics","target_local_path":str(tmp_path/"missing.tsv"),"orchestrator_status":"waiting_for_real_file","file_validation_status":"not_available","schema_validation_status":"not_available"}]).to_csv(state, sep="\t", index=False)
    with pilot_summary.open("w", encoding="utf-8") as h:
        yaml.safe_dump({"request_id":"upstream_a35"}, h, sort_keys=False)
    with request.open("w", encoding="utf-8") as h:
        yaml.safe_dump({"request_id":"test_smoke","atlas_name":"test_public","inputs":{"pilot_execution_orchestrator_state":str(state),"pilot_execution_summary":str(pilot_summary)},"expected_outputs":{"real_data_smoke_test_activation_dir":str(out)}}, h, sort_keys=False)
    s, smoke_state, blocker, activation, handoff, paths = build_public_dataset_real_data_smoke_test_activation(request_path=request)
    assert paths["smoke_test_state"].exists()
    assert paths["blocker_report"].exists()
    assert paths["activation_artifact_plan"].exists()
    assert paths["feature_store_handoff_artifact_plan"].exists()
    assert paths["rerun_script"].exists()
    assert paths["operator_runbook"].exists()
    assert paths["summary"].exists()
    assert paths["report"].exists()
    assert s["pilot_dataset_count"] == 1
    assert s["real_file_present_count"] == 0
    assert s["validation_passed_count"] == 0
    assert s["primary_blocking_reason"] == "missing_real_file"
    assert not blocker.empty


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--request", "request.yaml", "--output-dir", "out"])
    assert str(args.request).endswith("request.yaml")
    assert str(args.output_dir).endswith("out")

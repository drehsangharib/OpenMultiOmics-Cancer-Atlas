from pathlib import Path

import pandas as pd
import yaml

from core.data.build_public_dataset_source_access_packet import (
    build_arg_parser,
    build_public_dataset_source_access_packet,
)


def test_build_public_dataset_source_access_packet(tmp_path: Path):
    registry = tmp_path / "registry.yaml"
    task_board = tmp_path / "task_board.tsv"
    intake = tmp_path / "intake.tsv"
    schema = tmp_path / "schema.tsv"
    request = tmp_path / "request.yaml"
    output_dir = tmp_path / "source_packets"
    with registry.open("w", encoding="utf-8") as handle:
        yaml.safe_dump({"datasets": {"dataset_a": {"display_name": "Dataset A", "source_id": "gdc_tcga", "accession_or_project_id": "TCGA-TEST", "atlas_hint": "brca", "modality": "transcriptomics", "expected_file_type": "matrix", "replacement_priority": 1, "local_replacement_path": str(tmp_path / "real.tsv"), "notes": "test"}}}, handle, sort_keys=False)
    pd.DataFrame([{"dataset_id": "dataset_a", "task_status": "open_pending_acquisition", "target_local_path": str(tmp_path / "real.tsv"), "operator_action": "Acquire"}]).to_csv(task_board, sep="\t", index=False)
    pd.DataFrame([{"dataset_id": "dataset_a", "intake_status": "awaiting_file", "candidate_file_count": 0, "dropzone_dir": str(tmp_path / "dropzone")}]).to_csv(intake, sep="\t", index=False)
    pd.DataFrame([{"dataset_id": "dataset_a", "schema_validation_status": "skipped_awaiting_file", "schema_candidate_file": ""}]).to_csv(schema, sep="\t", index=False)
    with request.open("w", encoding="utf-8") as handle:
        yaml.safe_dump({"request_id": "test_source_packet", "atlas_name": "test_public", "inputs": {"dataset_accession_registry": str(registry), "acquisition_task_board": str(task_board), "real_file_intake_inventory": str(intake), "modality_schema_validation_table": str(schema)}, "expected_outputs": {"source_access_packet_dir": str(output_dir)}}, handle, sort_keys=False)
    summary, packet_df, inventory_df, paths = build_public_dataset_source_access_packet(request_path=request)
    assert paths["source_access_packets"].exists()
    assert paths["portal_link_table"].exists()
    assert paths["command_templates"].exists()
    assert paths["packet_yaml_inventory"].exists()
    assert paths["source_access_summary"].exists()
    assert paths["source_access_report"].exists()
    assert summary["source_packet_count"] == 1
    assert summary["packet_yaml_count"] == 1
    assert "TCGA-TEST" in packet_df.loc[0, "portal_url"]
    assert Path(inventory_df.loc[0, "source_packet_yaml"]).exists()


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--request", "request.yaml", "--output-dir", "out"])
    assert str(args.request).endswith("request.yaml")
    assert str(args.output_dir).endswith("out")

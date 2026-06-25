# Public Dataset Pilot Execution Orchestrator Bundle

## Version

`v0.4.0-a35`

## Purpose

This larger milestone combines first-real-pilot validation gates, manifest activation planning, and feature-store handoff queue generation into one orchestrator.

It does not download data, create real replacement files, or overwrite manifests. It produces readiness state and queued activation/handoff outputs that become active only after the real file is placed and validation passes.

## Outputs

```text
public_dataset_pilot_execution_orchestrator_state.tsv
public_dataset_pilot_execution_validation_gate_table.tsv
public_dataset_pilot_manifest_activation_queue.tsv
public_dataset_pilot_feature_store_handoff_queue.tsv
public_dataset_pilot_execution_full_rerun_plan.ps1
public_dataset_pilot_execution_operator_runbook.md
public_dataset_pilot_execution_orchestrator_summary.yaml
public_dataset_pilot_execution_orchestrator_report.html
```

## Expected result after a34

```text
pilot_dataset_count: 1
waiting_for_real_file_count: 1
file_present_validation_required_count: 0
ready_for_activation_count: 0
manifest_activation_queue_count: 1
feature_store_handoff_queue_count: 1
```

## Run

```powershell
python -m core.data.build_public_dataset_pilot_execution_orchestrator
```

## Validate

```powershell
python -m py_compile core\datauild_public_dataset_pilot_execution_orchestrator.py
python -m py_compile tests	est_build_public_dataset_pilot_execution_orchestrator.py
python -m pytest tests	est_build_public_dataset_pilot_execution_orchestrator.py -q
python -m pytest -q
```

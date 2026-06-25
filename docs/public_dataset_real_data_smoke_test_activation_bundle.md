# Real Data Smoke-Test Activation Bundle

## Version

`v0.4.0-a36`

## Purpose

This larger milestone provides the first true real-data smoke-test controller. It detects whether the first selected pilot real file is present, rolls up file/schema validation state, identifies blockers, and prepares activation/handoff artifact plans once validation passes.

It does not download data, create real replacement files, or overwrite original manifests.

## Outputs

```text
public_dataset_real_data_smoke_test_state.tsv
public_dataset_real_data_smoke_test_blocker_report.tsv
public_dataset_real_data_activation_artifact_plan.tsv
public_dataset_real_data_feature_store_handoff_artifact_plan.tsv
public_dataset_real_data_smoke_test_full_rerun_plan.ps1
public_dataset_real_data_smoke_test_operator_runbook.md
public_dataset_real_data_smoke_test_summary.yaml
public_dataset_real_data_smoke_test_report.html
```

## Expected result before file placement

```text
pilot_dataset_count: 1
real_file_present_count: 0
validation_passed_count: 0
activation_ready_count: 0
feature_store_handoff_ready_count: 0
primary_blocking_reason: missing_real_file
```

## Run

```powershell
python -m core.data.build_public_dataset_real_data_smoke_test_activation
```

## Validate

```powershell
python -m py_compile core\datauild_public_dataset_real_data_smoke_test_activation.py
python -m py_compile tests	est_build_public_dataset_real_data_smoke_test_activation.py
python -m pytest tests	est_build_public_dataset_real_data_smoke_test_activation.py -q
python -m pytest -q
```

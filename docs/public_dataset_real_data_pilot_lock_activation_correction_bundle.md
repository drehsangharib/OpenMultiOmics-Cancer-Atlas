# Real Data Pilot Lock + Activation Correction Bundle

## Version

`v0.4.0-a37`

## Purpose

This patch fixes the real-data pilot selection issue observed after TCGA-BRCA became file-present and schema-validated. Previous pilot selection logic could switch from BRCA to a missing GBM dataset because it prioritized targets still needing acquisition.

This corrected export also patches the runtime bug where empty `target_local_path` values could be converted to `int("")` during target-file detection.

## Outputs

```text
public_dataset_validated_real_file_inventory.tsv
public_dataset_locked_real_data_pilot.tsv
public_dataset_corrected_real_data_smoke_test_state.tsv
public_dataset_real_data_pilot_lock_correction_audit.tsv
public_dataset_real_data_pilot_lock_rerun_plan.ps1
public_dataset_real_data_pilot_lock_operator_runbook.md
public_dataset_real_data_pilot_lock_summary.yaml
public_dataset_real_data_pilot_lock_report.html
```

## Expected result with current BRCA real data

```text
validated_real_file_candidate_count: 1
locked_pilot_dataset_ids:
  - tcga_brca_transcriptomics
real_file_present_count: 1
validation_passed_count: 1
activation_ready_count: 1
feature_store_handoff_ready_count: 1
primary_blocking_reason: none
```

## Run

```powershell
python -m core.data.build_public_dataset_real_data_pilot_lock_activation_correction
```

## Validate

```powershell
python -m py_compile core\datauild_public_dataset_real_data_pilot_lock_activation_correction.py
python -m py_compile tests	est_build_public_dataset_real_data_pilot_lock_activation_correction.py
python -m pytest tests	est_build_public_dataset_real_data_pilot_lock_activation_correction.py -q
python -m pytest -q
```

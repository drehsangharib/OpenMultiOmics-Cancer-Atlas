# Public Dataset First Real Pilot Activation Bundle

## Version

`v0.4.0-a34`

## Purpose

This milestone moves from broad acquisition planning into a concrete first-real-dataset pilot. It selects the highest-priority ready-to-acquire dataset, prepares file-placement readiness, activation planning, and feature-store handoff planning.

Current expected first pilot is `tcga_brca_transcriptomics`, because it is the highest-priority ready-to-acquire dataset after the a33 accelerator bundle.

## Outputs

```text
public_dataset_first_real_pilot_selection.tsv
public_dataset_first_real_pilot_readiness.tsv
public_dataset_first_real_pilot_activation_plan.tsv
public_dataset_first_real_pilot_feature_store_handoff_plan.tsv
public_dataset_first_real_pilot_validation_rerun_plan.ps1
public_dataset_first_real_pilot_operator_workbook.md
public_dataset_first_real_pilot_summary.yaml
public_dataset_first_real_pilot_report.html
```

## Expected result after a33

```text
selected_pilot_count: 1
selected_pilot_dataset_ids:
  - tcga_brca_transcriptomics
pilot_target_file_present_count: 0
pilot_ready_for_file_placement_count: 1
activation_waiting_count: 1
handoff_waiting_count: 1
```

## Run

```powershell
python -m core.data.build_public_dataset_first_real_pilot_activation
```

## Validate

```powershell
python -m py_compile core\datauild_public_dataset_first_real_pilot_activation.py
python -m py_compile tests	est_build_public_dataset_first_real_pilot_activation.py
python -m pytest tests	est_build_public_dataset_first_real_pilot_activation.py -q
python -m pytest -q
```

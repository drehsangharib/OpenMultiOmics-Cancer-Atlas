# Public Dataset Real File Intake Bundle

## Version

`v0.4.0-a30`

## Purpose

This larger milestone creates a standardized real-file intake/drop-zone layer from the `v0.4.0-a29` acquisition operations outputs.

It creates per-dataset dropzone directories and README files, scans for candidate files, and writes an intake inventory/report. It does not download public data and does not create or modify real replacement files.

## Inputs

```text
configs/public_data_sources/public_dataset_real_file_intake_request.yaml
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_acquisition_operations/public_dataset_acquisition_task_board.tsv
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_acquisition_operations/public_dataset_acquisition_operations_summary.yaml
```

## Outputs

```text
outputs/public_data_acquisition/multi_cancer_realdata_pilot/real_file_intake/public_dataset_real_file_intake_inventory.tsv
outputs/public_data_acquisition/multi_cancer_realdata_pilot/real_file_intake/public_dataset_real_file_dropzone_readme_inventory.tsv
outputs/public_data_acquisition/multi_cancer_realdata_pilot/real_file_intake/public_dataset_real_file_intake_summary.yaml
outputs/public_data_acquisition/multi_cancer_realdata_pilot/real_file_intake/public_dataset_real_file_intake_report.html
data/public/multi_cancer_realdata_pilot/real_file_dropzone/<atlas>/<modality>/<dataset_id>/README.md
```

## Expected result after a29

```text
dataset_count: 4
dropzone_dir_count: 4
dropzone_readme_count: 4
candidate_file_count: 0
target_file_present_count: 0
awaiting_file_count: 4
```

## Run

```powershell
python -m core.data.build_public_dataset_real_file_intake_bundle
```

## Validate

```powershell
python -m py_compile core\datauild_public_dataset_real_file_intake_bundle.py
python -m py_compile tests	est_build_public_dataset_real_file_intake_bundle.py
python -m pytest tests	est_build_public_dataset_real_file_intake_bundle.py -q
python -m pytest -q
```

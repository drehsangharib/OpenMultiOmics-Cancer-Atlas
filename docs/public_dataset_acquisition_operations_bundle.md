# Public Dataset Acquisition Operations Bundle

## Version

`v0.4.0-a29`

## Purpose

This larger milestone bundles acquisition operations into one subsystem. It consumes the `v0.4.0-a28` acquisition status dashboard and produces an operational task board, checklist, source-specific acquisition templates, and progress rollup.

## Inputs

Default request file:

```text
configs/public_data_sources/public_dataset_acquisition_operations_request.yaml
```

Main input artifacts:

```text
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_acquisition_status_dashboard/public_dataset_acquisition_status_dashboard.tsv
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_acquisition_status_dashboard/public_dataset_acquisition_status_summary.yaml
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_acquisition_status_dashboard/public_dataset_acquisition_status_by_source.tsv
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_acquisition_status_dashboard/public_dataset_acquisition_status_by_modality.tsv
```

## Outputs

Default output directory:

```text
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_acquisition_operations
```

Generated files:

```text
public_dataset_acquisition_task_board.tsv
public_dataset_acquisition_checklist.md
public_dataset_acquisition_source_templates.tsv
public_dataset_acquisition_progress_rollup.tsv
public_dataset_acquisition_operations_summary.yaml
public_dataset_acquisition_operations_report.html
```

## Expected result after a28

```text
dataset_count: 4
tasks_open: 4
tasks_complete: 0
source_template_count: 3
modalities_covered: 4
```

## Run

```powershell
python -m core.data.build_public_dataset_acquisition_operations_bundle
```

## Validate

```powershell
python -m py_compile core\datauild_public_dataset_acquisition_operations_bundle.py
python -m py_compile tests	est_build_public_dataset_acquisition_operations_bundle.py
python -m pytest tests	est_build_public_dataset_acquisition_operations_bundle.py -q
python -m pytest -q
```

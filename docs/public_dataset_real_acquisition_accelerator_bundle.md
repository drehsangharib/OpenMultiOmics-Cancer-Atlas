# Public Dataset Real Acquisition Accelerator Bundle

## Version

`v0.4.0-a33`

## Purpose

This larger milestone consolidates source access packets, intake state, and modality-schema validation state into an operator-ready real public-data acquisition accelerator.

It generates a master acquisition plan, priority queue, accession-resolution queue, target-path plan, validation rerun script, operator workbook, summary, and report.

## Re-export correction

This package was re-exported with a safer optional-input table reader. Missing optional request inputs now return an empty table instead of resolving to `Path('.')`, which prevents a Windows `PermissionError` during unit tests when optional artifacts are intentionally omitted.

## Expected result after a32

```text
dataset_count: 4
ready_to_acquire_count: 3
requires_accession_resolution_count: 1
target_file_present_count: 0
post_acquisition_validation_plan_count: 4
```

## Run

```powershell
python -m core.data.build_public_dataset_real_acquisition_accelerator
```

## Validate

```powershell
python -m py_compile core\datauild_public_dataset_real_acquisition_accelerator.py
python -m py_compile tests	est_build_public_dataset_real_acquisition_accelerator.py
python -m pytest tests	est_build_public_dataset_real_acquisition_accelerator.py -q
python -m pytest -q
```

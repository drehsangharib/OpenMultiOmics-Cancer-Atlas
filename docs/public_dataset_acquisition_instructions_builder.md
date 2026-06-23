# Public Dataset Acquisition Instructions Builder

## Version

`v0.4.0-a26`

## Purpose

This step generates actionable per-dataset acquisition instructions for public dataset replacement candidates.

It consumes the replacement plan, readiness validator output, execution scaffold output, file validation output, and dataset accession registry. It produces a practical acquisition guide that tells the user which public dataset file is needed, where it should be saved locally, and which validation commands should be rerun afterward.

## Inputs

Default request file:

```text
configs/public_data_sources/public_dataset_acquisition_instructions_request.yaml
```

Main input artifacts:

```text
configs/public_data_sources/public_dataset_accession_registry.yaml
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_replacement_workflow/public_dataset_replacement_plan.tsv
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_replacement_readiness/public_dataset_replacement_readiness_table.tsv
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_replacement_execution_scaffold/public_dataset_replacement_execution_jobs.tsv
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_replacement_file_validation/public_dataset_replacement_file_validation_table.tsv
```

## Outputs

Default output directory:

```text
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_acquisition_instructions
```

Generated files:

```text
public_dataset_acquisition_instructions.tsv
public_dataset_acquisition_instructions_source_artifact_index.tsv
public_dataset_acquisition_instructions_summary.yaml
public_dataset_acquisition_instructions_report.html
```

## Expected current result after a25

Because the current a25 state has four replacement candidates and no real local files, the expected initial a26 result is:

```text
instruction_count: 4
acquisition_needed_count: 4
local_file_present_count: 0
```

## Run

From the repository root:

```powershell
python -m core.data.build_public_dataset_acquisition_instructions
```

## Validate

```powershell
python -m py_compile core\datauild_public_dataset_acquisition_instructions.py
python -m py_compile tests	est_build_public_dataset_acquisition_instructions.py
python -m pytest tests	est_build_public_dataset_acquisition_instructions.py -q
python -m pytest -q
```

## Agent role

This stage turns the replacement/readiness/execution/file-validation pipeline into an actionable local acquisition guide for real public data files.

# Public Dataset Replacement File Validator

## Version

`v0.4.0-a25`

## Purpose

This step validates local real public dataset replacement files before downstream replacement execution.

The validator consumes the `v0.4.0-a24` execution scaffold outputs. It does not download public data, modify replacement manifests, or run modality processors. It performs a basic structural validation gate for real files that are attached to ready execution jobs.

## Inputs

Default request file:

```text
configs/public_data_sources/public_dataset_replacement_file_validation_request.yaml
```

The request points to the a24 outputs:

```text
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_replacement_execution_scaffold/public_dataset_replacement_execution_jobs.tsv
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_replacement_execution_scaffold/public_dataset_replacement_execution_summary.yaml
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_replacement_execution_scaffold/public_dataset_replacement_execution_source_artifact_index.tsv
```

## Outputs

Default output directory:

```text
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_replacement_file_validation
```

Generated files:

```text
public_dataset_replacement_file_validation_table.tsv
public_dataset_replacement_file_validation_source_artifact_index.tsv
public_dataset_replacement_file_validation_summary.yaml
public_dataset_replacement_file_validation_report.html
```

## Validation states

The validator can assign these states:

```text
validated_real_file
skipped_not_ready
missing_real_file
failed_disallowed_extension
failed_unreadable_table
failed_too_few_rows
failed_too_few_columns
warning_missing_id_like_first_column
```

## Expected result after a24

Because the current a24 state has four skipped candidates and zero ready execution jobs, the expected initial a25 result is:

```text
replacement_candidate_count: 4
ready_execution_job_count: 0
validated_real_file_count: 0
skipped_not_ready_count: 4
missing_real_file_count: 0
failed_validation_count: 0
```

## Run

From the repository root:

```powershell
python -m core.data.validate_public_dataset_replacement_files
```

## Validate

```powershell
python -m py_compile core\dataalidate_public_dataset_replacement_files.py
python -m py_compile tests	est_validate_public_dataset_replacement_files.py
python -m pytest tests	est_validate_public_dataset_replacement_files.py -q
python -m pytest -q
```

## Agent role

This stage is the first real-file structural validation gate. It prepares the project for future modality-specific replacement execution once real public dataset files are supplied.

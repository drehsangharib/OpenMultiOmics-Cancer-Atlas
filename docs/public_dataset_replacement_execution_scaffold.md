# Public Dataset Replacement Execution Scaffold

## Version

`v0.4.0-a24`

## Purpose

This step builds a controlled, non-destructive execution scaffold from the `v0.4.0-a23` public dataset replacement readiness outputs.

The scaffold does not download public data, overwrite manifests, modify real files, or execute modality processors. Instead, it prepares auditable execution records for candidates that have already reached `ready_for_replacement_validation` and explicit skip records for candidates that are not ready.

## Inputs

Default request file:

```text
configs/public_data_sources/public_dataset_replacement_execution_request.yaml
```

The request points to the a23 outputs:

```text
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_replacement_readiness/public_dataset_replacement_readiness_table.tsv
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_replacement_readiness/public_dataset_replacement_readiness_summary.yaml
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_replacement_readiness/public_dataset_replacement_readiness_source_artifact_index.tsv
```

## Outputs

Default output directory:

```text
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_replacement_execution_scaffold
```

Generated files:

```text
public_dataset_replacement_execution_jobs.tsv
public_dataset_replacement_execution_manifest_inventory.tsv
public_dataset_replacement_execution_source_artifact_index.tsv
public_dataset_replacement_execution_summary.yaml
public_dataset_replacement_execution_report.html
execution_job_manifests/
```

## Expected result after a23

Because the current a23 state has four candidates and zero real replacement files, the expected initial a24 result is:

```text
replacement_candidate_count: 4
ready_execution_job_count: 0
skipped_not_ready_count: 4
execution_job_manifest_count: 0
```

## Run

From the repository root:

```powershell
python -m core.data.build_public_dataset_replacement_execution_scaffold
```

## Validate

```powershell
python -m py_compile core\datauild_public_dataset_replacement_execution_scaffold.py
python -m py_compile tests	est_build_public_dataset_replacement_execution_scaffold.py
python -m pytest tests	est_build_public_dataset_replacement_execution_scaffold.py -q
python -m pytest -q
```

## Agent role

This stage creates the execution planning layer between readiness validation and future real public-data replacement execution. It protects the repository from destructive execution while preserving auditable records of ready and skipped candidates.

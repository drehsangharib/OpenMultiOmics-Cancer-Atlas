# Public Data Execution Smoke Runner

## Purpose

`core/data/run_public_data_execution_smoke.py` verifies that materialized public-data manifest stubs can execute through modality feature-store processors.

## North star

```text
AI-driven raw-data-to-biological-insight platform
```

This step begins validating real/public-data execution readiness after acquisition planning and local file materialization.

## Main command

```powershell
python -m core.data.run_public_data_execution_smoke
```

## Required prior steps

```powershell
python -m core.data.build_public_data_acquisition_plan
python -m core.data.materialize_public_data_files
```

## Outputs

```text
outputs/public_data_acquisition/<atlas>/execution_smoke/execution_smoke_results.tsv
outputs/public_data_acquisition/<atlas>/execution_smoke/execution_smoke_summary.yaml
outputs/public_data_acquisition/<atlas>/execution_smoke/execution_smoke_report.html
```

## Suggested release tag

```text
v0.4.0-a17 = Public-data execution smoke runner
```

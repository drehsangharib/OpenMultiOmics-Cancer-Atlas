# Public Data Local File Materialization

## Purpose

`core/data/materialize_public_data_files.py` turns public-data acquisition manifest templates into local file requirements, placeholder files, and execution-ready manifest stubs.

## North star

```text
AI-driven raw-data-to-biological-insight platform
```

This layer bridges public repository planning to local data execution.

## Main command

```powershell
python -m core.data.materialize_public_data_files
```

## Required prior step

```powershell
python -m core.data.build_public_data_acquisition_plan
```

## Outputs

```text
outputs/public_data_acquisition/<atlas>/local_file_materialization/local_file_requirements.tsv
outputs/public_data_acquisition/<atlas>/local_file_materialization/materialized_manifest_inventory.tsv
outputs/public_data_acquisition/<atlas>/local_file_materialization/local_file_materialization_summary.yaml
outputs/public_data_acquisition/<atlas>/local_file_materialization/local_file_materialization_report.html
outputs/public_data_acquisition/<atlas>/local_file_materialization/materialized_manifest_stubs/*.yaml
```

## Suggested release tag

```text
v0.4.0-a16 = Public-data local file materialization scaffold
```

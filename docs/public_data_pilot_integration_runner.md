# Public Data Pilot Integration Runner

## Purpose

`core/data/run_public_data_pilot_integration.py` runs multi-omics integration and AI interpretation on the public-data pilot feature-store bundle.

## North star

```text
AI-driven raw-data-to-biological-insight platform
```

This step connects the public-data pilot feature-store bundle to the full downstream OpenMultiOmics analysis chain.

## Main command

```powershell
python -m core.data.run_public_data_pilot_integration
```

## Required prior steps

```powershell
python -m core.data.build_public_data_acquisition_plan
python -m core.data.materialize_public_data_files
python -m core.data.run_public_data_execution_smoke
python -m core.data.build_public_data_pilot_bundle
```

## Outputs

```text
outputs/public_data_acquisition/<atlas>/pilot_integration_run/public_data_pilot_integration_summary.yaml
outputs/public_data_acquisition/<atlas>/pilot_integration_run/public_data_pilot_integration_artifact_inventory.tsv
outputs/public_data_acquisition/<atlas>/pilot_integration_run/public_data_pilot_integration_report.html
```

## Suggested release tag

```text
v0.4.0-a19 = Public-data pilot integration runner
```

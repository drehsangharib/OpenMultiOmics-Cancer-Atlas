# Public-Data Pilot Portfolio Dashboard

## Purpose

`core/data/build_public_data_portfolio_dashboard.py` builds a dashboard-style index over the public-data pilot workflow outputs.

## North star

```text
AI-driven raw-data-to-biological-insight platform
```

This step makes the public-data pilot workflow easier to review, share, and plan from one portfolio-level entry point.

## Main command

```powershell
python -m core.data.build_public_data_portfolio_dashboard
```

## Required prior steps

```powershell
python -m core.data.build_public_data_acquisition_plan
python -m core.data.materialize_public_data_files
python -m core.data.run_public_data_execution_smoke
python -m core.data.build_public_data_pilot_bundle
python -m core.data.run_public_data_pilot_integration
python -m core.data.build_public_data_pilot_release_bundle
```

## Outputs

```text
outputs/public_data_acquisition/<atlas>/portfolio_dashboard/public_data_portfolio_dashboard_summary.yaml
outputs/public_data_acquisition/<atlas>/portfolio_dashboard/public_data_workflow_stage_summary.tsv
outputs/public_data_acquisition/<atlas>/portfolio_dashboard/public_data_portfolio_metrics.tsv
outputs/public_data_acquisition/<atlas>/portfolio_dashboard/public_data_source_artifact_index.tsv
outputs/public_data_acquisition/<atlas>/portfolio_dashboard/index.html
outputs/public_data_acquisition/<atlas>/portfolio_dashboard/README.md
```

## Suggested release tag

```text
v0.4.0-a21 = Public-data pilot dashboard index and portfolio report
```

# Public Dataset Replacement Workflow

## Purpose

`core/data/build_public_dataset_replacement_workflow.py` maps placeholder public-data matrices to real public dataset accession candidates and replacement manifest stubs.

## North star

```text
AI-driven raw-data-to-biological-insight platform
```

This step begins formalizing how the scaffolded public-data pilot becomes a real public-data-backed workflow.

## Main command

```powershell
python -m core.data.build_public_dataset_replacement_workflow
```

## Required prior step

```powershell
python -m core.data.build_public_data_portfolio_dashboard
```

## Outputs

```text
outputs/public_data_acquisition/<atlas>/dataset_replacement_workflow/public_dataset_replacement_plan.tsv
outputs/public_data_acquisition/<atlas>/dataset_replacement_workflow/replacement_manifest_inventory.tsv
outputs/public_data_acquisition/<atlas>/dataset_replacement_workflow/replacement_source_artifact_index.tsv
outputs/public_data_acquisition/<atlas>/dataset_replacement_workflow/public_dataset_replacement_summary.yaml
outputs/public_data_acquisition/<atlas>/dataset_replacement_workflow/public_dataset_replacement_report.html
outputs/public_data_acquisition/<atlas>/dataset_replacement_workflow/replacement_manifest_stubs/*.yaml
```

## Suggested release tag

```text
v0.4.0-a22 = Public dataset accession registry and replacement workflow
```

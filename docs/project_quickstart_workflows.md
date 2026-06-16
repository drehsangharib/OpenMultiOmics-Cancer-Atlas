# OpenMultiOmics-Cancer-Atlas Quickstart Workflows

This document summarizes metadata-only workflows in OpenMultiOmics-Cancer-Atlas.

## Xena metadata workflow

```powershell
python -m core.pipelines.run_xena_metadata_pipeline --recommended-only --make-report
```

```powershell
python -m core.pipelines.run_xena_metadata_pipeline --recommended-only --make-report --open-report
```

## Unified GDC + Xena workflow

```powershell
python -m core.pipelines.run_unified_public_omics_pipeline --make-report
```

```powershell
python -m core.pipelines.run_unified_public_omics_pipeline --refresh-xena --xena-recommended-only --make-report
```

```powershell
python -m core.pipelines.run_unified_public_omics_pipeline --refresh-xena --xena-recommended-only --make-report --open-report
```

Expected outputs:

```text
outputs/dataset_inventory/unified_public_cancer_omics_inventory.tsv
outputs/reports/unified_public_omics_pipeline_summary.tsv
outputs/reports/unified_public_cancer_omics_inventory_report.html
```

## Metadata-only policy

These workflows are metadata-only by default and do not download large molecular matrices.

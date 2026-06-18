# Multi-Omics Feature Table Builder

## Purpose

`core/integration/build_multiomics_feature_table.py` converts a multi-omics integration manifest into an integration-ready feature table.

## North star

```text
AI-driven raw-data-to-biological-insight platform
```

This step moves the system from aligned modality feature stores to a single matrix that downstream AI analysis modules can consume.

## Main command

```powershell
python -m core.integration.build_multiomics_feature_table --integration-manifest outputseatures\integrated\multi_cancer_demo\multiomics_integration_manifest.yaml
```

## Outputs

```text
outputs/features/integrated/<atlas>/integrated_feature_matrix.tsv
outputs/features/integrated/<atlas>/feature_block_inventory.tsv
outputs/features/integrated/<atlas>/integrated_feature_qc_summary.tsv
```

## Behavior

```text
reads multi-omics integration manifest
loads normalized modality matrices
prefixes feature names by modality
selects complete-case samples by default
writes integrated matrix and QC summary
```

## Suggested release tag

```text
v0.4.0-a7 = Integrated multi-omics feature table and AI analysis context
```

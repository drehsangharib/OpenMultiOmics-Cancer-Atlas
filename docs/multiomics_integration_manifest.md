# Multi-Omics Integration Manifest

## Purpose

`core/integration/build_multiomics_integration_manifest.py` builds a YAML manifest describing aligned modality feature stores for downstream AI multi-omics integration.

## Main command

```powershell
python -m core.integration.build_multiomics_integration_manifest --atlas brca --modalities transcriptomics proteomics epigenome metabolomics
```

## Outputs

```text
outputs/features/integrated/<atlas>/sample_alignment.tsv
outputs/features/integrated/<atlas>/modality_inventory.tsv
outputs/features/integrated/<atlas>/alignment_qc_summary.tsv
outputs/features/integrated/<atlas>/multiomics_integration_manifest.yaml
```

## Role in the AI multi-omics analysis agent/system

This manifest becomes the handoff from modality preprocessing into multi-omics integration.

```text
feature stores -> sample alignment -> integration manifest -> AI multi-omics reasoning -> biological insight
```

## Suggested release tag

```text
v0.4.0-a6 = Multi-omics sample alignment and integration manifest
```

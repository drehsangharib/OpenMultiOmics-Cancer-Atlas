# Multi-Omics Sample Alignment

## Purpose

`core/integration/build_multiomics_sample_alignment.py` aligns sample identifiers across modality feature stores.

## North star

```text
AI-driven raw-data-to-biological-insight platform
```

This layer starts connecting independent modality feature stores into a multi-omics integration-ready dataset.

## Main command

```powershell
python -m core.integration.build_multiomics_sample_alignment --atlas brca --modalities transcriptomics proteomics epigenome metabolomics
```

## Outputs

```text
outputs/features/integrated/<atlas>/sample_alignment.tsv
outputs/features/integrated/<atlas>/modality_inventory.tsv
outputs/features/integrated/<atlas>/alignment_qc_summary.tsv
```

## Meaning

The sample alignment table records which samples are present in each modality and identifies complete-case samples for downstream multi-omics integration.

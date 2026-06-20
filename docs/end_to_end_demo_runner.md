# End-to-End Demo Runner

## Purpose

`core/pipelines/run_end_to_end_demo.py` orchestrates the OpenMultiOmics demo path from modality feature stores to external annotation evidence.

## North star

```text
AI-driven raw-data-to-biological-insight platform
```

This step demonstrates the integrated platform behavior:

```text
feature stores
-> multi-omics integration manifest
-> integrated feature table
-> AI analysis context
-> baseline AI analysis
-> biological insight seed report
-> program annotation scaffold
-> pathway-ready evidence layer
-> external annotation connector scaffold
```

## Main command

```powershell
python -m core.pipelines.run_end_to_end_demo
```

## Optional explicit command

```powershell
python -m core.pipelines.run_end_to_end_demo `
  --atlas multi_cancer_demo `
  --manifest-paths `
  outputseatures	ranscriptomicsrcaeature_store_manifest.yaml `
  outputseatures\proteomics\luadeature_store_manifest.yaml `
  outputseatures\epigenome\gbmeature_store_manifest.yaml `
  outputseatures\metabolomics\multi_cancereature_store_manifest.yaml
```

## Outputs

```text
outputs/reports/end_to_end_demo/end_to_end_demo_summary.yaml
outputs/reports/end_to_end_demo/end_to_end_demo_report.html
outputs/reports/end_to_end_demo/end_to_end_artifact_inventory.tsv
outputs/reports/end_to_end_demo/platform_capability_map.tsv
```

## Suggested release tag

```text
v0.4.0-a13 = End-to-end demo runner and release report
```

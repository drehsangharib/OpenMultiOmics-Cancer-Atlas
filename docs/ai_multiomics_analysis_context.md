# AI Multi-Omics Analysis Context

## Purpose

`core/agent/build_ai_multiomics_analysis_context.py` creates a structured YAML context for downstream AI multi-omics analysis.

## Role

This file is the handoff from data engineering into the future AI analysis agent/system.

```text
feature stores -> sample alignment -> integrated feature table -> AI analysis context -> biological insight generation
```

## Main command

```powershell
python -m core.agent.build_ai_multiomics_analysis_context `
  --integration-manifest outputseatures\integrated\multi_cancer_demo\multiomics_integration_manifest.yaml `
  --integrated-feature-matrix outputseatures\integrated\multi_cancer_demo\integrated_feature_matrix.tsv `
  --feature-block-inventory outputseatures\integrated\multi_cancer_demoeature_block_inventory.tsv `
  --integrated-feature-qc-summary outputseatures\integrated\multi_cancer_demo\integrated_feature_qc_summary.tsv
```

## Output

```text
outputs/features/integrated/<atlas>/ai_multiomics_analysis_context.yaml
```

## Next layer

The next major layer should implement analysis modules that consume this context, such as clustering, feature ranking, pathway scoring, and biological interpretation reports.

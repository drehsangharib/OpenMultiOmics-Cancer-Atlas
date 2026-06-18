# Baseline AI Multi-Omics Analysis

## Purpose

`core/agent/run_baseline_multiomics_analysis.py` runs the first baseline AI-oriented analysis over an integrated multi-omics feature table.

## North star

```text
AI-driven raw-data-to-biological-insight platform
```

This step begins the transition from data engineering to biological insight generation.

## Main command

```powershell
python -m core.agent.run_baseline_multiomics_analysis --analysis-context outputseatures\integrated\multi_cancer_demoi_multiomics_analysis_context.yaml
```

## Outputs

```text
outputs/features/integrated/<atlas>/baseline_ai_analysis/sample_embedding.tsv
outputs/features/integrated/<atlas>/baseline_ai_analysis/sample_clusters.tsv
outputs/features/integrated/<atlas>/baseline_ai_analysis/cluster_summary.tsv
outputs/features/integrated/<atlas>/baseline_ai_analysis/feature_rankings.tsv
outputs/features/integrated/<atlas>/baseline_ai_analysis/modality_block_summary.tsv
outputs/features/integrated/<atlas>/baseline_ai_analysis/baseline_analysis_summary.yaml
outputs/features/integrated/<atlas>/baseline_ai_analysis/baseline_multiomics_insight_report.html
```

## Current analysis behavior

```text
median imputation for any remaining missing values
feature scaling
PCA-style embedding using singular value decomposition
PC1-based baseline sample grouping
feature ranking by absolute PC1 loading
modality-block summary
HTML insight seed report
```

## Suggested release tag

```text
v0.4.0-a8 = Baseline AI multi-omics analysis module
```

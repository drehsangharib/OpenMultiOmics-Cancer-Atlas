# Biological Insight Seed Report

## Purpose

`core/agent/build_biological_insight_seed.py` converts baseline AI multi-omics analysis outputs into scaffolded biological interpretation candidates.

## North star

```text
AI-driven raw-data-to-biological-insight platform
```

This is the first biological interpretation scaffold in the AI multi-omics analysis agent/system.

## Main command

```powershell
python -m core.agent.build_biological_insight_seed `
  --analysis-context outputseatures\integrated\multi_cancer_demoi_multiomics_analysis_context.yaml `
  --baseline-analysis-dir outputseatures\integrated\multi_cancer_demoaseline_ai_analysis
```

## Inputs

```text
baseline_ai_analysis/feature_rankings.tsv
baseline_ai_analysis/modality_block_summary.tsv
baseline_ai_analysis/cluster_summary.tsv
ai_multiomics_analysis_context.yaml
```

## Outputs

```text
outputs/features/integrated/<atlas>/biological_insight_seed/ranked_feature_annotations.tsv
outputs/features/integrated/<atlas>/biological_insight_seed/modality_program_summary.tsv
outputs/features/integrated/<atlas>/biological_insight_seed/candidate_biological_themes.tsv
outputs/features/integrated/<atlas>/biological_insight_seed/biological_insight_seed_summary.yaml
outputs/features/integrated/<atlas>/biological_insight_seed/biological_insight_seed_report.html
```

## Current interpretation scaffold

```text
transcriptomics -> expression_state_signal
proteomics -> protein_abundance_signal
epigenome -> epigenetic_state_signal
metabolomics -> metabolic_state_signal
multiomics -> cross_modality_state_signal
```

## Important note

The generated themes are seed hypotheses and require downstream biological validation against curated pathway, ontology, and annotation resources.

## Suggested release tag

```text
v0.4.0-a9 = Biological insight seed report and pathway/program annotation scaffold
```

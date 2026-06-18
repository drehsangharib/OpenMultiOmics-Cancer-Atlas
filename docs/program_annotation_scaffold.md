# Program Annotation Scaffold

## Purpose

`core/agent/build_program_annotation_report.py` maps biological insight seed outputs to a curated biological program scaffold.

## North star

```text
AI-driven raw-data-to-biological-insight platform
```

This step expands the interpretation layer from seed themes to a reusable program annotation scaffold.

## Main command

```powershell
python -m core.agent.build_program_annotation_report `
  --biological-insight-seed-dir outputseatures\integrated\multi_cancer_demoiological_insight_seed
```

## Outputs

```text
program_annotated_features.tsv
program_level_summary.tsv
interpretation_priority_table.tsv
program_annotation_summary.yaml
program_annotation_report.html
```

## Current scaffold

```text
expression_state_signal
protein_abundance_signal
epigenetic_state_signal
metabolic_state_signal
cross_modality_state_signal
```

## Suggested release tag

```text
v0.4.0-a10 = Curated biological program annotation scaffold
```

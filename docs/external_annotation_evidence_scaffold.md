# External Annotation Evidence Scaffold

## Purpose

`core/agent/build_external_annotation_evidence.py` prepares pathway-ready evidence for future connection to curated external annotation resources.

## North star

```text
AI-driven raw-data-to-biological-insight platform
```

This layer defines the connector-ready interface between internal multi-omics analysis outputs and future external pathway, ontology, gene-set, protein, methylation, and metabolite resources.

## Main command

```powershell
python -m core.agent.build_external_annotation_evidence `
  --pathway-ready-evidence-dir outputseatures\integrated\multi_cancer_demoiological_insight_seed\program_annotation\pathway_ready_evidence
```

## Outputs

```text
external_annotation_evidence.tsv
external_term_summary.tsv
connector_inventory.tsv
connector_readiness_summary.tsv
external_annotation_summary.yaml
external_annotation_report.html
```

## Interpretation status

This is still a scaffold. It uses a local external annotation seed table and prepares the interface for future real external resource binding.

## Suggested release tag

```text
v0.4.0-a12 = External annotation connector scaffold
```

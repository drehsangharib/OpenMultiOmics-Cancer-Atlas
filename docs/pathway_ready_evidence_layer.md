# Pathway-Ready Evidence Layer

## Purpose

`core/agent/build_pathway_ready_evidence_layer.py` turns program-annotated feature outputs into a pathway-ready evidence scaffold.

## North star

```text
AI-driven raw-data-to-biological-insight platform
```

This step prepares the project for future connections to curated pathway, ontology, gene-set, protein, methylation, and metabolite annotation systems.

## Main command

```powershell
python -m core.agent.build_pathway_ready_evidence_layer `
  --program-annotation-dir outputs\features\integrated\multi_cancer_demo\biological_insight_seed\program_annotation
```

## Outputs

```text
feature_evidence_table.tsv
program_evidence_summary.tsv
pathway_prioritization_table.tsv
annotation_resource_inventory.tsv
pathway_ready_evidence_summary.yaml
pathway_ready_evidence_report.html
```

## Interpretation status

This is a local seed scaffold. It is not yet a full curated biological database integration layer. The next stage should connect the scaffold to external annotation resources and pathway databases.

## Suggested release tag

```text
v0.4.0-a11 = Pathway-ready evidence layer
```

# UCSC Xena Metadata Pipeline

## Purpose

`core/pipelines/run_xena_metadata_pipeline.py` runs the UCSC Xena metadata-only dataset inventory workflow with one command.

This module is part of Milestone 1E.8: integrating Xena dataset inventory report generation into the Xena metadata pipeline.

## Scope

The pipeline queries selected UCSC Xena hubs and writes dataset-level metadata.

The pipeline does **not** download:

```text
expression matrices
copy-number matrices
methylation matrices
mutation matrices
clinical matrices
large molecular files
```

It only writes metadata inventory, summary TSV outputs, and optionally an HTML report.

---

## Main command

Run the recommended first-wave Xena hubs:

```powershell
python -m core.pipelines.run_xena_metadata_pipeline --recommended-only
```

Expected outputs:

```text
outputs/dataset_inventory/xena_dataset_inventory.tsv
outputs/reports/xena_metadata_pipeline_summary.tsv
```

---

## Generate HTML report

To generate the Xena dataset inventory, summary TSV, and HTML report in one command:

```powershell
python -m core.pipelines.run_xena_metadata_pipeline --recommended-only --make-report
```

Expected outputs:

```text
outputs/dataset_inventory/xena_dataset_inventory.tsv
outputs/reports/xena_metadata_pipeline_summary.tsv
outputs/reports/xena_dataset_inventory_report.html
```

---

## Generate and open HTML report

To open the generated report automatically:

```powershell
python -m core.pipelines.run_xena_metadata_pipeline --recommended-only --make-report --open-report
```

The `--open-report` option requires `--make-report`.

---

## Query one hub

```powershell
python -m core.pipelines.run_xena_metadata_pipeline --hub-id gdc_xena
```

---

## Query multiple hubs

```powershell
python -m core.pipelines.run_xena_metadata_pipeline `
  --hub-id gdc_xena `
  --hub-id tcga_xena `
  --hub-id pancanatlas
```

---

## Query recommended first-wave hubs

```powershell
python -m core.pipelines.run_xena_metadata_pipeline --recommended-only
```

Expected first-wave hubs include:

```text
gdc_xena
tcga_xena
pancanatlas
toil_xena
ucsc_public
```

---

## Query high-priority hubs

```powershell
python -m core.pipelines.run_xena_metadata_pipeline --min-priority 5
```

---

## Custom output paths

### Custom dataset inventory path

```powershell
python -m core.pipelines.run_xena_metadata_pipeline `
  --recommended-only `
  --output outputs/dataset_inventory/xena_dataset_inventory.tsv
```

### Custom summary path

```powershell
python -m core.pipelines.run_xena_metadata_pipeline `
  --recommended-only `
  --summary outputs/reports/xena_metadata_pipeline_summary.tsv
```

### Custom report path

```powershell
python -m core.pipelines.run_xena_metadata_pipeline `
  --recommended-only `
  --make-report `
  --report outputs/reports/xena_dataset_inventory_report.html
```

### Custom report title

```powershell
python -m core.pipelines.run_xena_metadata_pipeline `
  --recommended-only `
  --make-report `
  --report-title "OpenMultiOmics Cancer Atlas - UCSC Xena Dataset Inventory"
```

---

## Strict mode

By default, individual hub query failures are recorded in the inventory and the pipeline continues.

To fail immediately on any hub query error:

```powershell
python -m core.pipelines.run_xena_metadata_pipeline --recommended-only --strict
```

---

## Optional delay between hub queries

Use `--sleep-seconds` to pause between hub queries:

```powershell
python -m core.pipelines.run_xena_metadata_pipeline `
  --recommended-only `
  --sleep-seconds 1
```

---

## Timeout

Use `--timeout` to control HTTP timeout in seconds:

```powershell
python -m core.pipelines.run_xena_metadata_pipeline `
  --recommended-only `
  --timeout 90
```

---

## Outputs

### Dataset inventory

```text
outputs/dataset_inventory/xena_dataset_inventory.tsv
```

This file contains metadata-only dataset records with fields such as:

```text
hub_id
hub_name
hub_url
dataset_id
dataset_name
dataset_label
data_category
omics_modality
matrix_type
resource_family
cancer_scope
sample_scope
priority_for_atlas
integration_stage
source_database
notes
```

### Pipeline summary

```text
outputs/reports/xena_metadata_pipeline_summary.tsv
```

The summary TSV includes counts by:

```text
hub_id
omics_modality
data_category
integration_stage
```

It also records:

```text
total_dataset_rows
query_error_rows
elapsed_seconds_rounded
report_generated
report_path
```

### HTML report

```text
outputs/reports/xena_dataset_inventory_report.html
```

The HTML report includes:

```text
overview metrics
dataset counts by hub
dataset counts by omics modality
dataset counts by data category
integration-stage counts
top high-priority datasets
example datasets by hub and modality
unknown-classification review list
```

---

## Recommended workflow

For a full recommended Xena metadata/reporting run:

```powershell
python -m core.pipelines.run_xena_metadata_pipeline --recommended-only --make-report --open-report
```

This command writes:

```text
outputs/dataset_inventory/xena_dataset_inventory.tsv
outputs/reports/xena_metadata_pipeline_summary.tsv
outputs/reports/xena_dataset_inventory_report.html
```

---

## Public-data-only policy

This pipeline performs metadata-only discovery.

It does not download controlled-access data, private datasets, or large molecular matrices.

All generated outputs are derived from public UCSC Xena hub metadata and should remain local unless intentionally curated for release.

---

## Generated outputs and Git

Generated outputs should generally not be committed:

```text
outputs/dataset_inventory/xena_dataset_inventory.tsv
outputs/reports/xena_metadata_pipeline_summary.tsv
outputs/reports/xena_dataset_inventory_report.html
```

Only source code, tests, and documentation should be committed unless generated outputs are intentionally curated.

---

## Tests

Run the pipeline-wrapper tests:

```powershell
python -m pytest tests/test_run_xena_metadata_pipeline.py -q
```

Run the report tests:

```powershell
python -m pytest tests/test_xena_dataset_inventory_report.py -q
```

Run the full suite:

```powershell
python -m pytest -q
```

---

## Milestone meaning

```text
1E.8 = Integrate Xena report generation into Xena metadata pipeline
```

Suggested release tag:

```text
v0.1.19 = Xena metadata pipeline report integration
```

---

## Example successful run

A successful recommended multi-hub run should print a summary similar to:

```text
Xena metadata pipeline summary:
  dataset_inventory_rows: 1892
  elapsed_time: ...
  dataset_inventory_output: outputs\dataset_inventory\xena_dataset_inventory.tsv
  summary_output: outputs\reports\xena_metadata_pipeline_summary.tsv
  report_output: outputs\reports\xena_dataset_inventory_report.html

Rows by hub:
  gdc_xena: 889
  tcga_xena: 760
  ucsc_public: 165
  toil_xena: 54
  pancanatlas: 24

Rows by modality:
  transcriptomics: 513
  unknown: 348
  cnv: 311
  clinical_annotation: 245
  snv: 143
  methylation: 116
  annotation_map: 98
  proteomics: 79
  functional_signature: 38
  genomic_signature: 1

Query-error rows: 0

Xena metadata pipeline complete.
```

Exact row counts may change as UCSC Xena hubs are updated.
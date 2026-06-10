# GDC Metadata Pipeline Runner

## Purpose

`core/pipelines/run_gdc_metadata_pipeline.py` runs the GDC metadata workflow end-to-end with one command.

This module is part of Milestone 1D.3 and 1D.4:

```text
1D.3 = reproducible one-command GDC pipeline execution
1D.4 = safe development-output mode for project-limited test runs
```

The pipeline uses public GDC metadata and locally generated summary outputs. It does not download raw controlled-access files or process private datasets.

---

## Full official command

Run the full official GDC metadata pipeline:

```powershell
python -m core.pipelines.run_gdc_metadata_pipeline
```

This performs:

```text
1. GDC project inventory
2. GDC file counts by project
3. GDC project modality matrix
4. GDC project priority ranking
5. GDC priority visual outputs
6. GDC priority HTML report
```

---

## Main official outputs

Official full-run outputs are written to:

```text
outputs/dataset_inventory/gdc_project_inventory.tsv
outputs/dataset_inventory/gdc_file_counts_by_project.tsv
outputs/dataset_inventory/gdc_project_modality_matrix.tsv
outputs/ranked_datasets/gdc_project_priority_ranking.tsv
outputs/figures/
outputs/reports/gdc_project_priority_report.html
outputs/reports/gdc_metadata_pipeline_summary.tsv
```

Generated outputs should remain local and should not be committed unless intentionally curated.

---

## Open the report after generation

Use:

```powershell
python -m core.pipelines.run_gdc_metadata_pipeline --open-report
```

This runs the pipeline and opens:

```text
outputs/reports/gdc_project_priority_report.html
```

---

## Regenerate visuals and report only

Use this when the main TSV outputs already exist and you only want to refresh downstream products:

```powershell
python -m core.pipelines.run_gdc_metadata_pipeline --report-only
```

To also open the report:

```powershell
python -m core.pipelines.run_gdc_metadata_pipeline --report-only --open-report
```

In `--report-only` mode, the pipeline reuses:

```text
outputs/dataset_inventory/gdc_project_inventory.tsv
outputs/dataset_inventory/gdc_file_counts_by_project.tsv
```

and regenerates:

```text
outputs/dataset_inventory/gdc_project_modality_matrix.tsv
outputs/ranked_datasets/gdc_project_priority_ranking.tsv
outputs/figures/
outputs/reports/gdc_project_priority_report.html
outputs/reports/gdc_metadata_pipeline_summary.tsv
```

---

## Reuse existing file counts

The file-count step can be slow because it queries file metadata for all GDC projects.

To reuse an existing file-count table:

```powershell
python -m core.pipelines.run_gdc_metadata_pipeline --skip-file-counts
```

This reuses:

```text
outputs/dataset_inventory/gdc_file_counts_by_project.tsv
```

and regenerates downstream outputs.

---

## Reuse existing project inventory

To reuse an existing project inventory but refresh file counts and downstream outputs:

```powershell
python -m core.pipelines.run_gdc_metadata_pipeline --skip-project-inventory
```

This reuses:

```text
outputs/dataset_inventory/gdc_project_inventory.tsv
```

and regenerates:

```text
outputs/dataset_inventory/gdc_file_counts_by_project.tsv
outputs/dataset_inventory/gdc_project_modality_matrix.tsv
outputs/ranked_datasets/gdc_project_priority_ranking.tsv
outputs/figures/
outputs/reports/gdc_project_priority_report.html
```

---

## Safe development output mode

Use `--dev-output` for test runs so official full-output files are not overwritten.

This is especially important when using:

```text
--project-limit
```

because project-limited runs intentionally produce small test outputs.

Recommended safe development command:

```powershell
python -m core.pipelines.run_gdc_metadata_pipeline --project-limit 5 --dev-output --open-report
```

This writes all generated files to:

```text
outputs/dev/gdc_project_inventory.tsv
outputs/dev/gdc_file_counts_by_project.tsv
outputs/dev/gdc_project_modality_matrix.tsv
outputs/dev/gdc_project_priority_ranking.tsv
outputs/dev/figures/
outputs/dev/gdc_project_priority_report.html
outputs/dev/gdc_metadata_pipeline_summary.tsv
```

This protects the official full-run files:

```text
outputs/dataset_inventory/gdc_project_inventory.tsv
outputs/dataset_inventory/gdc_file_counts_by_project.tsv
outputs/dataset_inventory/gdc_project_modality_matrix.tsv
outputs/ranked_datasets/gdc_project_priority_ranking.tsv
outputs/figures/
outputs/reports/gdc_project_priority_report.html
outputs/reports/gdc_metadata_pipeline_summary.tsv
```

---

## Fast test run

For a small test run, use:

```powershell
python -m core.pipelines.run_gdc_metadata_pipeline --project-limit 5 --dev-output
```

To open the generated development report:

```powershell
python -m core.pipelines.run_gdc_metadata_pipeline --project-limit 5 --dev-output --open-report
```

Expected development report:

```text
outputs/dev/gdc_project_priority_report.html
```

Expected development summary:

```text
outputs/dev/gdc_metadata_pipeline_summary.tsv
```

---

## Official output safety check

After running a development pipeline, confirm official full outputs were not overwritten:

```powershell
(Get-Content outputs\dataset_inventory\gdc_file_counts_by_project.tsv).Count
(Get-Content outputs\dataset_inventory\gdc_project_modality_matrix.tsv).Count
(Get-Content outputs\ranked_datasets\gdc_project_priority_ranking.tsv).Count
```

For the full 91-project GDC run, expected approximate line counts are:

```text
3981
92
92
```

These correspond to:

```text
3980 file-count rows + header
91 modality-matrix project rows + header
91 ranking rows + header
```

For a 5-project development run, check:

```powershell
(Get-Content outputs\dev\gdc_file_counts_by_project.tsv).Count
(Get-Content outputs\dev\gdc_project_modality_matrix.tsv).Count
(Get-Content outputs\dev\gdc_project_priority_ranking.tsv).Count
```

Expected development counts should be much smaller, commonly around:

```text
~138
6
6
```

The exact file-count row number may vary with GDC metadata, but the modality and ranking tables should have one header row plus the limited project count.

---

## Link images instead of embedding base64

By default, the HTML report embeds images as base64 data URIs. This makes the report portable as one HTML file.

To link local image files instead:

```powershell
python -m core.pipelines.run_gdc_metadata_pipeline --report-only --link-images
```

For development outputs:

```powershell
python -m core.pipelines.run_gdc_metadata_pipeline --project-limit 5 --dev-output --link-images --open-report
```

---

## Common command recipes

### Full official rebuild

```powershell
python -m core.pipelines.run_gdc_metadata_pipeline --open-report
```

### Full rebuild but reuse project inventory

```powershell
python -m core.pipelines.run_gdc_metadata_pipeline --skip-project-inventory --open-report
```

### Rebuild report from existing full outputs

```powershell
python -m core.pipelines.run_gdc_metadata_pipeline --report-only --open-report
```

### Safe 5-project test run

```powershell
python -m core.pipelines.run_gdc_metadata_pipeline --project-limit 5 --dev-output --open-report
```

### Safe 10-project test run

```powershell
python -m core.pipelines.run_gdc_metadata_pipeline --project-limit 10 --dev-output --open-report
```

### Skip report generation

```powershell
python -m core.pipelines.run_gdc_metadata_pipeline --skip-report
```

### Skip visual generation

```powershell
python -m core.pipelines.run_gdc_metadata_pipeline --skip-visuals
```

---

## Pipeline summary output

Each pipeline run writes a summary table.

Official summary:

```text
outputs/reports/gdc_metadata_pipeline_summary.tsv
```

Development summary:

```text
outputs/dev/gdc_metadata_pipeline_summary.tsv
```

The summary table includes:

```text
step_name
status
output_path
row_count
elapsed_seconds
```

Example statuses:

```text
completed
skipped_existing
skipped
```

---

## Public-data-only policy

This pipeline uses public GDC metadata and locally generated summary tables.

The pipeline does not:

```text
download controlled-access raw files
process private datasets
store user credentials
require GDC authentication tokens
```

Controlled-access file availability may be counted in public metadata summaries, but controlled-access files are not downloaded.

---

## Tests

Run all tests:

```powershell
python -m pytest -q
```

Run only pipeline-runner tests:

```powershell
python -m pytest tests/test_run_gdc_metadata_pipeline.py -q
```

Syntax-check the runner:

```powershell
python -m py_compile core\pipelines\run_gdc_metadata_pipeline.py
```

Syntax-check the test file:

```powershell
python -m py_compile tests\test_run_gdc_metadata_pipeline.py
```

The pipeline-runner tests use monkeypatching and temporary files to avoid live GDC network calls.

---

## Notes for future development

Future pipeline improvements may include:

```text
automatic dev-output mode whenever --project-limit is used
pipeline configuration files
JSON pipeline manifests
subset-specific report generation
cancer-specific atlas module export
UCSC Xena integration
cross-database multi-omics coverage reports
```
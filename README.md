# OpenMultiOmics-Cancer-Atlas

OpenMultiOmics-Cancer-Atlas is an open-database-first, AI-assisted public cancer multi-omics atlas project.

The project is designed to search, rank, harmonize, and integrate public cancer datasets across transcriptomics, proteomics, epigenomics, metabolomics, genomics, and clinical metadata.

## Scope

This repository is intentionally **public-data-only**. It should not contain unpublished/private experimental data.

The first flagship atlas module is:

```text
atlases/gbm/
```

GBM is developed first because it provides a biologically rich test case involving tumor-intrinsic signaling, brain microenvironment, neuronal/glial signatures, epigenomic regulation, and multi-omics validation.

## Core goals

1. Build a public cancer dataset inventory.
2. Rank public datasets by biological and technical relevance.
3. Harmonize metadata across public repositories.
4. Support cancer-type-specific atlas modules.
5. Build reusable public signatures and reference matrices.
6. Enable private/local comparison to unpublished datasets without committing private data.

## Data governance

Do **not** commit:

- unpublished raw data
- private sample metadata
- internal differential expression/proteomics/metabolomics tables
- manuscript figures/results before publication
- private FASTQ/BAM/H5AD/RDS/mzML/raw MS files

Use `examples/` only for toy or synthetic/demo data.

## Quick start

### Windows PowerShell

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m core.scoring.public_dataset_ranker --atlas gbm
```

Expected outputs:

```text
outputs/dataset_inventory/public_dataset_inventory.tsv
outputs/ranked_datasets/ranked_gbm_public_datasets.tsv
outputs/reports/OpenMultiOmics_Cancer_Atlas_GBM_v0.1_report.html
```

### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m core.scoring.public_dataset_ranker --atlas gbm
```

## Repository layout

```text
core/       Reusable platform modules
configs/    Global database/scoring/species configuration
atlases/    Cancer-type-specific atlas modules
examples/   Demo/synthetic data only
notebooks/  Analysis notebooks
docs/       Documentation
tests/      Unit tests
outputs/    Generated outputs, mostly ignored by Git
```

<!-- OPENMULTIOMICS_WORKFLOWS_START -->

## Quickstart Workflows

OpenMultiOmics-Cancer-Atlas currently supports metadata-only workflows for GDC, UCSC Xena, and unified public cancer omics inventory generation.

These workflows do not download large molecular matrices by default.

### Xena metadata workflow

Generate the recommended UCSC Xena metadata inventory and report:

```powershell
python -m core.pipelines.run_xena_metadata_pipeline --recommended-only --make-report
```

Generate and open the Xena report:

```powershell
python -m core.pipelines.run_xena_metadata_pipeline --recommended-only --make-report --open-report
```

Expected outputs:

```text
outputs/dataset_inventory/xena_dataset_inventory.tsv
outputs/reports/xena_metadata_pipeline_summary.tsv
outputs/reports/xena_dataset_inventory_report.html
```

### Unified GDC + Xena workflow

Build the unified public cancer omics inventory and report:

```powershell
python -m core.pipelines.run_unified_public_omics_pipeline --make-report
```

Refresh Xena first, then build the unified inventory and report:

```powershell
python -m core.pipelines.run_unified_public_omics_pipeline --refresh-xena --xena-recommended-only --make-report
```

Generate and open the unified report:

```powershell
python -m core.pipelines.run_unified_public_omics_pipeline --refresh-xena --xena-recommended-only --make-report --open-report
```

Expected outputs:

```text
outputs/dataset_inventory/unified_public_cancer_omics_inventory.tsv
outputs/reports/unified_public_omics_pipeline_summary.tsv
outputs/reports/unified_public_cancer_omics_inventory_report.html
```

### Unified inventory QC report

Generate the unified inventory quality-control report:

```powershell
python -m core.reporting.unified_public_cancer_omics_qc_report
```

Expected output:

```text
outputs/reports/unified_public_cancer_omics_qc_report.html
```

### Full workflow guide

See:

```text
docs/project_quickstart_workflows.md
```

<!-- OPENMULTIOMICS_WORKFLOWS_END -->

## License

MIT License for code. Documentation and generated public-data summaries can be adapted under CC-BY-4.0 if desired.

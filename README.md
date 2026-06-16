# OpenMultiOmics-Cancer-Atlas

OpenMultiOmics-Cancer-Atlas is an open-database-first, AI-assisted public cancer multi-omics atlas project.

The project is designed to search, rank, harmonize, and integrate public cancer datasets across transcriptomics, proteomics, epigenomics, metabolomics, genomics, and clinical metadata.

## Scope

This repository is intentionally **public-data-only**. It should not contain unpublished/private experimental data.

## Quick start

### Windows PowerShell

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m core.scoring.public_dataset_ranker --atlas gbm
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

```powershell
python -m core.pipelines.run_xena_metadata_pipeline --recommended-only --make-report
```

```powershell
python -m core.pipelines.run_xena_metadata_pipeline --recommended-only --make-report --open-report
```

### Unified GDC + Xena workflow

```powershell
python -m core.pipelines.run_unified_public_omics_pipeline --make-report
```

```powershell
python -m core.pipelines.run_unified_public_omics_pipeline --refresh-xena --xena-recommended-only --make-report
```

```powershell
python -m core.pipelines.run_unified_public_omics_pipeline --refresh-xena --xena-recommended-only --make-report --open-report
```

Expected outputs:

```text
outputs/dataset_inventory/unified_public_cancer_omics_inventory.tsv
outputs/reports/unified_public_omics_pipeline_summary.tsv
outputs/reports/unified_public_cancer_omics_inventory_report.html
```

Full workflow guide:

```text
docs/project_quickstart_workflows.md
```

<!-- OPENMULTIOMICS_WORKFLOWS_END -->

## License

MIT License for code. Documentation and generated public-data summaries can be adapted under CC-BY-4.0 if desired.


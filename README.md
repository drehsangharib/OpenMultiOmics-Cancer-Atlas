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

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m core.scoring.public_dataset_ranker --atlas gbm
```

Expected outputs:

```text
outputs/dataset_inventory/public_dataset_inventory.tsv
outputs/ranked_datasets/ranked_gbm_public_datasets.tsv
outputs/reports/OpenMultiOmics_Cancer_Atlas_GBM_v0.1_report.html
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

## First milestone

Version `0.1` implements a dataset inventory and ranking engine for the GBM atlas module.

## License

MIT License for code. Documentation and generated public-data summaries can be adapted under CC-BY-4.0 if desired.

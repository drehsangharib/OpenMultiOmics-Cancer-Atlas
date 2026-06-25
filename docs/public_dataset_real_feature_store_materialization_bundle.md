# Real Data Feature-Store Materialization Bundle

## Version

`v0.4.0-a38`

## Purpose

This milestone materializes the validated and locked TCGA-BRCA real transcriptomics pilot into an AI-ready feature-store bundle.

This final corrected export fixes issues detected before commit:

1. Replaces `DataFrame.applymap` with a pandas-version-compatible column-wise transform.
2. Adds safe optional YAML loading so empty optional paths do not resolve to `Path('.')`.
3. Adds BRCA fallback metadata resolution when a37 runtime outputs have blank `target_local_path` or `modality` despite activation readiness.

## Outputs

```text
tcga_brca_transcriptomics_ai_ready_feature_matrix.tsv
tcga_brca_transcriptomics_gene_summary.tsv
tcga_brca_transcriptomics_sample_summary.tsv
tcga_brca_transcriptomics_feature_store_manifest.yaml
tcga_brca_transcriptomics_feature_store_summary.yaml
tcga_brca_transcriptomics_feature_store_report.html
```

## Expected with current BRCA real-data pilot

```text
dataset_id: tcga_brca_transcriptomics
modality: transcriptomics
feature_count: 60660
sample_count: 20
ready_for_ai_model_input: true
```

## Run

```powershell
python -m core.data.build_public_dataset_real_feature_store
```

## Validate

```powershell
python -m py_compile core\datauild_public_dataset_real_feature_store.py
python -m py_compile tests	est_build_public_dataset_real_feature_store.py
python -m pytest tests	est_build_public_dataset_real_feature_store.py -q
python -m pytest -q
```

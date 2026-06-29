# Real Data AI-Ready Benchmark Handoff Bundle

## Version

`v0.4.0-a39`

## Purpose

This milestone converts the real TCGA-BRCA feature store from v0.4.0-a38 into deterministic AI/modeling handoff artifacts.

It performs variance-based feature selection, transposes the feature matrix into sample-by-feature model input format, creates deterministic train/validation/test split manifests, and writes a model handoff manifest and HTML report.

## Outputs

```text
tcga_brca_transcriptomics_model_input_matrix.tsv
tcga_brca_transcriptomics_feature_selection_table.tsv
tcga_brca_transcriptomics_sample_split_manifest.tsv
tcga_brca_transcriptomics_split_summary.tsv
tcga_brca_transcriptomics_model_handoff_manifest.yaml
tcga_brca_transcriptomics_ai_ready_benchmark_summary.yaml
tcga_brca_transcriptomics_ai_ready_benchmark_report.html
```

## Expected with current a38 feature store

```text
dataset_id: tcga_brca_transcriptomics
sample_count: 20
input_feature_count: 60660
selected_feature_count: 5000
ready_for_baseline_modeling: true
```

## Run

```powershell
python -m core.data.build_public_dataset_ai_ready_benchmark_handoff
```

## Validate

```powershell
python -m py_compile core\datauild_public_dataset_ai_ready_benchmark_handoff.py
python -m py_compile tests	est_build_public_dataset_ai_ready_benchmark_handoff.py
python -m pytest tests	est_build_public_dataset_ai_ready_benchmark_handoff.py -q
python -m pytest -q
```

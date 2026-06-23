# Public Dataset Modality Schema Validator Bundle

## Version

`v0.4.0-a31`

## Purpose

This bundled milestone adds modality-aware structural validation for real public dataset files discovered by the `v0.4.0-a30` real-file intake bundle.

It validates transcriptomics, epigenome, proteomics, and metabolomics candidate files with shared table checks and modality-specific ID-column hints. It does not download, create, or modify real replacement files.

## Inputs

```text
configs/public_data_sources/public_dataset_modality_schema_validation_request.yaml
outputs/public_data_acquisition/multi_cancer_realdata_pilot/real_file_intake/public_dataset_real_file_intake_inventory.tsv
outputs/public_data_acquisition/multi_cancer_realdata_pilot/real_file_intake/public_dataset_real_file_intake_summary.yaml
```

## Outputs

```text
outputs/public_data_acquisition/multi_cancer_realdata_pilot/modality_schema_validation/public_dataset_modality_schema_validation_table.tsv
outputs/public_data_acquisition/multi_cancer_realdata_pilot/modality_schema_validation/public_dataset_modality_schema_validation_by_modality.tsv
outputs/public_data_acquisition/multi_cancer_realdata_pilot/modality_schema_validation/public_dataset_modality_schema_validation_summary.yaml
outputs/public_data_acquisition/multi_cancer_realdata_pilot/modality_schema_validation/public_dataset_modality_schema_validation_report.html
```

## Expected result after a30

```text
dataset_count: 4
validated_schema_count: 0
awaiting_file_count: 4
failed_or_warning_count: 0
modalities_covered: 4
```

## Run

```powershell
python -m core.data.validate_public_dataset_modality_schemas
```

## Validate

```powershell
python -m py_compile core\dataalidate_public_dataset_modality_schemas.py
python -m py_compile tests	est_validate_public_dataset_modality_schemas.py
python -m pytest tests	est_validate_public_dataset_modality_schemas.py -q
python -m pytest -q
```

param(
    [string]$RepoRoot = "D:\AI project\OpenMultiOmics-Cancer-Atlas"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
cd $RepoRoot

Write-Host "=============================================="
Write-Host "v0.4.0-a31 Public Dataset Modality Schema Validation"
Write-Host "=============================================="

python -m py_compile core\data\validate_public_dataset_modality_schemas.py
python -m py_compile tests\test_validate_public_dataset_modality_schemas.py
python -m pytest tests\test_validate_public_dataset_modality_schemas.py -q
python -m pytest -q
python -m core.data.validate_public_dataset_modality_schemas

Write-Host "Done. Modality schema validation outputs should be under:"
Write-Host "outputs\public_data_acquisition\multi_cancer_realdata_pilot\modality_schema_validation"

param(
    [string]$RepoRoot = "D:\AI project\OpenMultiOmics-Cancer-Atlas"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
cd $RepoRoot

Write-Host "==============================================="
Write-Host "v0.4.0-a23 Public Dataset Replacement Readiness"
Write-Host "==============================================="

python -m py_compile core\data\validate_public_dataset_replacement_readiness.py
python -m py_compile tests\test_validate_public_dataset_replacement_readiness.py
python -m pytest tests\test_validate_public_dataset_replacement_readiness.py -q
python -m pytest -q
python -m core.data.validate_public_dataset_replacement_readiness

Write-Host "Done. Readiness outputs should be under:"
Write-Host "outputs\public_data_acquisition\multi_cancer_realdata_pilot\dataset_replacement_readiness"

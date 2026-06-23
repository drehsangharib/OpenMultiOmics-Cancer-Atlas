param(
    [string]$RepoRoot = "D:\AI project\OpenMultiOmics-Cancer-Atlas"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
cd $RepoRoot

Write-Host "=============================================="
Write-Host "v0.4.0-a25 Public Dataset Replacement Files"
Write-Host "=============================================="

python -m py_compile core\data\validate_public_dataset_replacement_files.py
python -m py_compile tests\test_validate_public_dataset_replacement_files.py
python -m pytest tests\test_validate_public_dataset_replacement_files.py -q
python -m pytest -q
python -m core.data.validate_public_dataset_replacement_files

Write-Host "Done. File validation outputs should be under:"
Write-Host "outputs\public_data_acquisition\multi_cancer_realdata_pilot\dataset_replacement_file_validation"

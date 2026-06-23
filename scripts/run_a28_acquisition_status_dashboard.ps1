param(
    [string]$RepoRoot = "D:\AI project\OpenMultiOmics-Cancer-Atlas"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
cd $RepoRoot

Write-Host "=============================================="
Write-Host "v0.4.0-a28 Public Dataset Acquisition Status"
Write-Host "=============================================="

python -m py_compile core\data\build_public_dataset_acquisition_status_dashboard.py
python -m py_compile tests\test_build_public_dataset_acquisition_status_dashboard.py
python -m pytest tests\test_build_public_dataset_acquisition_status_dashboard.py -q
python -m pytest -q
python -m core.data.build_public_dataset_acquisition_status_dashboard

Write-Host "Done. Acquisition status dashboard outputs should be under:"
Write-Host "outputs\public_data_acquisition\multi_cancer_realdata_pilot\dataset_acquisition_status_dashboard"

param(
    [string]$RepoRoot = "D:\AI project\OpenMultiOmics-Cancer-Atlas"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
cd $RepoRoot

Write-Host "==========================================="
Write-Host "v0.4.0-a27 Public Dataset Acquisition Workspace"
Write-Host "==========================================="

python -m py_compile core\data\build_public_dataset_acquisition_workspace.py
python -m py_compile tests\test_build_public_dataset_acquisition_workspace.py
python -m pytest tests\test_build_public_dataset_acquisition_workspace.py -q
python -m pytest -q
python -m core.data.build_public_dataset_acquisition_workspace

Write-Host "Done. Acquisition workspace outputs should be under:"
Write-Host "outputs\public_data_acquisition\multi_cancer_realdata_pilot\dataset_acquisition_workspace"

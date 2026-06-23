param(
    [string]$RepoRoot = "D:\AI project\OpenMultiOmics-Cancer-Atlas"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
cd $RepoRoot

Write-Host "================================================"
Write-Host "v0.4.0-a24 Public Dataset Replacement Execution"
Write-Host "================================================"

python -m py_compile core\data\build_public_dataset_replacement_execution_scaffold.py
python -m py_compile tests\test_build_public_dataset_replacement_execution_scaffold.py
python -m pytest tests\test_build_public_dataset_replacement_execution_scaffold.py -q
python -m pytest -q
python -m core.data.build_public_dataset_replacement_execution_scaffold

Write-Host "Done. Execution scaffold outputs should be under:"
Write-Host "outputs\public_data_acquisition\multi_cancer_realdata_pilot\dataset_replacement_execution_scaffold"

param(
    [string]$RepoRoot = "D:\AI project\OpenMultiOmics-Cancer-Atlas"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
cd $RepoRoot

Write-Host "=============================================="
Write-Host "v0.4.0-a30 Public Dataset Real File Intake"
Write-Host "=============================================="

python -m py_compile core\data\build_public_dataset_real_file_intake_bundle.py
python -m py_compile tests\test_build_public_dataset_real_file_intake_bundle.py
python -m pytest tests\test_build_public_dataset_real_file_intake_bundle.py -q
python -m pytest -q
python -m core.data.build_public_dataset_real_file_intake_bundle

Write-Host "Done. Real file intake outputs should be under:"
Write-Host "outputs\public_data_acquisition\multi_cancer_realdata_pilot\real_file_intake"

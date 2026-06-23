param(
    [string]$RepoRoot = "D:\AI project\OpenMultiOmics-Cancer-Atlas"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
cd $RepoRoot

Write-Host "=============================================="
Write-Host "v0.4.0-a32 Public Dataset Source Access Packets"
Write-Host "=============================================="

python -m py_compile core\data\build_public_dataset_source_access_packet.py
python -m py_compile tests\test_build_public_dataset_source_access_packet.py
python -m pytest tests\test_build_public_dataset_source_access_packet.py -q
python -m pytest -q
python -m core.data.build_public_dataset_source_access_packet

Write-Host "Done. Source access packet outputs should be under:"
Write-Host "outputs\public_data_acquisition\multi_cancer_realdata_pilot\source_access_packets"

$ErrorActionPreference = "Stop"

Write-Host "=== Running OpenMultiOmics-Cancer-Atlas v0.4.0-a41 ==="

python core\data\build_public_dataset_biological_interpretation.py `
  --config configs\public_data_sources\public_dataset_biological_interpretation_request.yaml

Write-Host ""
Write-Host "Generated a41 outputs:"
Get-ChildItem outputs\public_data_acquisition\multi_cancer_realdata_pilot\biological_interpretation -Force |
  Select-Object Name, Length, LastWriteTime |
  Format-Table -AutoSize

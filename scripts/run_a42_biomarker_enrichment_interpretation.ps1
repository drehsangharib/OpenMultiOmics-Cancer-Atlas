$ErrorActionPreference = "Stop"

Write-Host "=== Running OpenMultiOmics-Cancer-Atlas v0.4.0-a42-fix3 ==="
Write-Host "GDC STAR header recovery biomarker enrichment bridge"

python core\data\build_public_dataset_biomarker_enrichment_interpretation.py `
  --config configs\public_data_sources\public_dataset_biomarker_enrichment_interpretation_request.json

Write-Host ""
Write-Host "Generated a42-fix3 outputs:"
Get-ChildItem outputs\public_data_acquisition\multi_cancer_realdata_pilot\biomarker_enrichment_interpretation -Force |
  Select-Object Name, Length, LastWriteTime |
  Format-Table -AutoSize

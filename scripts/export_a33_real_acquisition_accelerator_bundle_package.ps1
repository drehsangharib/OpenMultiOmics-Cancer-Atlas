param([string]$RepoRoot = "D:\AI project\OpenMultiOmics-Cancer-Atlas")
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
cd $RepoRoot
$StepName="v0_4_0_a33_public_dataset_real_acquisition_accelerator_bundle_package"
$ExportRoot="exports\$StepName"; $ZipPath="exports\$StepName.zip"
New-Item -ItemType Directory -Force -Path $ExportRoot | Out-Null
New-Item -ItemType Directory -Force -Path "$ExportRoot\configs\public_data_sources","$ExportRoot\core\data","$ExportRoot\tests","$ExportRoot\docs","$ExportRoot\scripts" | Out-Null
Copy-Item "configs\public_data_sources\public_dataset_real_acquisition_accelerator_request.yaml" "$ExportRoot\configs\public_data_sources\public_dataset_real_acquisition_accelerator_request.yaml" -Force
Copy-Item "core\data\build_public_dataset_real_acquisition_accelerator.py" "$ExportRoot\core\data\build_public_dataset_real_acquisition_accelerator.py" -Force
Copy-Item "tests\test_build_public_dataset_real_acquisition_accelerator.py" "$ExportRoot\tests\test_build_public_dataset_real_acquisition_accelerator.py" -Force
Copy-Item "docs\public_dataset_real_acquisition_accelerator_bundle.md" "$ExportRoot\docs\public_dataset_real_acquisition_accelerator_bundle.md" -Force
Copy-Item "scripts\run_a33_real_acquisition_accelerator_bundle.ps1" "$ExportRoot\scripts\run_a33_real_acquisition_accelerator_bundle.ps1" -Force
Copy-Item "scripts\export_a33_real_acquisition_accelerator_bundle_package.ps1" "$ExportRoot\scripts\export_a33_real_acquisition_accelerator_bundle_package.ps1" -Force
@"
# OpenMultiOmics-Cancer-Atlas Project Tracker

## Current confirmed milestone

### v0.4.0-a33

Previous confirmed milestone: v0.4.0-a32 commit dcc5934 tag v0.4.0-a32.

Re-export correction: read_table() now safely handles optional missing inputs and no longer resolves empty optional paths to Path('.').
"@ | Out-File "$ExportRoot\PROJECT_TRACKER.md" -Encoding utf8
if (Test-Path "tracker.docx") { Copy-Item "tracker.docx" "$ExportRoot\tracker.docx" -Force }
$ManifestPath="$ExportRoot\MANIFEST.sha256.txt"; if(Test-Path $ManifestPath){Remove-Item $ManifestPath -Force}
Get-ChildItem $ExportRoot -Recurse -File | Where-Object {$_.Name -ne "MANIFEST.sha256.txt"} | ForEach-Object { $Rel=$_.FullName.Substring((Resolve-Path $ExportRoot).Path.Length+1).Replace('\','/'); $Hash=Get-FileHash $_.FullName -Algorithm SHA256; "$($Hash.Hash)  $Rel" | Out-File $ManifestPath -Encoding utf8 -Append }
if(Test-Path $ZipPath){Remove-Item $ZipPath -Force}; Compress-Archive -Path "$ExportRoot\*" -DestinationPath $ZipPath -Force
Write-Host "Created ZIP: $ZipPath"

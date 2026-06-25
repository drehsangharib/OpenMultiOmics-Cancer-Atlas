param([string]$RepoRoot = "D:\AI project\OpenMultiOmics-Cancer-Atlas")
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
cd $RepoRoot
$StepName="v0_4_0_a36_real_data_smoke_test_activation_bundle_package"
$ExportRoot="exports\$StepName"; $ZipPath="exports\$StepName.zip"
New-Item -ItemType Directory -Force -Path $ExportRoot | Out-Null
New-Item -ItemType Directory -Force -Path "$ExportRoot\configs\public_data_sources","$ExportRoot\core\data","$ExportRoot\tests","$ExportRoot\docs","$ExportRoot\scripts" | Out-Null
Copy-Item "configs\public_data_sources\public_dataset_real_data_smoke_test_activation_request.yaml" "$ExportRoot\configs\public_data_sources\public_dataset_real_data_smoke_test_activation_request.yaml" -Force
Copy-Item "core\data\build_public_dataset_real_data_smoke_test_activation.py" "$ExportRoot\core\data\build_public_dataset_real_data_smoke_test_activation.py" -Force
Copy-Item "tests\test_build_public_dataset_real_data_smoke_test_activation.py" "$ExportRoot\tests\test_build_public_dataset_real_data_smoke_test_activation.py" -Force
Copy-Item "docs\public_dataset_real_data_smoke_test_activation_bundle.md" "$ExportRoot\docs\public_dataset_real_data_smoke_test_activation_bundle.md" -Force
Copy-Item "scripts\run_a36_real_data_smoke_test_activation_bundle.ps1" "$ExportRoot\scripts\run_a36_real_data_smoke_test_activation_bundle.ps1" -Force
Copy-Item "scripts\export_a36_real_data_smoke_test_activation_bundle_package.ps1" "$ExportRoot\scripts\export_a36_real_data_smoke_test_activation_bundle_package.ps1" -Force
@"
# OpenMultiOmics-Cancer-Atlas Project Tracker

## Current confirmed milestone

### v0.4.0-a36

Previous confirmed milestone: v0.4.0-a35-fix1 commit 84a0ef5 tag v0.4.0-a35-fix1.

Purpose: real-data smoke-test activation controller for first pilot.
"@ | Out-File "$ExportRoot\PROJECT_TRACKER.md" -Encoding utf8
if(Test-Path "tracker.docx"){Copy-Item "tracker.docx" "$ExportRoot\tracker.docx" -Force}
$ManifestPath="$ExportRoot\MANIFEST.sha256.txt"; if(Test-Path $ManifestPath){Remove-Item $ManifestPath -Force}
Get-ChildItem $ExportRoot -Recurse -File | Where-Object {$_.Name -ne "MANIFEST.sha256.txt"} | ForEach-Object { $Rel=$_.FullName.Substring((Resolve-Path $ExportRoot).Path.Length+1).Replace('\','/'); $Hash=Get-FileHash $_.FullName -Algorithm SHA256; "$($Hash.Hash)  $Rel" | Out-File $ManifestPath -Encoding utf8 -Append }
if(Test-Path $ZipPath){Remove-Item $ZipPath -Force}; Compress-Archive -Path "$ExportRoot\*" -DestinationPath $ZipPath -Force
Write-Host "Created ZIP: $ZipPath"

param([string]$RepoRoot = "D:\AI project\OpenMultiOmics-Cancer-Atlas")
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
cd $RepoRoot
$StepName="v0_4_0_a39_real_data_ai_ready_benchmark_handoff_bundle_package"
$ExportRoot="exports\$StepName"; $ZipPath="exports\$StepName.zip"
New-Item -ItemType Directory -Force -Path $ExportRoot | Out-Null
New-Item -ItemType Directory -Force -Path "$ExportRoot\configs\public_data_sources","$ExportRoot\core\data","$ExportRoot\tests","$ExportRoot\docs","$ExportRoot\scripts" | Out-Null
Copy-Item "configs\public_data_sources\public_dataset_ai_ready_benchmark_handoff_request.yaml" "$ExportRoot\configs\public_data_sources\public_dataset_ai_ready_benchmark_handoff_request.yaml" -Force
Copy-Item "core\data\build_public_dataset_ai_ready_benchmark_handoff.py" "$ExportRoot\core\data\build_public_dataset_ai_ready_benchmark_handoff.py" -Force
Copy-Item "tests\test_build_public_dataset_ai_ready_benchmark_handoff.py" "$ExportRoot\tests\test_build_public_dataset_ai_ready_benchmark_handoff.py" -Force
Copy-Item "docs\public_dataset_ai_ready_benchmark_handoff_bundle.md" "$ExportRoot\docs\public_dataset_ai_ready_benchmark_handoff_bundle.md" -Force
Copy-Item "scripts\run_a39_ai_ready_benchmark_handoff_bundle.ps1" "$ExportRoot\scripts\run_a39_ai_ready_benchmark_handoff_bundle.ps1" -Force
Copy-Item "scripts\export_a39_ai_ready_benchmark_handoff_bundle_package.ps1" "$ExportRoot\scripts\export_a39_ai_ready_benchmark_handoff_bundle_package.ps1" -Force
@"
# OpenMultiOmics-Cancer-Atlas Project Tracker

## Current confirmed milestone

### v0.4.0-a39

Previous confirmed milestone: v0.4.0-a38 commit 36135bf tag v0.4.0-a38.

Purpose: create deterministic AI-ready benchmark/modeling handoff artifacts from the real TCGA-BRCA feature store.
"@ | Out-File "$ExportRoot\PROJECT_TRACKER.md" -Encoding utf8
if(Test-Path "tracker.docx"){Copy-Item "tracker.docx" "$ExportRoot\tracker.docx" -Force}
$ManifestPath="$ExportRoot\MANIFEST.sha256.txt"; if(Test-Path $ManifestPath){Remove-Item $ManifestPath -Force}
Get-ChildItem $ExportRoot -Recurse -File | Where-Object {$_.Name -ne "MANIFEST.sha256.txt"} | ForEach-Object { $Rel=$_.FullName.Substring((Resolve-Path $ExportRoot).Path.Length+1).Replace('\','/'); $Hash=Get-FileHash $_.FullName -Algorithm SHA256; "$($Hash.Hash)  $Rel" | Out-File $ManifestPath -Encoding utf8 -Append }
if(Test-Path $ZipPath){Remove-Item $ZipPath -Force}; Compress-Archive -Path "$ExportRoot\*" -DestinationPath $ZipPath -Force
Write-Host "Created ZIP: $ZipPath"

param(
    [string]$RepoRoot = "D:\AI project\OpenMultiOmics-Cancer-Atlas"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
cd $RepoRoot

$StepName = "v0_4_0_a23_public_dataset_replacement_readiness_validator_package"
$ExportRoot = "exports\$StepName"
$ZipPath = "exports\$StepName.zip"

New-Item -ItemType Directory -Force -Path $ExportRoot | Out-Null
New-Item -ItemType Directory -Force -Path "$ExportRoot\configs\public_data_sources" | Out-Null
New-Item -ItemType Directory -Force -Path "$ExportRoot\core\data" | Out-Null
New-Item -ItemType Directory -Force -Path "$ExportRoot\tests" | Out-Null
New-Item -ItemType Directory -Force -Path "$ExportRoot\docs" | Out-Null
New-Item -ItemType Directory -Force -Path "$ExportRoot\scripts" | Out-Null

Copy-Item "configs\public_data_sources\public_dataset_replacement_readiness_request.yaml" "$ExportRoot\configs\public_data_sources\public_dataset_replacement_readiness_request.yaml" -Force
Copy-Item "core\data\validate_public_dataset_replacement_readiness.py" "$ExportRoot\core\data\validate_public_dataset_replacement_readiness.py" -Force
Copy-Item "tests\test_validate_public_dataset_replacement_readiness.py" "$ExportRoot\tests\test_validate_public_dataset_replacement_readiness.py" -Force
Copy-Item "docs\public_dataset_replacement_readiness_validator.md" "$ExportRoot\docs\public_dataset_replacement_readiness_validator.md" -Force
Copy-Item "scripts\run_a23_readiness_validator.ps1" "$ExportRoot\scripts\run_a23_readiness_validator.ps1" -Force
Copy-Item "scripts\export_a23_readiness_package.ps1" "$ExportRoot\scripts\export_a23_readiness_package.ps1" -Force

$TrackerMdPath = "$ExportRoot\PROJECT_TRACKER.md"
@"
# OpenMultiOmics-Cancer-Atlas Project Tracker

## Current confirmed milestone

### v0.4.0-a23

**Step name:** v0_4_0_a23_public_dataset_replacement_readiness_validator_package

## Previous confirmed milestone

### v0.4.0-a22

**Commit:** 7ebd996  
**Tag:** v0.4.0-a22  
**Step:** Public dataset replacement workflow builder

## Current source-of-truth file set

- configs/public_data_sources/public_dataset_replacement_readiness_request.yaml
- core/data/validate_public_dataset_replacement_readiness.py
- tests/test_validate_public_dataset_replacement_readiness.py
- docs/public_dataset_replacement_readiness_validator.md
- scripts/run_a23_readiness_validator.ps1
- scripts/export_a23_readiness_package.ps1

## Purpose

Validate whether a22 public dataset replacement candidates are ready for real-file replacement validation.

## Recovery/export rule

The local repository is the source of truth. Do not reconstruct approximate scripts when exact repo files are needed. Every export must include exact source files, MANIFEST.sha256.txt, PROJECT_TRACKER.md, and tracker.docx.
"@ | Out-File $TrackerMdPath -Encoding utf8

if (Test-Path "tracker.docx") {
    Copy-Item "tracker.docx" "$ExportRoot\tracker.docx" -Force
} else {
    Write-Host "WARNING: tracker.docx not found in repo root. Copy tracker.docx from the a23 ZIP into repo root before exporting."
}

$ManifestPath = "$ExportRoot\MANIFEST.sha256.txt"
if (Test-Path $ManifestPath) { Remove-Item $ManifestPath -Force }
$RelativeFiles = @(
  "configs\public_data_sources\public_dataset_replacement_readiness_request.yaml",
  "core\data\validate_public_dataset_replacement_readiness.py",
  "tests\test_validate_public_dataset_replacement_readiness.py",
  "docs\public_dataset_replacement_readiness_validator.md",
  "scripts\run_a23_readiness_validator.ps1",
  "scripts\export_a23_readiness_package.ps1",
  "PROJECT_TRACKER.md",
  "tracker.docx"
)
foreach ($RelPath in $RelativeFiles) {
    $FullPath = Join-Path $ExportRoot $RelPath
    if (Test-Path $FullPath) {
        $Hash = Get-FileHash $FullPath -Algorithm SHA256
        "$($Hash.Hash)  $($RelPath -replace '\\','/')" | Out-File $ManifestPath -Encoding utf8 -Append
    } else {
        "MISSING  $($RelPath -replace '\\','/')" | Out-File $ManifestPath -Encoding utf8 -Append
    }
}

if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path "$ExportRoot\*" -DestinationPath $ZipPath -Force
Write-Host "Created ZIP: $ZipPath"
Get-Content $ManifestPath

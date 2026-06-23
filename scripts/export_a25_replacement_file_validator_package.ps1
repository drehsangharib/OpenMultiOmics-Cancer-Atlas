param(
    [string]$RepoRoot = "D:\AI project\OpenMultiOmics-Cancer-Atlas"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
cd $RepoRoot

$StepName = "v0_4_0_a25_public_dataset_replacement_file_validator_package"
$ExportRoot = "exports\$StepName"
$ZipPath = "exports\$StepName.zip"

New-Item -ItemType Directory -Force -Path $ExportRoot | Out-Null
New-Item -ItemType Directory -Force -Path "$ExportRoot\configs\public_data_sources" | Out-Null
New-Item -ItemType Directory -Force -Path "$ExportRoot\core\data" | Out-Null
New-Item -ItemType Directory -Force -Path "$ExportRoot\tests" | Out-Null
New-Item -ItemType Directory -Force -Path "$ExportRoot\docs" | Out-Null
New-Item -ItemType Directory -Force -Path "$ExportRoot\scripts" | Out-Null

Copy-Item "configs\public_data_sources\public_dataset_replacement_file_validation_request.yaml" "$ExportRoot\configs\public_data_sources\public_dataset_replacement_file_validation_request.yaml" -Force
Copy-Item "core\data\validate_public_dataset_replacement_files.py" "$ExportRoot\core\data\validate_public_dataset_replacement_files.py" -Force
Copy-Item "tests\test_validate_public_dataset_replacement_files.py" "$ExportRoot\tests\test_validate_public_dataset_replacement_files.py" -Force
Copy-Item "docs\public_dataset_replacement_file_validator.md" "$ExportRoot\docs\public_dataset_replacement_file_validator.md" -Force
Copy-Item "scripts\run_a25_replacement_file_validator.ps1" "$ExportRoot\scripts\run_a25_replacement_file_validator.ps1" -Force
Copy-Item "scripts\export_a25_replacement_file_validator_package.ps1" "$ExportRoot\scripts\export_a25_replacement_file_validator_package.ps1" -Force

$TrackerMdPath = "$ExportRoot\PROJECT_TRACKER.md"
@"
# OpenMultiOmics-Cancer-Atlas Project Tracker

## Current confirmed milestone

### v0.4.0-a25

**Step name:** v0_4_0_a25_public_dataset_replacement_file_validator_package

## Previous confirmed milestones

### v0.4.0-a24-fix1

**Commit:** bfb9951  
**Tag:** v0.4.0-a24-fix1  
**Step:** Added missing a24 export package script

### v0.4.0-a24

**Commit:** 4fa8d41  
**Tag:** v0.4.0-a24  
**Step:** Public dataset replacement execution scaffold

## Current source-of-truth file set

- configs/public_data_sources/public_dataset_replacement_file_validation_request.yaml
- core/data/validate_public_dataset_replacement_files.py
- tests/test_validate_public_dataset_replacement_files.py
- docs/public_dataset_replacement_file_validator.md
- scripts/run_a25_replacement_file_validator.ps1
- scripts/export_a25_replacement_file_validator_package.ps1

## Purpose

Validate local real public dataset replacement files before downstream replacement execution.

## Expected current result

- replacement candidates: 4
- ready execution jobs: 0
- validated real files: 0
- skipped not ready: 4

## Recovery/export rule

The local repository is the source of truth. Do not reconstruct approximate scripts when exact repo files are needed. Every export must include exact source files, MANIFEST.sha256.txt, PROJECT_TRACKER.md, and tracker.docx.
"@ | Out-File $TrackerMdPath -Encoding utf8

if (Test-Path "tracker.docx") {
    Copy-Item "tracker.docx" "$ExportRoot\tracker.docx" -Force
} else {
    Write-Host "WARNING: tracker.docx not found in repo root. Copy tracker.docx from the a25 ZIP into repo root before exporting if you need a Word tracker."
}

$ManifestPath = "$ExportRoot\MANIFEST.sha256.txt"
if (Test-Path $ManifestPath) { Remove-Item $ManifestPath -Force }
$RelativeFiles = @(
  "configs\public_data_sources\public_dataset_replacement_file_validation_request.yaml",
  "core\data\validate_public_dataset_replacement_files.py",
  "tests\test_validate_public_dataset_replacement_files.py",
  "docs\public_dataset_replacement_file_validator.md",
  "scripts\run_a25_replacement_file_validator.ps1",
  "scripts\export_a25_replacement_file_validator_package.ps1",
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

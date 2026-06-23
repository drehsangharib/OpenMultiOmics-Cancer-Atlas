param(
    [string]$RepoRoot = "D:\AI project\OpenMultiOmics-Cancer-Atlas"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
cd $RepoRoot

$StepName = "v0_4_0_a31_public_dataset_modality_schema_validator_bundle_package"
$ExportRoot = "exports\$StepName"
$ZipPath = "exports\$StepName.zip"

New-Item -ItemType Directory -Force -Path $ExportRoot | Out-Null
New-Item -ItemType Directory -Force -Path "$ExportRoot\configs\public_data_sources" | Out-Null
New-Item -ItemType Directory -Force -Path "$ExportRoot\core\data" | Out-Null
New-Item -ItemType Directory -Force -Path "$ExportRoot\tests" | Out-Null
New-Item -ItemType Directory -Force -Path "$ExportRoot\docs" | Out-Null
New-Item -ItemType Directory -Force -Path "$ExportRoot\scripts" | Out-Null

Copy-Item "configs\public_data_sources\public_dataset_modality_schema_validation_request.yaml" "$ExportRoot\configs\public_data_sources\public_dataset_modality_schema_validation_request.yaml" -Force
Copy-Item "core\data\validate_public_dataset_modality_schemas.py" "$ExportRoot\core\data\validate_public_dataset_modality_schemas.py" -Force
Copy-Item "tests\test_validate_public_dataset_modality_schemas.py" "$ExportRoot\tests\test_validate_public_dataset_modality_schemas.py" -Force
Copy-Item "docs\public_dataset_modality_schema_validator_bundle.md" "$ExportRoot\docs\public_dataset_modality_schema_validator_bundle.md" -Force
Copy-Item "scripts\run_a31_modality_schema_validator_bundle.ps1" "$ExportRoot\scripts\run_a31_modality_schema_validator_bundle.ps1" -Force
Copy-Item "scripts\export_a31_modality_schema_validator_bundle_package.ps1" "$ExportRoot\scripts\export_a31_modality_schema_validator_bundle_package.ps1" -Force

$TrackerMdPath = "$ExportRoot\PROJECT_TRACKER.md"
@"
# OpenMultiOmics-Cancer-Atlas Project Tracker

## Current confirmed milestone

### v0.4.0-a31

**Step name:** v0_4_0_a31_public_dataset_modality_schema_validator_bundle_package

## Previous confirmed milestone

### v0.4.0-a30

**Commit:** db6b421  
**Tag:** v0.4.0-a30  
**Step:** Public dataset real file intake bundle

## Purpose

Run modality-aware schema validation for real public dataset files from the a30 intake bundle.

## Expected current result

- dataset count: 4
- validated schemas: 0
- awaiting files: 4
- failed/warning: 0
- modalities covered: 4

## Recovery/export rule

The local repository is the source of truth. Do not reconstruct approximate scripts when exact repo files are needed. Every export must include exact source files, MANIFEST.sha256.txt, PROJECT_TRACKER.md, and tracker.docx.
"@ | Out-File $TrackerMdPath -Encoding utf8

if (Test-Path "tracker.docx") { Copy-Item "tracker.docx" "$ExportRoot\tracker.docx" -Force }

$ManifestPath = "$ExportRoot\MANIFEST.sha256.txt"
if (Test-Path $ManifestPath) { Remove-Item $ManifestPath -Force }
$RelativeFiles = @(
  "configs\public_data_sources\public_dataset_modality_schema_validation_request.yaml",
  "core\data\validate_public_dataset_modality_schemas.py",
  "tests\test_validate_public_dataset_modality_schemas.py",
  "docs\public_dataset_modality_schema_validator_bundle.md",
  "scripts\run_a31_modality_schema_validator_bundle.ps1",
  "scripts\export_a31_modality_schema_validator_bundle_package.ps1",
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

param(
    [string]$RepoRoot = "D:\AI project\OpenMultiOmics-Cancer-Atlas"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
cd $RepoRoot

$StepName = "v0_4_0_a28_public_dataset_acquisition_status_dashboard_package"
$ExportRoot = "exports\$StepName"
$ZipPath = "exports\$StepName.zip"

New-Item -ItemType Directory -Force -Path $ExportRoot | Out-Null
New-Item -ItemType Directory -Force -Path "$ExportRoot\configs\public_data_sources" | Out-Null
New-Item -ItemType Directory -Force -Path "$ExportRoot\core\data" | Out-Null
New-Item -ItemType Directory -Force -Path "$ExportRoot\tests" | Out-Null
New-Item -ItemType Directory -Force -Path "$ExportRoot\docs" | Out-Null
New-Item -ItemType Directory -Force -Path "$ExportRoot\scripts" | Out-Null

Copy-Item "configs\public_data_sources\public_dataset_acquisition_status_dashboard_request.yaml" "$ExportRoot\configs\public_data_sources\public_dataset_acquisition_status_dashboard_request.yaml" -Force
Copy-Item "core\data\build_public_dataset_acquisition_status_dashboard.py" "$ExportRoot\core\data\build_public_dataset_acquisition_status_dashboard.py" -Force
Copy-Item "tests\test_build_public_dataset_acquisition_status_dashboard.py" "$ExportRoot\tests\test_build_public_dataset_acquisition_status_dashboard.py" -Force
Copy-Item "docs\public_dataset_acquisition_status_dashboard.md" "$ExportRoot\docs\public_dataset_acquisition_status_dashboard.md" -Force
Copy-Item "scripts\run_a28_acquisition_status_dashboard.ps1" "$ExportRoot\scripts\run_a28_acquisition_status_dashboard.ps1" -Force
Copy-Item "scripts\export_a28_acquisition_status_dashboard_package.ps1" "$ExportRoot\scripts\export_a28_acquisition_status_dashboard_package.ps1" -Force

$TrackerMdPath = "$ExportRoot\PROJECT_TRACKER.md"
@"
# OpenMultiOmics-Cancer-Atlas Project Tracker

## Current confirmed milestone

### v0.4.0-a28

**Step name:** v0_4_0_a28_public_dataset_acquisition_status_dashboard_package

## Previous confirmed milestone

### v0.4.0-a27

**Commit:** 9d18ebb  
**Tag:** v0.4.0-a27  
**Step:** Public dataset acquisition workspace builder

## Current source-of-truth file set

- configs/public_data_sources/public_dataset_acquisition_status_dashboard_request.yaml
- core/data/build_public_dataset_acquisition_status_dashboard.py
- tests/test_build_public_dataset_acquisition_status_dashboard.py
- docs/public_dataset_acquisition_status_dashboard.md
- scripts/run_a28_acquisition_status_dashboard.ps1
- scripts/export_a28_acquisition_status_dashboard_package.ps1

## Purpose

Summarize public dataset acquisition progress by dataset, source, and modality.

## Expected current result

- dataset count: 4
- pending acquisition: 4
- local files present: 0
- workspace incomplete: 0

## Recovery/export rule

The local repository is the source of truth. Do not reconstruct approximate scripts when exact repo files are needed. Every export must include exact source files, MANIFEST.sha256.txt, PROJECT_TRACKER.md, and tracker.docx.
"@ | Out-File $TrackerMdPath -Encoding utf8

if (Test-Path "tracker.docx") {
    Copy-Item "tracker.docx" "$ExportRoot\tracker.docx" -Force
} else {
    Write-Host "WARNING: tracker.docx not found in repo root. Copy tracker.docx from the a28 ZIP into repo root before exporting if you need a Word tracker."
}

$ManifestPath = "$ExportRoot\MANIFEST.sha256.txt"
if (Test-Path $ManifestPath) { Remove-Item $ManifestPath -Force }
$RelativeFiles = @(
  "configs\public_data_sources\public_dataset_acquisition_status_dashboard_request.yaml",
  "core\data\build_public_dataset_acquisition_status_dashboard.py",
  "tests\test_build_public_dataset_acquisition_status_dashboard.py",
  "docs\public_dataset_acquisition_status_dashboard.md",
  "scripts\run_a28_acquisition_status_dashboard.ps1",
  "scripts\export_a28_acquisition_status_dashboard_package.ps1",
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

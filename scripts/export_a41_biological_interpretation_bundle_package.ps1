$ErrorActionPreference = "Stop"

$PackageName = "v0_4_0_a41_biological_interpretation_layer_package"
$ExportRoot = "exports\$PackageName"
$ZipPath = "exports\$PackageName.zip"

if (Test-Path $ExportRoot) { Remove-Item $ExportRoot -Recurse -Force }
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
New-Item -ItemType Directory -Force $ExportRoot | Out-Null

$Files = @(
    "configs\public_data_sources\public_dataset_biological_interpretation_request.yaml",
    "core\data\build_public_dataset_biological_interpretation.py",
    "tests\test_build_public_dataset_biological_interpretation.py",
    "docs\public_dataset_biological_interpretation_layer.md",
    "scripts\run_a41_biological_interpretation_bundle.ps1",
    "scripts\export_a41_biological_interpretation_bundle_package.ps1"
)

foreach ($File in $Files) {
    if (-not (Test-Path $File)) { throw "Missing package file: $File" }
    $Dest = Join-Path $ExportRoot $File
    New-Item -ItemType Directory -Force (Split-Path $Dest -Parent) | Out-Null
    Copy-Item $File $Dest -Force
}

$Tracker = @"
# OpenMultiOmics-Cancer-Atlas — Project Tracker

## Current State

- Project: OpenMultiOmics-Cancer-Atlas
- Current milestone: v0.4.0-a41
- Current milestone scope: biological interpretation layer
- Upstream confirmed milestone: v0.4.0-a40
- Upstream confirmed commit: 716a7ce
- Upstream confirmed tag: v0.4.0-a40
- Previous milestone: v0.4.0-a39
- Previous commit: 8153557

## v0.4.0-a41 Files

- configs/public_data_sources/public_dataset_biological_interpretation_request.yaml
- core/data/build_public_dataset_biological_interpretation.py
- tests/test_build_public_dataset_biological_interpretation.py
- docs/public_dataset_biological_interpretation_layer.md
- scripts/run_a41_biological_interpretation_bundle.ps1
- scripts/export_a41_biological_interpretation_bundle_package.ps1

## Runtime Outputs

Generated under:

outputs/public_data_acquisition/multi_cancer_realdata_pilot/biological_interpretation/

Expected outputs:

- pca_kmeans_clusters.png
- top_feature_importance.png
- top_features_interpretation.tsv
- gene_set_interpretation.tsv
- biological_interpretation_report.md
- biological_interpretation_summary.json

## Commands

pytest tests\test_build_public_dataset_biological_interpretation.py -q

powershell -ExecutionPolicy Bypass -File scripts\run_a41_biological_interpretation_bundle.ps1

powershell -ExecutionPolicy Bypass -File scripts\export_a41_biological_interpretation_bundle_package.ps1

## Commit Policy

Commit source/config/test/doc/script files only.

Do not commit outputs/, exports/, downloads/, or data/public/.
"@

$TrackerPath = "$ExportRoot\PROJECT_TRACKER.md"
$Tracker | Set-Content -Path $TrackerPath -Encoding UTF8

$RunNotes = @"
# Install and Run Notes

## Test

pytest tests\test_build_public_dataset_biological_interpretation.py -q

## Run

powershell -ExecutionPolicy Bypass -File scripts\run_a41_biological_interpretation_bundle.ps1

## Export

powershell -ExecutionPolicy Bypass -File scripts\export_a41_biological_interpretation_bundle_package.ps1

## Commit and Tag

git add configs\public_data_sources\public_dataset_biological_interpretation_request.yaml
git add core\data\build_public_dataset_biological_interpretation.py
git add tests\test_build_public_dataset_biological_interpretation.py
git add docs\public_dataset_biological_interpretation_layer.md
git add scripts\run_a41_biological_interpretation_bundle.ps1
git add scripts\export_a41_biological_interpretation_bundle_package.ps1

git commit -m "Add biological interpretation layer"
git tag v0.4.0-a41
git push
git push origin v0.4.0-a41
"@
$RunNotes | Set-Content -Path "$ExportRoot\INSTALL_AND_RUN_NOTES.md" -Encoding UTF8

$Manifest = "$ExportRoot\MANIFEST.sha256.txt"
Get-ChildItem $ExportRoot -Recurse -File |
    Where-Object { $_.Name -ne "MANIFEST.sha256.txt" } |
    Sort-Object FullName |
    ForEach-Object {
        $Hash = Get-FileHash $_.FullName -Algorithm SHA256
        $Relative = $_.FullName.Substring((Resolve-Path $ExportRoot).Path.Length + 1)
        "$($Hash.Hash)  $Relative"
    } | Set-Content -Path $Manifest -Encoding UTF8

Compress-Archive -Path "$ExportRoot\*" -DestinationPath $ZipPath -Force
Write-Host "Export complete: $ZipPath"

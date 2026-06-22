# Public-Data Pilot Release Bundle

## Purpose

`core/data/build_public_data_pilot_release_bundle.py` packages public-data pilot integration outputs into a reproducible release bundle.

## North star

```text
AI-driven raw-data-to-biological-insight platform
```

This step turns the public-data pilot integration run into a shareable release artifact.

## Main command

```powershell
python -m core.data.build_public_data_pilot_release_bundle
```

## Required prior steps

```powershell
python -m core.data.build_public_data_acquisition_plan
python -m core.data.materialize_public_data_files
python -m core.data.run_public_data_execution_smoke
python -m core.data.build_public_data_pilot_bundle
python -m core.data.run_public_data_pilot_integration
```

## Outputs

```text
outputs/public_data_acquisition/<atlas>/pilot_release_bundle/public_data_pilot_release_manifest.yaml
outputs/public_data_acquisition/<atlas>/pilot_release_bundle/public_data_pilot_release_inventory.tsv
outputs/public_data_acquisition/<atlas>/pilot_release_bundle/public_data_pilot_release_report.html
outputs/public_data_acquisition/<atlas>/pilot_release_bundle/README.md
outputs/public_data_acquisition/<atlas>/pilot_release_bundle/OpenMultiOmics_public_data_pilot_release_bundle.zip
```

## Suggested release tag

```text
v0.4.0-a20 = Public-data pilot release bundle
```

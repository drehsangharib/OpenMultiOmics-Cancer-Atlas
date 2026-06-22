# Public Data Pilot Feature-Store Bundle

## Purpose

`core/data/build_public_data_pilot_bundle.py` collects smoke-tested public-data feature stores into a reusable pilot bundle.

## North star

```text
AI-driven raw-data-to-biological-insight platform
```

This step turns public-data smoke execution into a portable bundle that can feed downstream multi-omics integration and end-to-end demos.

## Main command

```powershell
python -m core.data.build_public_data_pilot_bundle
```

## Required prior steps

```powershell
python -m core.data.build_public_data_acquisition_plan
python -m core.data.materialize_public_data_files
python -m core.data.run_public_data_execution_smoke
```

## Outputs

```text
outputs/public_data_acquisition/<atlas>/pilot_feature_store_bundle/pilot_feature_store_bundle_inventory.tsv
outputs/public_data_acquisition/<atlas>/pilot_feature_store_bundle/copied_feature_store_artifacts.tsv
outputs/public_data_acquisition/<atlas>/pilot_feature_store_bundle/pilot_bundle_modality_summary.tsv
outputs/public_data_acquisition/<atlas>/pilot_feature_store_bundle/pilot_feature_store_bundle_manifest.yaml
outputs/public_data_acquisition/<atlas>/pilot_feature_store_bundle/pilot_feature_store_bundle_report.html
outputs/public_data_acquisition/<atlas>/pilot_feature_store_bundle/OpenMultiOmics_public_data_pilot_feature_store_bundle.zip
```

## Suggested release tag

```text
v0.4.0-a18 = Public-data pilot feature-store bundle builder
```

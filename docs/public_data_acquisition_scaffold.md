# Public Data Acquisition Scaffold

## Purpose

`core/data/build_public_data_acquisition_plan.py` creates a public-data acquisition plan and local manifest templates for real-dataset OpenMultiOmics pilots.

## North star

```text
AI-driven raw-data-to-biological-insight platform
```

This step starts the transition from synthetic demonstration matrices to real public-data-backed runs.

## Main command

```powershell
python -m core.data.build_public_data_acquisition_plan
```

## Outputs

```text
outputs/public_data_acquisition/<atlas>/public_data_source_inventory.tsv
outputs/public_data_acquisition/<atlas>/public_data_acquisition_plan.tsv
outputs/public_data_acquisition/<atlas>/manifest_template_inventory.tsv
outputs/public_data_acquisition/<atlas>/public_data_acquisition_summary.yaml
outputs/public_data_acquisition/<atlas>/public_data_acquisition_report.html
outputs/public_data_acquisition/<atlas>/manifest_templates/*.yaml
```

## Interpretation status

This is an acquisition scaffold. It intentionally avoids network calls inside tests and expects user-exported public repository manifests or local downloaded matrices.

## Suggested release tag

```text
v0.4.0-a15 = Public-data acquisition and real-dataset demo scaffold
```

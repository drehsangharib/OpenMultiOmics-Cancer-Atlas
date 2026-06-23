# Public Dataset Acquisition Status Dashboard

## Version

`v0.4.0-a28`

## Purpose

This step builds an acquisition status dashboard from the `v0.4.0-a27` public dataset acquisition workspace.

It gives an operational view of which public replacement datasets still need acquisition, which local target files are present, and whether each dataset workspace has a README/checklist.

## Inputs

Default request file:

```text
configs/public_data_sources/public_dataset_acquisition_status_dashboard_request.yaml
```

The request points to the a27 outputs:

```text
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_acquisition_workspace/public_dataset_acquisition_workspace_index.tsv
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_acquisition_workspace/public_dataset_acquisition_workspace_summary.yaml
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_acquisition_workspace/public_dataset_acquisition_workspace_source_artifact_index.tsv
```

## Outputs

Default output directory:

```text
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_acquisition_status_dashboard
```

Generated files:

```text
public_dataset_acquisition_status_dashboard.tsv
public_dataset_acquisition_status_by_source.tsv
public_dataset_acquisition_status_by_modality.tsv
public_dataset_acquisition_status_source_artifact_index.tsv
public_dataset_acquisition_status_summary.yaml
public_dataset_acquisition_status_report.html
```

## Expected result after a27

Because the current a27 state is expected to contain four acquisition workspaces and no local real files, the expected initial a28 result is:

```text
dataset_count: 4
pending_acquisition_count: 4
local_file_present_count: 0
workspace_incomplete_count: 0
```

## Run

From the repository root:

```powershell
python -m core.data.build_public_dataset_acquisition_status_dashboard
```

## Validate

```powershell
python -m py_compile core\datauild_public_dataset_acquisition_status_dashboard.py
python -m py_compile tests	est_build_public_dataset_acquisition_status_dashboard.py
python -m pytest tests	est_build_public_dataset_acquisition_status_dashboard.py -q
python -m pytest -q
```

## Agent role

This stage creates a dashboard-like operational view of public dataset acquisition progress across source repositories and omics modalities.

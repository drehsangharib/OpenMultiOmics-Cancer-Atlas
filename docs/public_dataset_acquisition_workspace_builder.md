# Public Dataset Acquisition Workspace Builder

## Version

`v0.4.0-a27`

## Purpose

This step creates a local acquisition workspace from the `v0.4.0-a26` public dataset acquisition instructions.

It does not download public data and does not create or modify real replacement files. It creates auditable per-dataset workspace directories and README checklists that tell the user what to acquire, where to place it, and which validation commands to rerun.

## Inputs

Default request file:

```text
configs/public_data_sources/public_dataset_acquisition_workspace_request.yaml
```

The request points to the a26 outputs:

```text
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_acquisition_instructions/public_dataset_acquisition_instructions.tsv
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_acquisition_instructions/public_dataset_acquisition_instructions_summary.yaml
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_acquisition_instructions/public_dataset_acquisition_instructions_source_artifact_index.tsv
```

## Outputs

Default output directory:

```text
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_acquisition_workspace
```

Generated files:

```text
public_dataset_acquisition_workspace_index.tsv
public_dataset_acquisition_workspace_source_artifact_index.tsv
public_dataset_acquisition_workspace_summary.yaml
public_dataset_acquisition_workspace_report.html
dataset_workspaces/<dataset_id>/README.md
```

## Expected result after a26

Because the current a26 state is expected to contain four acquisition instructions and no local real files, the expected initial a27 result is:

```text
workspace_dataset_count: 4
acquisition_needed_count: 4
dataset_readme_count: 4
local_file_present_count: 0
```

## Run

From the repository root:

```powershell
python -m core.data.build_public_dataset_acquisition_workspace
```

## Validate

```powershell
python -m py_compile core\datauild_public_dataset_acquisition_workspace.py
python -m py_compile tests	est_build_public_dataset_acquisition_workspace.py
python -m pytest tests	est_build_public_dataset_acquisition_workspace.py -q
python -m pytest -q
```

## Agent role

This stage turns acquisition instructions into a local operational workspace for real public dataset acquisition.

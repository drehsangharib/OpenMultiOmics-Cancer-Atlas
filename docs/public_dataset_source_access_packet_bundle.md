# Public Dataset Source Access Packet Bundle

## Version

`v0.4.0-a32`

## Purpose

This milestone creates source-specific access packets for each public dataset candidate. It is designed to turn the prior planning/intake/validation layers into concrete operator-facing acquisition packets.

The bundle does not download public data. It creates portal links, source-specific command templates, per-dataset YAML packets, and a source access report.

## Inputs

```text
configs/public_data_sources/public_dataset_source_access_packet_request.yaml
configs/public_data_sources/public_dataset_accession_registry.yaml
outputs/public_data_acquisition/multi_cancer_realdata_pilot/dataset_acquisition_operations/public_dataset_acquisition_task_board.tsv
outputs/public_data_acquisition/multi_cancer_realdata_pilot/real_file_intake/public_dataset_real_file_intake_inventory.tsv
outputs/public_data_acquisition/multi_cancer_realdata_pilot/modality_schema_validation/public_dataset_modality_schema_validation_table.tsv
```

## Outputs

```text
outputs/public_data_acquisition/multi_cancer_realdata_pilot/source_access_packets/public_dataset_source_access_packets.tsv
outputs/public_data_acquisition/multi_cancer_realdata_pilot/source_access_packets/public_dataset_source_portal_links.tsv
outputs/public_data_acquisition/multi_cancer_realdata_pilot/source_access_packets/public_dataset_source_command_templates.ps1
outputs/public_data_acquisition/multi_cancer_realdata_pilot/source_access_packets/public_dataset_source_packet_yaml_inventory.tsv
outputs/public_data_acquisition/multi_cancer_realdata_pilot/source_access_packets/public_dataset_source_access_summary.yaml
outputs/public_data_acquisition/multi_cancer_realdata_pilot/source_access_packets/public_dataset_source_access_report.html
outputs/public_data_acquisition/multi_cancer_realdata_pilot/source_access_packets/source_packet_yamls/*.yaml
```

## Expected result after a31

```text
source_packet_count: 4
source_count: 3
modality_count: 4
placeholder_accession_count: 1
packet_yaml_count: 4
```

## Run

```powershell
python -m core.data.build_public_dataset_source_access_packet
```

## Validate

```powershell
python -m py_compile core\datauild_public_dataset_source_access_packet.py
python -m py_compile tests	est_build_public_dataset_source_access_packet.py
python -m pytest tests	est_build_public_dataset_source_access_packet.py -q
python -m pytest -q
```

# End-to-End Release Bundle

## Purpose

`core/releases/build_end_to_end_release_bundle.py` packages the OpenMultiOmics end-to-end demo outputs into a reproducible release bundle.

## North star

```text
AI-driven raw-data-to-biological-insight platform
```

This step creates a shareable and auditable release artifact from the full demo path:

```text
feature stores
-> integration manifest
-> integrated feature table
-> AI analysis context
-> baseline analysis
-> biological insight seed
-> program annotation
-> pathway-ready evidence
-> external annotation evidence
-> release bundle
```

## Main command

```powershell
python -m core.releases.build_end_to_end_release_bundle
```

## Outputs

```text
outputs/releases/v0.4.0-a14/release_manifest.yaml
outputs/releases/v0.4.0-a14/release_artifact_inventory.tsv
outputs/releases/v0.4.0-a14/release_capability_map.tsv
outputs/releases/v0.4.0-a14/release_summary_report.html
outputs/releases/v0.4.0-a14/README.md
outputs/releases/v0.4.0-a14/OpenMultiOmics_v0.4.0-a14_release_bundle.zip
```

## Suggested release tag

```text
v0.4.0-a14 = End-to-end release bundle
```

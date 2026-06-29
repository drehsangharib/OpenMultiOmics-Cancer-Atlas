# OpenMultiOmics-Cancer-Atlas v0.4.0-a41

## Biological Interpretation Layer

This milestone builds directly on finalized `v0.4.0-a40`.

## Upstream baseline

- Tag: `v0.4.0-a40`
- Commit: `716a7ce`
- Upstream outputs:
  - PCA coordinates
  - KMeans clusters
  - Random Forest feature importance
  - modeling summary

## Purpose

`v0.4.0-a41` converts the baseline modeling outputs into biological interpretation outputs:

- PCA/KMeans figure
- top feature-importance figure
- top-feature interpretation table
- gene-set scaffold table
- biological interpretation report
- summary JSON

## Run

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_a41_biological_interpretation_bundle.ps1
```

## Test

```powershell
pytest tests\test_build_public_dataset_biological_interpretation.py -q
```

## Export

```powershell
powershell -ExecutionPolicy Bypass -File scripts\export_a41_biological_interpretation_bundle_package.ps1
```

## Commit policy

Commit only source/config/test/doc/script files.

Do not commit:

- `outputs/`
- `exports/`
- `downloads/`
- `data/public/`

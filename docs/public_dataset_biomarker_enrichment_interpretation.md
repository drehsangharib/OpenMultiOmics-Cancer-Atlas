# OpenMultiOmics-Cancer-Atlas v0.4.0-a42-fix3

## GDC STAR Header Recovery

This fix handles GDC STAR-count files that contain metadata or comment/preamble lines before the true `gene_id/gene_name` header. The script now scans file lines for a header containing both gene ID and gene symbol/name columns, reads from that header, recovers `gene_id -> gene_name`, and reruns biomarker enrichment quality gates.

## Run

```powershell
pytest tests\test_build_public_dataset_biomarker_enrichment_interpretation.py -q
pytest -q
powershell -ExecutionPolicy Bypass -File scripts\run_a42_biomarker_enrichment_interpretation.ps1
```

## Commit policy

Commit only source/config/test/doc/script files. Do not commit downloads/, data/public/, outputs/, or exports/.

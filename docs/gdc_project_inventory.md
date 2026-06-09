\# GDC Project Inventory Module



\## Purpose



`core/search/gdc\_project\_inventory.py` fetches public project-level metadata from the NCI Genomic Data Commons (GDC) and writes a local TSV inventory.



This module is part of Milestone 1B: real public dataset harvesting.



\## Why GDC?



GDC provides programmatic access to cancer data and metadata through its REST API. The API supports search, retrieval, and download-oriented workflows across endpoints such as `projects`, `cases`, and `files`.



\## Command



```powershell

python -m core.search.gdc\_project\_inventory


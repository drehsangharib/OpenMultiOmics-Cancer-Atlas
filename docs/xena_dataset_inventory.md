\# UCSC Xena Dataset Inventory



\## Purpose



`core/search/xena\_dataset\_inventory.py` builds a metadata-only inventory of datasets available from selected UCSC Xena hubs.



This module is part of Milestone 1E.4: live UCSC Xena dataset inventory crawler.



\## Scope



This module queries Xena hub dataset lists and writes dataset-level metadata.



It does not download:



```text

large expression matrices

copy-number matrices

methylation matrices

mutation matrices

clinical matrices


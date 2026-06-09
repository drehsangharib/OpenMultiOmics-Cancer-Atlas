\# GDC File Counts by Project



\## Purpose



`core/search/gdc\_file\_counts\_by\_project.py` summarizes public GDC file availability by project.



This module is part of Milestone 1B: real public dataset harvesting.



\## Why this matters



The project inventory tells us which GDC projects exist. The file-count summary tells us what kinds of data each project contains.



This lets the atlas identify which cancer projects have:



\- RNA-seq

\- methylation

\- mutation data

\- copy-number data

\- clinical or biospecimen files

\- open versus controlled-access files



\## Commands



Run one project first:



```powershell

python -m core.search.gdc\_file\_counts\_by\_project --project-id TCGA-GBM


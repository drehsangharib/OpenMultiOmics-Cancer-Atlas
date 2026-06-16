\# Keyword-Driven Public Omics Atlas QC Report



\## Purpose



`core/atlas/report\_keyword\_public\_omics\_atlas\_qc.py` generates a reusable metadata-only QC report for any atlas slice built by `core/atlas/build\_keyword\_public\_omics\_atlas.py`.



This module generalizes the atlas QC layer so that atlas-specific QC reports can be generated for GBM, LUAD, BRCA, or any other keyword-defined atlas.



\## Input



By default, this module reads:



```text

outputs/atlases/<atlas\_name>/<atlas\_name>\_public\_omics\_atlas\_inventory.tsv


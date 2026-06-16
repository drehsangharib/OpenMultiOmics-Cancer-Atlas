\# GBM Public Omics Atlas Pipeline



\## Purpose



`atlases/gbm/run\_gbm\_public\_omics\_atlas\_pipeline.py` runs the full GBM public omics atlas workflow in one command.



This pipeline can:



\- optionally refresh UCSC Xena metadata

\- build the unified public cancer omics inventory

\- generate the unified QC report

\- build the GBM atlas slice

\- generate the GBM atlas report

\- generate the GBM atlas QC report

\- optionally open the final GBM reports



\## Main command



```powershell

python -m atlases.gbm.run\_gbm\_public\_omics\_atlas\_pipeline --make-report --make-qc-report




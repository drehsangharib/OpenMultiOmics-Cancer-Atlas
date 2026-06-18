\# Transcriptomics Feature-Store Pipeline



\## Purpose



`core/modalities/process\_transcriptomics\_matrix.py` processes a transcriptomics matrix defined by a data manifest and writes standardized feature-store outputs.



\## Current role



This is the first executable modality pipeline in the AI multi-omics analysis agent/system.



\## Main command



```powershell

python -m core.modalities.process\_transcriptomics\_matrix --manifest configs\\data\_manifests\\example\_transcriptomics\_manifest.yaml


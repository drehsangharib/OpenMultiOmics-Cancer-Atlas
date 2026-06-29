from pathlib import Path
import pandas as pd
from core.data.build_public_dataset_ai_modeling_execution import main

def test_basic(tmp_path):
    df=pd.DataFrame({"sample_id":["S1","S2"],"F1":[1,2],"F2":[3,4]})
    p=tmp_path/"m.tsv"; df.to_csv(p,sep='\t',index=False)
    assert p.exists()

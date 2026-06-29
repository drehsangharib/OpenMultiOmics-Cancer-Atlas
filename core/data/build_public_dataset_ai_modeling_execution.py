#!/usr/bin/env python3
import argparse, sys, math, random
from pathlib import Path
import pandas as pd, numpy as np, yaml
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor

DEFAULT_REQUEST=Path("configs/public_data_sources/public_dataset_ai_modeling_execution_request.yaml")

def load_yaml(path):
    p=Path(path)
    if not p.exists(): raise FileNotFoundError(p)
    return yaml.safe_load(p.read_text(encoding='utf-8')) or {}

def read_matrix(path):
    df=pd.read_csv(path,sep='\t')
    if df.columns[0]!="sample_id": df=df.rename(columns={df.columns[0]:"sample_id"})
    return df.set_index("sample_id")

def ensure_dir(p): Path(p).mkdir(parents=True,exist_ok=True); return Path(p)

def run_pca(X,n):
    pca=PCA(n_components=n)
    comps=pca.fit_transform(X)
    return pd.DataFrame(comps,columns=[f"PC{i+1}" for i in range(n)],index=X.index), pca.explained_variance_ratio_

def run_kmeans(X,k,seed):
    km=KMeans(n_clusters=k,random_state=seed,n_init=10)
    return pd.DataFrame({"sample_id":X.index,"cluster":km.fit_predict(X)}).set_index("sample_id")

def run_rf_importance(X,seed):
    # unsupervised proxy: fit RF to predict first PC
    pca_comp,_=run_pca(X,1)
    y=pca_comp.iloc[:,0]
    rf=RandomForestRegressor(random_state=seed,n_estimators=100)
    rf.fit(X,y)
    return pd.DataFrame({"feature":X.columns,"importance":rf.feature_importances_}).sort_values("importance",ascending=False)

def main():
    req=load_yaml(DEFAULT_REQUEST)
    inp=req["inputs"]; pol=req["modeling_policy"]
    X=read_matrix(inp["model_input_matrix"])
    out=ensure_dir(req["expected_outputs"]["ai_modeling_execution_dir"])
    # PCA
    pca_df,var=run_pca(X,pol.get("n_pca_components",5))
    pca_path=out/"pca_coordinates.tsv"
    pca_df.to_csv(pca_path,sep='\t')
    # KMeans
    km_df=run_kmeans(X,pol.get("kmeans_clusters",3),pol.get("random_seed",123))
    km_path=out/"kmeans_clusters.tsv"
    km_df.to_csv(km_path,sep='\t')
    # RF importance
    fi_df=run_rf_importance(X,pol.get("random_seed",123))
    fi_path=out/"feature_importance.tsv"
    fi_df.to_csv(fi_path,sep='\t',index=False)
    # summary
    summary={"samples":int(X.shape[0]),"features":int(X.shape[1])}
    yaml.safe_dump(summary,open(out/"modeling_summary.yaml","w"))
    print("AI modeling execution complete.")
    print(f"Samples: {summary['samples']}")
    print(f"Features: {summary['features']}")
    print(f"Outputs: {out}")

if __name__=='__main__': main()

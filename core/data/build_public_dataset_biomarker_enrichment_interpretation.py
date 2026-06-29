from __future__ import annotations
import argparse, json, math, re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_CONFIG = Path("configs/public_data_sources/public_dataset_biomarker_enrichment_interpretation_request.json")
ENSEMBL_RE = re.compile(r"(ENSG\d{11})", re.IGNORECASE)
ID_CANDIDATES = ["gene_id", "ensembl_gene_id", "ensembl_id", "feature", "feature_id", "id"]
SYMBOL_CANDIDATES = ["gene_name", "gene_symbol", "symbol", "external_gene_name", "hgnc_symbol", "name"]
GENE_SETS: Dict[str, List[str]] = {
    "BRCA_luminal_hormone_axis": ["ESR1", "PGR", "GATA3", "FOXA1", "XBP1", "BCL2", "TFF1", "TFF3", "AGR2", "KRT8", "KRT18", "KRT19"],
    "BRCA_HER2_ERBB_signaling": ["ERBB2", "ERBB3", "GRB7", "EGFR", "MET", "KRAS", "MAPK1", "MAPK3", "PIK3CA", "AKT1", "MTOR"],
    "BRCA_basal_epithelial": ["KRT5", "KRT6A", "KRT6B", "KRT14", "KRT17", "EGFR", "LAMC2", "CAV1", "CAV2"],
    "proliferation_cell_cycle": ["MKI67", "TOP2A", "CDK1", "CCNB1", "CCNB2", "CDC20", "AURKA", "AURKB", "BUB1", "BUB1B", "PCNA", "MCM2", "MCM3", "MCM4", "MCM5", "MCM6", "MCM7"],
    "immune_interferon_cytotoxicity": ["CD3D", "CD3E", "CD4", "CD8A", "CD8B", "PTPRC", "CXCL9", "CXCL10", "CXCL11", "CCL2", "CCL3", "CCL4", "CCL5", "NKG7", "GZMB", "PRF1", "IFNG", "STAT1"],
    "myeloid_macrophage_inflammation": ["LST1", "AIF1", "CD68", "CSF1R", "ITGAM", "TYROBP", "FCGR3A", "C1QA", "C1QB", "C1QC", "IL1B", "TNF"],
    "extracellular_matrix_invasion": ["COL1A1", "COL1A2", "COL3A1", "COL5A1", "COL5A2", "FN1", "VIM", "MMP2", "MMP9", "MMP11", "SPARC", "POSTN", "ITGA5", "ITGB1"],
    "dna_damage_repair_p53": ["BRCA1", "BRCA2", "RAD51", "RAD50", "ATM", "ATR", "CHEK1", "CHEK2", "PARP1", "TP53", "FANCA", "FANCD2"],
    "hypoxia_glycolysis": ["HIF1A", "VEGFA", "SLC2A1", "LDHA", "ENO1", "PGK1", "ALDOA", "HK2", "CA9", "BNIP3"],
    "emt_stemness": ["VIM", "ZEB1", "ZEB2", "SNAI1", "SNAI2", "TWIST1", "CDH2", "ITGA6", "PROM1", "ALDH1A1", "SOX2"],
}
COMMON_ENSEMBL_SYMBOL_FALLBACK = {"ENSG00000141510":"TP53","ENSG00000012048":"BRCA1","ENSG00000139618":"BRCA2","ENSG00000141736":"ERBB2","ENSG00000091831":"ESR1","ENSG00000082175":"PGR","ENSG00000107485":"GATA3","ENSG00000129514":"FOXA1","ENSG00000121879":"PIK3CA","ENSG00000142208":"AKT1","ENSG00000170312":"CDK1","ENSG00000148773":"MKI67","ENSG00000131747":"TOP2A","ENSG00000134057":"CCNB1","ENSG00000146648":"EGFR","ENSG00000133703":"KRAS","ENSG00000198793":"MTOR","ENSG00000171862":"PTEN"}

def norm_col(x): return re.sub(r"[^a-z0-9]+", "_", str(x).strip().lower()).strip("_")
def load_config(path: Path) -> dict: return json.loads(path.read_text(encoding="utf-8"))
def feature_key(v):
    s=str(v).strip(); m=ENSEMBL_RE.search(s)
    if m: return m.group(1).upper()
    if "|" in s: s=s.split("|")[-1]
    if ":" in s: s=s.split(":")[-1]
    return re.sub(r"\.\d+$", "", s).upper()
def find_col(df, candidates, default=None):
    lookup={norm_col(c):c for c in df.columns}
    for c in candidates:
        if norm_col(c) in lookup: return str(lookup[norm_col(c)])
    return default

def detect_header_row(path: Path, scan_lines: int = 200) -> Optional[int]:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i >= scan_lines: break
                cols=[norm_col(c) for c in line.rstrip("\n\r").split("\t")]
                if any(c in cols for c in ["gene_id","ensembl_gene_id","ensembl_id"]) and any(c in cols for c in ["gene_name","gene_symbol","external_gene_name","hgnc_symbol"]):
                    return i
    except Exception:
        return None
    return None

def read_table(path: Path, nrows: Optional[int]=None, header_row: Optional[int]=None) -> pd.DataFrame:
    sep = "," if path.suffix.lower()==".csv" else "\t"
    if header_row is None and sep == "\t":
        header_row = detect_header_row(path)
    return pd.read_csv(path, sep=sep, nrows=nrows, skiprows=header_row if header_row is not None else None, comment="#")

def candidate_annotation_files(roots):
    out=[]; seen=set()
    for raw in roots:
        r=Path(raw)
        cands=[]
        if r.is_file(): cands=[r]
        elif r.is_dir():
            for pat in ["*.tsv","*.txt","*.csv"]: cands += list(r.rglob(pat))
        for p in cands:
            k=str(p.resolve()).lower()
            if k not in seen:
                seen.add(k); out.append(p)
    return out

def recover_annotation_from_sources(config):
    rows=[]; maps=[]; scan=int(config.get("parameters",{}).get("star_header_scan_lines",200))
    for path in candidate_annotation_files(config["inputs"].get("annotation_source_roots", [])):
        header_row = detect_header_row(path, scan) if path.suffix.lower() != ".csv" else None
        row={"source_path":str(path),"readable":False,"header_row_detected":"" if header_row is None else header_row,"columns":"","id_column":"","symbol_column":"","rows_scanned":0,"mappings_recovered":0,"status":"not_scanned"}
        try:
            prev=read_table(path, nrows=20, header_row=header_row)
            row["readable"]=True; row["columns"]=";".join(map(str, prev.columns.tolist()[:50]))
            idc=find_col(prev, ID_CANDIDATES); sym=find_col(prev, SYMBOL_CANDIDATES)
            row["id_column"]=idc or ""; row["symbol_column"]=sym or ""
            if not idc: row["status"]="no_gene_id_like_column"
            elif not sym: row["status"]="no_gene_symbol_like_column"
            elif idc==sym: row["status"]="id_symbol_same_column"
            else:
                full=read_table(path, header_row=header_row)
                sub=full[[idc,sym]].dropna().copy(); row["rows_scanned"]=len(sub)
                sub["gene_id"]=sub[idc].apply(feature_key); sub["gene_name"]=sub[sym].astype(str).str.strip().str.upper()
                sub=sub[(sub.gene_id.str.len()>0)&(sub.gene_name.str.len()>0)]
                sub=sub[~sub.gene_name.str.match(r"^ENSG\d{11}$", na=False)]
                sub=sub[["gene_id","gene_name"]].drop_duplicates()
                row["mappings_recovered"]=len(sub); row["status"]="used_for_recovery" if len(sub) else "no_valid_mappings_recovered"
                if len(sub): maps.append(sub)
        except Exception as e:
            row["status"]="read_error"; row["error"]=str(e)
        rows.append(row)
    rec=pd.concat(maps, ignore_index=True).drop_duplicates("gene_id", keep="first") if maps else pd.DataFrame(columns=["gene_id","gene_name"])
    return rec, pd.DataFrame(rows)

def write_recovered_annotation(config, outputs):
    rec, diag = recover_annotation_from_sources(config)
    Path(outputs["recovered_gene_annotation"]).parent.mkdir(parents=True, exist_ok=True)
    rec.to_csv(outputs["recovered_gene_annotation"], sep="\t", index=False)
    diag.to_csv(outputs["annotation_recovery_diagnostics"], sep="\t", index=False)
    primary=Path(config["inputs"].get("primary_annotation_output", ""))
    if len(rec) and str(primary):
        primary.parent.mkdir(parents=True, exist_ok=True); rec.to_csv(primary, sep="\t", index=False)
    return rec, diag

def scan_annotation_sources(paths):
    mapping={}; rows=[]
    for raw in paths:
        p=Path(raw); row={"path":str(p),"exists":p.exists(),"readable":False,"rows_previewed":0,"columns":"","id_column":"","symbol_column":"","mappings_added":0,"status":"missing"}
        if not p.is_file(): rows.append(row); continue
        try:
            prev=read_table(p, nrows=5); row["readable"]=True; row["rows_previewed"]=len(prev); row["columns"]=";".join(map(str, prev.columns.tolist()[:30]))
            idc=find_col(prev, ID_CANDIDATES); sym=find_col(prev, SYMBOL_CANDIDATES); row["id_column"]=idc or ""; row["symbol_column"]=sym or ""
            if not idc: row["status"]="no_gene_id_like_column"
            elif not sym: row["status"]="no_gene_symbol_like_column"
            elif idc==sym: row["status"]="id_and_symbol_column_same"
            else:
                full=read_table(p); before=len(mapping)
                for _,r in full[[idc,sym]].dropna().iterrows():
                    k=feature_key(r[idc]); s=str(r[sym]).strip().upper()
                    if k and s and not ENSEMBL_RE.fullmatch(s): mapping[k]=s
                row["mappings_added"]=len(mapping)-before; row["status"]="used" if row["mappings_added"] else "no_valid_mappings_added"
        except Exception as e:
            row["status"]="read_error"; row["error"]=str(e)
        rows.append(row)
    fb=0
    for k,v in COMMON_ENSEMBL_SYMBOL_FALLBACK.items():
        if k not in mapping: mapping[k]=v; fb+=1
    rows.append({"path":"COMMON_ENSEMBL_SYMBOL_FALLBACK","exists":True,"readable":True,"rows_previewed":len(COMMON_ENSEMBL_SYMBOL_FALLBACK),"columns":"ensembl_id;gene_symbol","id_column":"ensembl_id","symbol_column":"gene_symbol","mappings_added":fb,"status":"used_fallback"})
    return mapping, pd.DataFrame(rows)

def infer_feature_and_importance_cols(df):
    fc=find_col(df,["feature","feature_id","gene","gene_id","gene_name","symbol"],str(df.columns[0])); ic=find_col(df,["importance","feature_importance","score","gini_importance","mean_decrease_impurity"])
    if ic is None:
        nums=[str(c) for c in df.columns if pd.to_numeric(df[c], errors="coerce").notna().sum()>0]
        if not nums: raise ValueError("Could not infer numeric feature-importance column")
        ic=nums[-1]
    return fc,ic

def resolve_feature_importance(feature_path, annotation_map, top_n):
    df=read_table(feature_path); fc,ic=infer_feature_and_importance_cols(df); df[ic]=pd.to_numeric(df[ic], errors="coerce")
    df=df.dropna(subset=[ic]).sort_values(ic, ascending=False).reset_index(drop=True); df["rank"]=range(1,len(df)+1); df["feature_key"]=df[fc].apply(feature_key)
    df["resolved_gene_symbol"]=df["feature_key"].map(annotation_map).fillna(""); df["resolved"]=df.resolved_gene_symbol.astype(str).str.len()>0; df["interpretation_label"]=df.resolved_gene_symbol.where(df.resolved, df.feature_key)
    top=df.head(top_n).copy(); unresolved=top[~top.resolved].copy()
    return top, unresolved, {"feature_column":fc,"importance_column":ic,"feature_rows":len(df),"top_n_evaluated":len(top),"resolved_top_n":int(top.resolved.sum()),"unresolved_top_n":int((~top.resolved).sum()),"resolved_fraction_top_n":float(top.resolved.mean()) if len(top) else 0.0}

def hypergeom_sf_at_least(k,pop,succ,draws):
    if pop<=0 or k<=0 or draws<=0: return 1.0
    denom=math.comb(pop,draws); total=0
    for i in range(k, min(succ,draws)+1):
        if draws-i <= pop-succ: total += math.comb(succ,i)*math.comb(pop-succ,draws-i)
    return min(1.0,max(0.0,total/denom)) if denom else 1.0

def bh_adjust(pvalues):
    m=len(pvalues); idx=sorted(enumerate(pvalues), key=lambda x:x[1]); adj=[1.0]*m; run=1.0
    for rfe,(i,p) in enumerate(reversed(idx), start=1):
        rank=m-rfe+1; run=min(run,p*m/rank); adj[i]=min(1.0,run)
    return adj

def build_gene_set_enrichment(top):
    q=set(g for g in top.loc[top.resolved,"resolved_gene_symbol"].astype(str).str.upper() if g); bg=set(q)
    for vals in GENE_SETS.values(): bg.update(vals)
    rows=[]
    for name, vals in GENE_SETS.items():
        gs=set(g.upper() for g in vals); matched=sorted(q.intersection(gs)); p=hypergeom_sf_at_least(len(matched), len(bg), len(gs.intersection(bg)), len(q))
        rows.append({"gene_set":name,"matched_gene_count":len(matched),"query_gene_count":len(q),"gene_set_size":len(gs),"matched_genes":";".join(matched),"p_value":p,"enrichment_score_simple":(len(matched)/max(1,len(gs)))*(len(matched)/max(1,len(q))) if q else 0.0})
    out=pd.DataFrame(rows); out["q_value_bh"]=bh_adjust(out.p_value.astype(float).tolist()) if len(out) else []
    return out.sort_values(["matched_gene_count","q_value_bh","gene_set"], ascending=[False,True,True])

def make_enrichment_plot(enrichment,path,dpi):
    path=Path(path); path.parent.mkdir(parents=True, exist_ok=True); plot=enrichment.sort_values(["matched_gene_count","gene_set"], ascending=[True,True])
    fig,ax=plt.subplots(figsize=(9,max(5,0.42*len(plot)+1.5))); ax.barh(plot.gene_set, plot.matched_gene_count); ax.set_title("Recovered GDC STAR Annotation Gene-Set Matches"); ax.set_xlabel("Matched resolved top-feature genes"); ax.set_ylabel("Gene set"); fig.tight_layout(); fig.savefig(path,dpi=dpi); plt.close(fig)

def find_existing_path(cands):
    for c in cands:
        p=Path(c)
        if p.is_file(): return p
    return None

def build_cluster_feature_signal(config, top, output_path, top_n):
    p=find_existing_path(config["inputs"].get("model_input_matrix_candidates", [])); cp=Path(config["inputs"].get("kmeans_clusters", "")); output_path=Path(output_path); output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"status":"skipped_missing_model_matrix_or_clusters","model_matrix_path":str(p) if p else "","cluster_path":str(cp)}]).to_csv(output_path, sep="\t", index=False)
    return {"cluster_feature_signal_status":"skipped_missing_model_matrix_or_clusters","model_matrix_path":str(p) if p else ""}

def build_clinical_bridge(config, output_path):
    rows=[]
    for raw in config["inputs"].get("clinical_metadata_candidates", []):
        p=Path(raw)
        if p.is_file():
            df=read_table(p,nrows=5); rows.append({"path":str(p),"status":"available","rows_previewed":len(df),"columns_preview":";".join(map(str,df.columns.tolist()[:20]))})
    if not rows: rows=[{"path":"","status":"not_available_yet","rows_previewed":"","columns_preview":"","note":"Clinical/subtype metadata not found."}]
    Path(output_path).parent.mkdir(parents=True, exist_ok=True); pd.DataFrame(rows).to_csv(output_path, sep="\t", index=False)
    return {"clinical_bridge_status":rows[0]["status"],"clinical_candidate_files_detected":sum(1 for r in rows if r["status"]=="available")}

def write_report(config, summary, top, enrichment, report_path):
    imp=summary["feature_importance"]["importance_column"]; top_lines=[]
    for _,r in top.head(int(config["parameters"].get("top_n_report_features",40))).iterrows():
        lab=r.resolved_gene_symbol if r.resolved else r.feature_key; stat="resolved" if r.resolved else "unresolved"; top_lines.append(f"- rank {int(r['rank'])}: `{lab}` ({stat}), importance={float(r[imp]):.6g}")
    enr=[f"- **{r.gene_set}**: {r.matched_gene_count} matches; q={float(r.q_value_bh):.4g}; genes={r.matched_genes if str(r.matched_genes).strip() else 'none'}" for _,r in enrichment.iterrows()]
    gate=summary["quality_gate"]
    text=f"""# OpenMultiOmics-Cancer-Atlas v0.4.0-a42-fix3 GDC STAR Header Recovery Report

## Purpose

This fix reads GDC STAR-count files that may contain preamble or metadata before the actual `gene_id/gene_name` header. It scans file lines for the real header, recovers `gene_id -> gene_name`, then reruns biomarker enrichment.

## Recovery Summary

- Recovered annotation rows: {summary['annotation_recovery']['recovered_annotation_rows']}
- Recovery sources used: {summary['annotation_recovery']['sources_used_for_recovery']}
- Annotation mapping size: {summary['annotation']['annotation_mapping_size']}

## Quality Gate

- Ready for biomarker review: `{summary['ready_for_biomarker_review']}`
- Resolved fraction: {summary['feature_importance']['resolved_fraction_top_n']:.3f}
- Gene sets with matches: {summary['gene_set_enrichment']['gene_sets_with_matches']}
- Blocking reasons: {', '.join(gate['blocking_reasons']) if gate['blocking_reasons'] else 'none'}

## Gene-Set Enrichment

{chr(10).join(enr)}

## Top Ranked Features

{chr(10).join(top_lines)}

Generated at: `{summary['generated_at_utc']}`
"""
    Path(report_path).parent.mkdir(parents=True, exist_ok=True); Path(report_path).write_text(text, encoding="utf-8")

def run(config_path: Path):
    config=load_config(config_path); outputs=config["outputs"]; params=config["parameters"]; Path(outputs["interpretation_dir"]).mkdir(parents=True, exist_ok=True)
    fp=Path(config["inputs"]["feature_importance"])
    if not fp.exists(): raise FileNotFoundError(f"Missing feature importance file: {fp}")
    rec, recdiag = write_recovered_annotation(config, outputs)
    amap, resdiag = scan_annotation_sources(config["inputs"].get("gene_annotation_candidates", [])); resdiag.to_csv(outputs["annotation_resolution_diagnostics"], sep="\t", index=False)
    top, unresolved, fis = resolve_feature_importance(fp, amap, int(params.get("top_n_features",250))); top.to_csv(outputs["resolved_feature_importance"], sep="\t", index=False); unresolved.to_csv(outputs["unresolved_features"], sep="\t", index=False)
    enr=build_gene_set_enrichment(top); enr.to_csv(outputs["gene_set_enrichment"], sep="\t", index=False); make_enrichment_plot(enr, outputs["gene_set_enrichment_png"], int(params.get("figure_dpi",160)))
    cluster=build_cluster_feature_signal(config, top, outputs["cluster_feature_signal"], int(params.get("cluster_top_n_features",30))); clinical=build_clinical_bridge(config, outputs["clinical_bridge_status"])
    minf=float(params.get("minimum_resolved_fraction_for_biomarker_review",0.25)); mins=int(params.get("minimum_gene_sets_with_matches_for_biomarker_review",1)); sets=int((enr.matched_gene_count>0).sum())
    blocking=[]
    if fis["resolved_fraction_top_n"] < minf: blocking.append("insufficient_ensembl_to_symbol_resolution")
    if sets < mins: blocking.append("no_curated_gene_set_matches")
    ready=not blocking; used=recdiag[recdiag.status=="used_for_recovery"].source_path.astype(str).tolist() if len(recdiag) else []
    summary={"version":config["version"],"bundle_name":config["bundle_name"],"project":config["project"],"generated_at_utc":datetime.now(timezone.utc).replace(microsecond=0).isoformat(),"upstream_version":config["upstream_version"],"upstream_commit":config["upstream_commit"],"annotation_recovery":{"recovered_annotation_rows":int(len(rec)),"sources_scanned":int(len(recdiag)),"sources_used_for_recovery":used},"annotation":{"annotation_mapping_size":int(len(amap)),"diagnostic_rows":int(len(resdiag)),"used_annotation_sources":resdiag[resdiag.status.astype(str).str.contains("used", na=False)].path.astype(str).tolist()},"feature_importance":fis,"gene_set_enrichment":{"gene_sets_evaluated":int(len(enr)),"gene_sets_with_matches":sets},"cluster_feature_signal":cluster,"clinical_bridge":clinical,"quality_gate":{"minimum_resolved_fraction_for_biomarker_review":minf,"minimum_gene_sets_with_matches_for_biomarker_review":mins,"blocking_reasons":blocking},"ready_for_biomarker_review":ready,"ready_for_annotation_recovery":not ready,"outputs":outputs}
    Path(outputs["summary_json"]).write_text(json.dumps(summary, indent=2), encoding="utf-8"); write_report(config, summary, top, enr, outputs["interpretation_report"]); return summary

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--config", default=str(DEFAULT_CONFIG)); args=ap.parse_args(); s=run(Path(args.config))
    print("v0.4.0-a42-fix3 GDC STAR header recovery completed."); print("Output directory:", s["outputs"]["interpretation_dir"]); print("Recovered annotation rows:", s["annotation_recovery"]["recovered_annotation_rows"]); print("Resolved top features:", s["feature_importance"]["resolved_top_n"]); print("Resolved fraction:", s["feature_importance"]["resolved_fraction_top_n"]); print("Gene sets with matches:", s["gene_set_enrichment"]["gene_sets_with_matches"]); print("Ready for biomarker review:", s["ready_for_biomarker_review"]); print("Blocking reasons:", ", ".join(s["quality_gate"]["blocking_reasons"]) if s["quality_gate"]["blocking_reasons"] else "none")
if __name__ == "__main__": main()

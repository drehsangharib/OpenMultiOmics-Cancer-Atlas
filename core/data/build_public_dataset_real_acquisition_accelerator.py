#!/usr/bin/env python3
import argparse, html, sys
from pathlib import Path
import pandas as pd
import yaml

DEFAULT_ACCELERATOR_REQUEST = Path("configs/public_data_sources/public_dataset_real_acquisition_accelerator_request.yaml")

def safe_str(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    return str(value)

def safe_int(value, default=0):
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except TypeError:
        pass
    try:
        return int(value)
    except Exception:
        return default

def load_yaml_mapping(path):
    path=Path(path)
    if not path.exists():
        raise FileNotFoundError(f"YAML file not found: {path}")
    with path.open("r",encoding="utf-8") as f:
        data=yaml.safe_load(f) or {}
    if not isinstance(data,dict):
        raise ValueError(f"YAML file must contain a mapping: {path}")
    return data

def write_yaml(path,data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8") as f:
        yaml.safe_dump(data,f,sort_keys=False)

def read_table(path):
    """Read an optional TSV/CSV table safely.

    Optional request inputs may be absent, None, or empty strings. On Windows,
    Path("") resolves to Path("."), so guard before Path conversion and reject
    directory paths to avoid PermissionError during tests or optional artifact use.
    """
    if path is None:
        return pd.DataFrame()
    raw_path=safe_str(path).strip()
    if not raw_path:
        return pd.DataFrame()
    path=Path(raw_path)
    if str(path)=="." or not path.exists() or path.is_dir():
        return pd.DataFrame()
    if path.suffix.lower()==".csv":
        return pd.read_csv(path)
    return pd.read_csv(path,sep="\t")

def ensure_dir(path):
    p=Path(path); p.mkdir(parents=True,exist_ok=True); return p

def escape_html(value):
    return html.escape("" if value is None else str(value))

def df_html(df,max_rows=300):
    if df.empty: return "<p>No records available.</p>"
    out=df.head(max_rows).copy(); lines=["<table border='1' cellspacing='0' cellpadding='5'>","<thead><tr>"]
    for c in out.columns: lines.append(f"<th>{escape_html(c)}</th>")
    lines.append("</tr></thead><tbody>")
    for _,r in out.iterrows():
        lines.append("<tr>")
        for c in out.columns: lines.append(f"<td>{escape_html(r[c])}</td>")
        lines.append("</tr>")
    lines.append("</tbody></table>"); return "\n".join(lines)

def require_columns(df, cols, name):
    missing=set(cols)-set(df.columns)
    if missing: raise ValueError(f"{name} missing columns: "+", ".join(sorted(missing)))

def merge_optional(base, inv, portal, intake, schema):
    df=base.copy()
    if not inv.empty and "dataset_id" in inv.columns:
        df=df.merge(inv[[c for c in ["dataset_id","source_packet_yaml","source_packet_yaml_exists"] if c in inv.columns]],on="dataset_id",how="left")
    if not portal.empty and "dataset_id" in portal.columns and "portal_url" not in df.columns:
        df=df.merge(portal[[c for c in ["dataset_id","portal_url"] if c in portal.columns]],on="dataset_id",how="left")
    if not intake.empty and "dataset_id" in intake.columns:
        df=df.merge(intake[[c for c in ["dataset_id","intake_status","candidate_file_count","dropzone_dir"] if c in intake.columns]],on="dataset_id",how="left")
    if not schema.empty and "dataset_id" in schema.columns:
        df=df.merge(schema[[c for c in ["dataset_id","schema_validation_status","schema_candidate_file"] if c in schema.columns]],on="dataset_id",how="left")
    return df

def build_master_plan(source_packets_df, packet_inventory_df, portal_links_df, intake_df, schema_df):
    require_columns(source_packets_df,{"dataset_id","display_name","source_id","accession_or_project_id","atlas_hint","modality","expected_file_type","replacement_priority","target_local_path","portal_url","command_template","operator_next_step"},"source_access_packets")
    df=merge_optional(source_packets_df,packet_inventory_df,portal_links_df,intake_df,schema_df)
    for c in ["source_packet_yaml","source_packet_yaml_exists","intake_status","candidate_file_count","dropzone_dir","schema_validation_status","schema_candidate_file"]:
        if c not in df.columns: df[c]=""
    df["requires_accession_resolution"]=df["accession_or_project_id"].astype(str).str.startswith("REPLACE_WITH").astype(int)
    df["target_file_present"]=df["target_local_path"].apply(lambda p:int(Path(safe_str(p)).exists()) if safe_str(p) else 0)
    df["ready_to_acquire"]=((df["requires_accession_resolution"]==0)&(df["target_file_present"]==0)).astype(int)
    df["acquisition_blocker"]=df.apply(lambda r:"placeholder_accession_requires_resolution" if safe_int(r["requires_accession_resolution"]) else ("target_file_already_present" if safe_int(r["target_file_present"]) else "none"),axis=1)
    df["post_acquisition_rerun_sequence"]="a23_readiness -> a24_execution_scaffold -> a25_file_validation -> a30_intake -> a31_modality_schema -> a32_source_packets"
    keep=["dataset_id","display_name","source_id","accession_or_project_id","atlas_hint","modality","expected_file_type","replacement_priority","target_local_path","portal_url","source_packet_yaml","dropzone_dir","command_template","requires_accession_resolution","ready_to_acquire","target_file_present","candidate_file_count","intake_status","schema_validation_status","schema_candidate_file","acquisition_blocker","operator_next_step","post_acquisition_rerun_sequence"]
    for c in keep:
        if c not in df.columns: df[c]=""
    return df.loc[:,keep].sort_values("replacement_priority").reset_index(drop=True)

def build_priority_queue(master):
    df=master[master["target_file_present"].apply(safe_int)==0].copy()
    df["queue_status"]=df.apply(lambda r:"blocked_accession_resolution" if safe_int(r["requires_accession_resolution"]) else "ready_to_acquire",axis=1)
    return df.sort_values(["queue_status","replacement_priority"]).reset_index(drop=True)

def build_accession_resolution(master):
    cols=["dataset_id","display_name","source_id","accession_or_project_id","modality","portal_url","operator_next_step"]
    df=master[master["requires_accession_resolution"].apply(safe_int)==1].copy()
    return df.loc[:,cols].reset_index(drop=True) if not df.empty else pd.DataFrame(columns=cols)

def build_target_path_plan(master):
    return master.loc[:,["dataset_id","source_id","modality","target_local_path","dropzone_dir","target_file_present","ready_to_acquire","acquisition_blocker"]].copy()

def validation_rerun_plan():
    return "\n".join(["# v0.4.0-a33 post-acquisition validation rerun plan","python -m core.data.validate_public_dataset_replacement_readiness","python -m core.data.build_public_dataset_replacement_execution_scaffold","python -m core.data.validate_public_dataset_replacement_files","python -m core.data.build_public_dataset_real_file_intake_bundle","python -m core.data.validate_public_dataset_modality_schemas","python -m core.data.build_public_dataset_source_access_packet","python -m core.data.build_public_dataset_real_acquisition_accelerator",""])

def operator_workbook(master,priority,accession):
    lines=["# Public Dataset Real Acquisition Operator Workbook","","## Priority queue",""]
    for _,r in priority.iterrows():
        lines += [f"### {safe_str(r.get('dataset_id'))}","",f"- source: `{safe_str(r.get('source_id'))}`",f"- accession/project: `{safe_str(r.get('accession_or_project_id'))}`",f"- modality: `{safe_str(r.get('modality'))}`",f"- queue_status: `{safe_str(r.get('queue_status'))}`",f"- portal_url: {safe_str(r.get('portal_url'))}",f"- target_local_path: `{safe_str(r.get('target_local_path'))}`",f"- source_packet_yaml: `{safe_str(r.get('source_packet_yaml'))}`",f"- next_step: {safe_str(r.get('operator_next_step'))}",""]
    lines += ["## Accession-resolution queue",""]
    if accession.empty: lines.append("No placeholder accessions currently require resolution.\n")
    else:
        for _,r in accession.iterrows(): lines += [f"- `{safe_str(r.get('dataset_id'))}` requires accession resolution before acquisition.",f"  - current accession value: `{safe_str(r.get('accession_or_project_id'))}`",""]
    lines += ["## After file placement","","```powershell",validation_rerun_plan().strip(),"```",""]
    return "\n".join(lines)

def html_report(request,master,priority,accession,summary):
    title="Public Dataset Real Acquisition Accelerator Report"
    return "\n".join(["<!DOCTYPE html>","<html>","<head>","<meta charset='utf-8'>",f"<title>{escape_html(title)}</title>","</head>","<body>",f"<h1>{escape_html(title)}</h1>","<p>This report consolidates source access packets into a master real-acquisition plan.</p>",f"<p><strong>Dataset count:</strong> {summary.get('dataset_count',0)}</p>",f"<p><strong>Ready to acquire:</strong> {summary.get('ready_to_acquire_count',0)}</p>",f"<p><strong>Requires accession resolution:</strong> {summary.get('requires_accession_resolution_count',0)}</p>",f"<p><strong>Target files present:</strong> {summary.get('target_file_present_count',0)}</p>","<h2>Master plan</h2>",df_html(master),"<h2>Priority queue</h2>",df_html(priority),"<h2>Accession-resolution queue</h2>",df_html(accession),"</body>","</html>"])

def build_public_dataset_real_acquisition_accelerator(request_path=DEFAULT_ACCELERATOR_REQUEST, output_dir=None):
    request=load_yaml_mapping(request_path); inputs=request.get("inputs",{}) or {}
    packet_path=inputs.get("source_access_packets"); packet_summary_path=inputs.get("source_access_summary")
    if not packet_path: raise ValueError("Accelerator request missing inputs.source_access_packets")
    if not packet_summary_path: raise ValueError("Accelerator request missing inputs.source_access_summary")
    packet_df=read_table(packet_path); packet_summary=load_yaml_mapping(packet_summary_path)
    inv=read_table(inputs.get("source_packet_yaml_inventory","")); portal=read_table(inputs.get("source_portal_links","")); intake=read_table(inputs.get("real_file_intake_inventory","")); schema=read_table(inputs.get("modality_schema_validation_table",""))
    out=ensure_dir(output_dir or (request.get("expected_outputs",{}) or {}).get("real_acquisition_accelerator_dir", Path("outputs/public_data_acquisition")/request.get("atlas_name","public_data_pilot")/"real_acquisition_accelerator"))
    master=build_master_plan(packet_df,inv,portal,intake,schema); priority=build_priority_queue(master); accession=build_accession_resolution(master); target=build_target_path_plan(master)
    paths={"master_plan":out/"public_dataset_real_acquisition_master_plan.tsv","priority_queue":out/"public_dataset_real_acquisition_priority_queue.tsv","accession_resolution":out/"public_dataset_real_acquisition_accession_resolution.tsv","target_path_plan":out/"public_dataset_real_acquisition_target_path_plan.tsv","validation_rerun_plan":out/"public_dataset_real_acquisition_validation_rerun_plan.ps1","operator_workbook":out/"public_dataset_real_acquisition_operator_workbook.md","summary":out/"public_dataset_real_acquisition_summary.yaml","report":out/"public_dataset_real_acquisition_report.html"}
    master.to_csv(paths["master_plan"],sep="\t",index=False); priority.to_csv(paths["priority_queue"],sep="\t",index=False); accession.to_csv(paths["accession_resolution"],sep="\t",index=False); target.to_csv(paths["target_path_plan"],sep="\t",index=False)
    paths["validation_rerun_plan"].write_text(validation_rerun_plan(),encoding="utf-8"); paths["operator_workbook"].write_text(operator_workbook(master,priority,accession),encoding="utf-8")
    summary={"request_id":str(request.get("request_id","")),"atlas_name":str(request.get("atlas_name","")),"upstream_source_access_request_id":str(packet_summary.get("request_id","")),"upstream_source_access_output_dir":str(packet_summary.get("output_dir","")),"dataset_count":int(master.shape[0]),"ready_to_acquire_count":int(master["ready_to_acquire"].sum()) if not master.empty else 0,"requires_accession_resolution_count":int(master["requires_accession_resolution"].sum()) if not master.empty else 0,"target_file_present_count":int(master["target_file_present"].sum()) if not master.empty else 0,"post_acquisition_validation_plan_count":int(master.shape[0]),"source_count":int(master["source_id"].nunique()) if not master.empty else 0,"modality_count":int(master["modality"].nunique()) if not master.empty else 0,"output_dir":str(out),"outputs":{k:str(p) for k,p in paths.items()},"agent_role":{"stage":"public_dataset_real_acquisition_accelerator_bundle","purpose":"consolidate public-data source access into an operator-ready acquisition plan"}}
    write_yaml(paths["summary"],summary); paths["report"].write_text(html_report(request,master,priority,accession,summary),encoding="utf-8")
    return summary, master, priority, accession, target, paths

def build_arg_parser():
    p=argparse.ArgumentParser(description="Build public dataset real acquisition accelerator bundle."); p.add_argument("--request",type=Path,default=DEFAULT_ACCELERATOR_REQUEST); p.add_argument("--output-dir",type=Path,default=None); return p

def main(argv=None):
    a=build_arg_parser().parse_args(argv)
    try:
        s,master,priority,accession,target,paths=build_public_dataset_real_acquisition_accelerator(request_path=a.request,output_dir=a.output_dir)
    except Exception as exc:
        print(f"ERROR: Public dataset real acquisition accelerator build failed: {exc}",file=sys.stderr); return 1
    print("Public dataset real acquisition accelerator complete."); print(f"Atlas: {s['atlas_name']}"); print(f"Datasets: {s['dataset_count']}"); print(f"Ready to acquire: {s['ready_to_acquire_count']}"); print(f"Requires accession resolution: {s['requires_accession_resolution_count']}"); print(f"Target files present: {s['target_file_present_count']}"); print(f"Report: {paths['report']}"); return 0

if __name__=="__main__":
    raise SystemExit(main())

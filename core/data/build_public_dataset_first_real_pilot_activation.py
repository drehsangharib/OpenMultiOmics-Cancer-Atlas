#!/usr/bin/env python3
import argparse, html, sys
from pathlib import Path
import pandas as pd
import yaml

DEFAULT_REQUEST = Path("configs/public_data_sources/public_dataset_first_real_pilot_request.yaml")


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
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"YAML file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML file must contain a mapping: {path}")
    return data


def write_yaml(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)


def read_table(path):
    if path is None:
        return pd.DataFrame()
    raw = safe_str(path).strip()
    if not raw:
        return pd.DataFrame()
    path = Path(raw)
    if str(path) == "." or not path.exists() or path.is_dir():
        return pd.DataFrame()
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_csv(path, sep="\t")


def ensure_dir(path):
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def escape_html(value):
    return html.escape("" if value is None else str(value))


def dataframe_to_html_table(df, max_rows=300):
    if df.empty:
        return "<p>No records available.</p>"
    out = df.head(max_rows).copy()
    lines = ["<table border='1' cellspacing='0' cellpadding='5'>", "<thead><tr>"]
    for col in out.columns:
        lines.append(f"<th>{escape_html(col)}</th>")
    lines.append("</tr></thead><tbody>")
    for _, row in out.iterrows():
        lines.append("<tr>")
        for col in out.columns:
            lines.append(f"<td>{escape_html(row[col])}</td>")
        lines.append("</tr>")
    lines.append("</tbody></table>")
    return "\n".join(lines)


def require_columns(df, required, name):
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"{name} missing columns: " + ", ".join(sorted(missing)))


def select_first_pilot(master_df, priority_df, policy):
    required = {
        "dataset_id", "display_name", "source_id", "accession_or_project_id", "atlas_hint", "modality",
        "expected_file_type", "replacement_priority", "target_local_path", "portal_url", "ready_to_acquire",
        "requires_accession_resolution", "target_file_present", "acquisition_blocker", "operator_next_step"
    }
    require_columns(master_df, required, "real_acquisition_master_plan")
    candidates = master_df.copy()
    if bool(policy.get("prefer_ready_to_acquire", True)):
        candidates = candidates[candidates["ready_to_acquire"].apply(safe_int) == 1].copy()
    preferred_modalities = [safe_str(x) for x in policy.get("preferred_modalities", [])]
    modality_rank = {m: i for i, m in enumerate(preferred_modalities)}
    candidates["modality_rank"] = candidates["modality"].map(lambda x: modality_rank.get(safe_str(x), 999))
    candidates["target_file_present_current"] = candidates["target_local_path"].apply(lambda p: int(Path(safe_str(p)).exists()) if safe_str(p) else 0)
    candidates = candidates.sort_values(["target_file_present_current", "modality_rank", "replacement_priority", "dataset_id"]).reset_index(drop=True)
    max_pilots = max(1, safe_int(policy.get("max_pilots", 1), 1))
    if candidates.empty:
        candidates = master_df.sort_values(["replacement_priority", "dataset_id"]).head(max_pilots).copy()
        candidates["modality_rank"] = candidates["modality"].map(lambda x: modality_rank.get(safe_str(x), 999))
        candidates["target_file_present_current"] = candidates["target_local_path"].apply(lambda p: int(Path(safe_str(p)).exists()) if safe_str(p) else 0)
    else:
        candidates = candidates.head(max_pilots).copy()
    candidates["pilot_rank"] = range(1, len(candidates) + 1)
    candidates["pilot_status"] = candidates.apply(
        lambda r: "ready_for_real_file_drop" if safe_int(r.get("ready_to_acquire", 0)) == 1 and safe_int(r.get("target_file_present_current", 0)) == 0 else ("file_present_ready_for_validation" if safe_int(r.get("target_file_present_current", 0)) == 1 else "blocked_or_review"),
        axis=1,
    )
    return candidates.reset_index(drop=True)


def build_readiness(pilot_df):
    rows = []
    for _, r in pilot_df.iterrows():
        target = safe_str(r.get("target_local_path"))
        exists = int(Path(target).exists()) if target else 0
        rows.append({
            "dataset_id": safe_str(r.get("dataset_id")),
            "pilot_rank": safe_int(r.get("pilot_rank"), 1),
            "source_id": safe_str(r.get("source_id")),
            "modality": safe_str(r.get("modality")),
            "target_local_path": target,
            "target_file_present": exists,
            "requires_accession_resolution": safe_int(r.get("requires_accession_resolution", 0)),
            "ready_to_acquire": safe_int(r.get("ready_to_acquire", 0)),
            "readiness_status": "ready_for_file_placement" if exists == 0 and safe_int(r.get("requires_accession_resolution", 0)) == 0 else ("ready_for_validation_rerun" if exists == 1 else "blocked_accession_resolution"),
            "next_action": "Download/export the real public table and save it to target_local_path" if exists == 0 else "Rerun validation and schema gates",
        })
    return pd.DataFrame(rows)


def build_activation_plan(pilot_df):
    rows = []
    for _, r in pilot_df.iterrows():
        target = safe_str(r.get("target_local_path"))
        exists = int(Path(target).exists()) if target else 0
        rows.append({
            "dataset_id": safe_str(r.get("dataset_id")),
            "source_id": safe_str(r.get("source_id")),
            "accession_or_project_id": safe_str(r.get("accession_or_project_id")),
            "modality": safe_str(r.get("modality")),
            "target_local_path": target,
            "target_file_present": exists,
            "activation_status": "activation_waiting_for_real_file" if exists == 0 else "activation_candidate_file_present",
            "activation_manifest_output": f"outputs/public_data_acquisition/multi_cancer_realdata_pilot/first_real_pilot_activation/activated_manifests/{safe_str(r.get('dataset_id'))}_activated_manifest.yaml",
            "activation_rule": "Non-destructive: write activated manifest copy only after file validation succeeds; do not overwrite original manifests.",
        })
    return pd.DataFrame(rows)


def build_handoff_plan(pilot_df):
    rows = []
    for _, r in pilot_df.iterrows():
        dataset_id = safe_str(r.get("dataset_id"))
        modality = safe_str(r.get("modality"))
        rows.append({
            "dataset_id": dataset_id,
            "modality": modality,
            "target_local_path": safe_str(r.get("target_local_path")),
            "feature_store_handoff_status": "waiting_for_validated_real_file",
            "feature_store_handoff_manifest": f"outputs/public_data_acquisition/multi_cancer_realdata_pilot/first_real_pilot_activation/feature_store_handoff/{dataset_id}_feature_store_handoff.yaml",
            "suggested_processor_stage": f"{modality}_feature_store_processor",
            "handoff_rule": "Trigger only after a25 file validation and a31 modality schema validation pass.",
        })
    return pd.DataFrame(rows)


def rerun_plan():
    return "\n".join([
        "# v0.4.0-a34 first real pilot validation rerun plan",
        "# Run after placing the selected pilot file at target_local_path.",
        "python -m core.data.validate_public_dataset_replacement_readiness",
        "python -m core.data.build_public_dataset_replacement_execution_scaffold",
        "python -m core.data.validate_public_dataset_replacement_files",
        "python -m core.data.build_public_dataset_real_file_intake_bundle",
        "python -m core.data.validate_public_dataset_modality_schemas",
        "python -m core.data.build_public_dataset_source_access_packet",
        "python -m core.data.build_public_dataset_real_acquisition_accelerator",
        "python -m core.data.build_public_dataset_first_real_pilot_activation",
        "",
    ])


def operator_workbook(pilot_df, readiness_df, activation_df, handoff_df):
    lines = ["# First Real Public Dataset Pilot Operator Workbook", ""]
    for _, r in pilot_df.iterrows():
        lines += [
            f"## Pilot {safe_int(r.get('pilot_rank'), 1)}: {safe_str(r.get('dataset_id'))}",
            "",
            f"- source: `{safe_str(r.get('source_id'))}`",
            f"- accession/project: `{safe_str(r.get('accession_or_project_id'))}`",
            f"- modality: `{safe_str(r.get('modality'))}`",
            f"- portal_url: {safe_str(r.get('portal_url'))}",
            f"- target_local_path: `{safe_str(r.get('target_local_path'))}`",
            f"- status: `{safe_str(r.get('pilot_status'))}`",
            "",
            "### Action",
            "",
            "1. Export/download the public data table from the portal URL.",
            "2. Save the table at `target_local_path`.",
            "3. Run the validation rerun plan generated by this bundle.",
            "4. Activate manifest/handoff only after validation succeeds.",
            "",
        ]
    lines += ["## Validation rerun command block", "", "```powershell", rerun_plan().strip(), "```", ""]
    return "\n".join(lines)


def build_html_report(request, pilot_df, readiness_df, activation_df, handoff_df, summary):
    title = "First Real Public Dataset Pilot Activation Report"
    return "\n".join([
        "<!DOCTYPE html>", "<html>", "<head>", "<meta charset='utf-8'>", f"<title>{escape_html(title)}</title>", "</head>", "<body>",
        f"<h1>{escape_html(title)}</h1>",
        f"<p><strong>Request:</strong> {escape_html(request.get('request_id', ''))}</p>",
        f"<p><strong>Atlas:</strong> {escape_html(request.get('atlas_name', ''))}</p>",
        f"<p><strong>Selected pilots:</strong> {summary.get('selected_pilot_count', 0)}</p>",
        f"<p><strong>Pilot target files present:</strong> {summary.get('pilot_target_file_present_count', 0)}</p>",
        "<h2>Pilot selection</h2>", dataframe_to_html_table(pilot_df),
        "<h2>Pilot readiness</h2>", dataframe_to_html_table(readiness_df),
        "<h2>Activation plan</h2>", dataframe_to_html_table(activation_df),
        "<h2>Feature-store handoff plan</h2>", dataframe_to_html_table(handoff_df),
        "</body>", "</html>",
    ])


def build_public_dataset_first_real_pilot_activation(request_path=DEFAULT_REQUEST, output_dir=None):
    request = load_yaml_mapping(request_path)
    inputs = request.get("inputs", {}) or {}
    policy = request.get("pilot_policy", {}) or {}
    master_path = inputs.get("real_acquisition_master_plan")
    summary_path = inputs.get("real_acquisition_summary")
    if not master_path:
        raise ValueError("First-real-pilot request missing inputs.real_acquisition_master_plan")
    if not summary_path:
        raise ValueError("First-real-pilot request missing inputs.real_acquisition_summary")
    master_df = read_table(master_path)
    priority_df = read_table(inputs.get("real_acquisition_priority_queue", ""))
    acquisition_summary = load_yaml_mapping(summary_path)
    expected_outputs = request.get("expected_outputs", {}) or {}
    out = ensure_dir(output_dir or expected_outputs.get("first_real_pilot_activation_dir", Path("outputs/public_data_acquisition") / request.get("atlas_name", "public_data_pilot") / "first_real_pilot_activation"))
    pilot_df = select_first_pilot(master_df, priority_df, policy)
    readiness_df = build_readiness(pilot_df)
    activation_df = build_activation_plan(pilot_df)
    handoff_df = build_handoff_plan(pilot_df)
    paths = {
        "pilot_selection": out / "public_dataset_first_real_pilot_selection.tsv",
        "pilot_readiness": out / "public_dataset_first_real_pilot_readiness.tsv",
        "activation_plan": out / "public_dataset_first_real_pilot_activation_plan.tsv",
        "feature_store_handoff_plan": out / "public_dataset_first_real_pilot_feature_store_handoff_plan.tsv",
        "validation_rerun_plan": out / "public_dataset_first_real_pilot_validation_rerun_plan.ps1",
        "operator_workbook": out / "public_dataset_first_real_pilot_operator_workbook.md",
        "summary": out / "public_dataset_first_real_pilot_summary.yaml",
        "report": out / "public_dataset_first_real_pilot_report.html",
    }
    pilot_df.to_csv(paths["pilot_selection"], sep="\t", index=False)
    readiness_df.to_csv(paths["pilot_readiness"], sep="\t", index=False)
    activation_df.to_csv(paths["activation_plan"], sep="\t", index=False)
    handoff_df.to_csv(paths["feature_store_handoff_plan"], sep="\t", index=False)
    paths["validation_rerun_plan"].write_text(rerun_plan(), encoding="utf-8")
    paths["operator_workbook"].write_text(operator_workbook(pilot_df, readiness_df, activation_df, handoff_df), encoding="utf-8")
    summary = {
        "request_id": str(request.get("request_id", "")),
        "atlas_name": str(request.get("atlas_name", "")),
        "upstream_real_acquisition_request_id": str(acquisition_summary.get("request_id", "")),
        "upstream_real_acquisition_output_dir": str(acquisition_summary.get("output_dir", "")),
        "selected_pilot_count": int(pilot_df.shape[0]),
        "selected_pilot_dataset_ids": pilot_df["dataset_id"].astype(str).tolist() if not pilot_df.empty else [],
        "pilot_target_file_present_count": int(readiness_df["target_file_present"].sum()) if not readiness_df.empty else 0,
        "pilot_ready_for_file_placement_count": int((readiness_df["readiness_status"] == "ready_for_file_placement").sum()) if not readiness_df.empty else 0,
        "activation_waiting_count": int((activation_df["activation_status"] == "activation_waiting_for_real_file").sum()) if not activation_df.empty else 0,
        "handoff_waiting_count": int((handoff_df["feature_store_handoff_status"] == "waiting_for_validated_real_file").sum()) if not handoff_df.empty else 0,
        "output_dir": str(out),
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {"stage": "public_dataset_first_real_pilot_activation_bundle", "purpose": "select and prepare the first real public dataset pilot for validation, activation, and feature-store handoff"},
    }
    write_yaml(paths["summary"], summary)
    paths["report"].write_text(build_html_report(request, pilot_df, readiness_df, activation_df, handoff_df, summary), encoding="utf-8")
    return summary, pilot_df, readiness_df, activation_df, handoff_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Build first real public dataset pilot activation bundle.")
    parser.add_argument("--request", type=Path, default=DEFAULT_REQUEST)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    try:
        summary, pilot_df, readiness_df, activation_df, handoff_df, paths = build_public_dataset_first_real_pilot_activation(request_path=args.request, output_dir=args.output_dir)
    except Exception as exc:
        print(f"ERROR: First real public dataset pilot activation build failed: {exc}", file=sys.stderr)
        return 1
    print("First real public dataset pilot activation bundle complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Selected pilots: {summary['selected_pilot_count']}")
    print(f"Selected pilot dataset IDs: {', '.join(summary['selected_pilot_dataset_ids'])}")
    print(f"Pilot target files present: {summary['pilot_target_file_present_count']}")
    print(f"Ready for file placement: {summary['pilot_ready_for_file_placement_count']}")
    print(f"Report: {paths['report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

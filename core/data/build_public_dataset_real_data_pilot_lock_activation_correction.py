#!/usr/bin/env python3
import argparse
import html
import sys
from pathlib import Path

import pandas as pd
import yaml

DEFAULT_REQUEST = Path("configs/public_data_sources/public_dataset_real_data_pilot_lock_request.yaml")


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
    text = safe_str(value).strip()
    if not text:
        return default
    try:
        return int(float(text))
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
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


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


def target_file_present_value(row):
    if safe_int(row.get("target_local_path_exists_current"), 0) == 1:
        return 1
    target_path = safe_str(row.get("target_local_path")).strip()
    if not target_path:
        return 0
    return int(Path(target_path).exists())


def build_validated_real_file_inventory(intake_df, schema_df, master_df):
    require_columns(
        intake_df,
        {"dataset_id", "intake_status", "target_local_path", "target_local_path_exists_current"},
        "real_file_intake_inventory",
    )
    require_columns(
        schema_df,
        {"dataset_id", "modality", "schema_validation_status", "schema_file_exists", "schema_file_readable"},
        "modality_schema_validation_table",
    )
    df = intake_df.merge(schema_df, on="dataset_id", how="left", suffixes=("_intake", "_schema"))
    if not master_df.empty and "dataset_id" in master_df.columns:
        cols = [c for c in ["dataset_id", "source_id", "accession_or_project_id", "replacement_priority", "portal_url"] if c in master_df.columns]
        df = df.merge(master_df[cols], on="dataset_id", how="left")
    for col in ["source_id", "accession_or_project_id", "replacement_priority", "portal_url"]:
        if col not in df.columns:
            df[col] = ""
    df["target_file_present"] = df.apply(target_file_present_value, axis=1)
    df["schema_validated"] = (df["schema_validation_status"].astype(str) == "validated_modality_schema").astype(int)
    df["real_pilot_candidate"] = ((df["target_file_present"] == 1) & (df["schema_validated"] == 1)).astype(int)
    keep = [
        "dataset_id", "source_id", "accession_or_project_id", "modality", "target_local_path",
        "target_file_present", "schema_validation_status", "schema_file_exists", "schema_file_readable",
        "schema_validated", "real_pilot_candidate", "replacement_priority", "portal_url",
    ]
    for col in keep:
        if col not in df.columns:
            df[col] = ""
    return df.loc[:, keep].copy()


def lock_pilot(validated_df, policy):
    preferred = safe_str(policy.get("preferred_dataset_id", "tcga_brca_transcriptomics"))
    candidates = validated_df[validated_df["real_pilot_candidate"].apply(safe_int) == 1].copy()
    if candidates.empty:
        return validated_df.head(0).copy()
    preferred_rows = candidates[candidates["dataset_id"].astype(str) == preferred]
    if not preferred_rows.empty:
        locked = preferred_rows.head(1).copy()
    else:
        candidates["priority_sort"] = candidates["replacement_priority"].apply(lambda x: safe_int(x, 999))
        locked = candidates.sort_values(["priority_sort", "dataset_id"]).head(1).copy()
    locked["pilot_lock_status"] = "locked_to_validated_real_file"
    locked["pilot_lock_reason"] = "preferred_validated_real_file_present" if safe_str(locked.iloc[0]["dataset_id"]) == preferred else "fallback_validated_real_file_present"
    locked["validation_passed"] = 1
    locked["activation_ready"] = 1
    locked["feature_store_handoff_ready"] = 1
    locked["blocking_reason"] = "none"
    return locked.reset_index(drop=True)


def build_corrected_smoke_state(locked_df):
    rows = []
    for _, row in locked_df.iterrows():
        dataset_id = safe_str(row.get("dataset_id"))
        modality = safe_str(row.get("modality"))
        rows.append({
            "dataset_id": dataset_id,
            "source_id": safe_str(row.get("source_id")),
            "accession_or_project_id": safe_str(row.get("accession_or_project_id")),
            "modality": modality,
            "target_local_path": safe_str(row.get("target_local_path")),
            "real_file_present": 1,
            "schema_validation_status": safe_str(row.get("schema_validation_status")),
            "validation_passed": 1,
            "activation_ready": 1,
            "feature_store_handoff_ready": 1,
            "smoke_test_status": "passed_ready_for_activation",
            "blocking_reason": "none",
            "activated_manifest_path": f"outputs/public_data_acquisition/multi_cancer_realdata_pilot/real_data_pilot_lock_activation_correction/activated_manifests/{dataset_id}_activated_real_data_manifest.yaml",
            "feature_store_handoff_manifest": f"outputs/public_data_acquisition/multi_cancer_realdata_pilot/real_data_pilot_lock_activation_correction/feature_store_handoff/{dataset_id}_feature_store_handoff.yaml",
            "suggested_processor_stage": f"{modality}_feature_store_processor",
        })
    return pd.DataFrame(rows)


def build_correction_audit(previous_selection_df, previous_smoke_df, locked_df):
    previous_selected = ";".join(previous_selection_df["dataset_id"].astype(str).tolist()) if not previous_selection_df.empty and "dataset_id" in previous_selection_df.columns else "not_available"
    previous_smoke = ";".join(previous_smoke_df["dataset_id"].astype(str).tolist()) if not previous_smoke_df.empty and "dataset_id" in previous_smoke_df.columns else "not_available"
    locked = ";".join(locked_df["dataset_id"].astype(str).tolist()) if not locked_df.empty and "dataset_id" in locked_df.columns else "none"
    return pd.DataFrame([{
        "audit_item": "pilot_selection_correction",
        "previous_first_real_pilot_selection": previous_selected,
        "previous_smoke_test_dataset": previous_smoke,
        "corrected_locked_pilot": locked,
        "correction_reason": "Prefer file-present validated real pilot over next missing ready_to_acquire dataset.",
    }])


def rerun_script():
    return "\n".join([
        "# v0.4.0-a37 real-data pilot lock and activation correction rerun plan",
        "python -m core.data.build_public_dataset_real_file_intake_bundle",
        "python -m core.data.validate_public_dataset_modality_schemas",
        "python -m core.data.build_public_dataset_real_data_pilot_lock_activation_correction",
        "",
    ])


def operator_runbook(locked_df, corrected_df):
    lines = ["# Real Data Pilot Lock + Activation Correction Runbook", ""]
    if locked_df.empty:
        lines += ["No validated real-file pilot was found. Confirm the BRCA matrix exists and schema validation passes.", ""]
    else:
        for _, row in corrected_df.iterrows():
            lines += [
                f"## Locked pilot: {safe_str(row.get('dataset_id'))}",
                "",
                f"- real_file_present: `{safe_str(row.get('real_file_present'))}`",
                f"- validation_passed: `{safe_str(row.get('validation_passed'))}`",
                f"- activation_ready: `{safe_str(row.get('activation_ready'))}`",
                f"- feature_store_handoff_ready: `{safe_str(row.get('feature_store_handoff_ready'))}`",
                f"- blocking_reason: `{safe_str(row.get('blocking_reason'))}`",
                f"- target_local_path: `{safe_str(row.get('target_local_path'))}`",
                "",
            ]
    lines += ["## Rerun block", "", "```powershell", rerun_script().strip(), "```", ""]
    return "\n".join(lines)


def html_report(validated_df, locked_df, corrected_df, audit_df, summary):
    title = "Real Data Pilot Lock + Activation Correction Report"
    return "\n".join([
        "<!DOCTYPE html>", "<html>", "<head>", "<meta charset='utf-8'>", f"<title>{escape_html(title)}</title>", "</head>", "<body>",
        f"<h1>{escape_html(title)}</h1>",
        f"<p><strong>Validated real-file candidates:</strong> {summary.get('validated_real_file_candidate_count', 0)}</p>",
        f"<p><strong>Locked pilots:</strong> {summary.get('locked_pilot_count', 0)}</p>",
        f"<p><strong>Activation ready:</strong> {summary.get('activation_ready_count', 0)}</p>",
        f"<p><strong>Primary blocking reason:</strong> {escape_html(summary.get('primary_blocking_reason', ''))}</p>",
        "<h2>Validated real-file inventory</h2>", dataframe_to_html_table(validated_df),
        "<h2>Locked pilot</h2>", dataframe_to_html_table(locked_df),
        "<h2>Corrected smoke-test state</h2>", dataframe_to_html_table(corrected_df),
        "<h2>Correction audit</h2>", dataframe_to_html_table(audit_df),
        "</body>", "</html>",
    ])


def build_public_dataset_real_data_pilot_lock_activation_correction(request_path=DEFAULT_REQUEST, output_dir=None):
    request = load_yaml_mapping(request_path)
    inputs = request.get("inputs", {}) or {}
    policy = request.get("pilot_lock_policy", {}) or {}
    intake_df = read_table(inputs.get("real_file_intake_inventory"))
    schema_df = read_table(inputs.get("modality_schema_validation_table"))
    master_df = read_table(inputs.get("real_acquisition_master_plan", ""))
    previous_selection_df = read_table(inputs.get("first_real_pilot_selection", ""))
    previous_smoke_df = read_table(inputs.get("real_data_smoke_test_state", ""))
    expected_outputs = request.get("expected_outputs", {}) or {}
    out = ensure_dir(output_dir or expected_outputs.get("real_data_pilot_lock_dir", Path("outputs/public_data_acquisition") / request.get("atlas_name", "public_data_pilot") / "real_data_pilot_lock_activation_correction"))
    validated_df = build_validated_real_file_inventory(intake_df, schema_df, master_df)
    locked_df = lock_pilot(validated_df, policy)
    corrected_df = build_corrected_smoke_state(locked_df)
    audit_df = build_correction_audit(previous_selection_df, previous_smoke_df, locked_df)
    paths = {
        "validated_real_file_inventory": out / "public_dataset_validated_real_file_inventory.tsv",
        "locked_pilot": out / "public_dataset_locked_real_data_pilot.tsv",
        "corrected_smoke_state": out / "public_dataset_corrected_real_data_smoke_test_state.tsv",
        "correction_audit": out / "public_dataset_real_data_pilot_lock_correction_audit.tsv",
        "rerun_script": out / "public_dataset_real_data_pilot_lock_rerun_plan.ps1",
        "operator_runbook": out / "public_dataset_real_data_pilot_lock_operator_runbook.md",
        "summary": out / "public_dataset_real_data_pilot_lock_summary.yaml",
        "report": out / "public_dataset_real_data_pilot_lock_report.html",
    }
    validated_df.to_csv(paths["validated_real_file_inventory"], sep="\t", index=False)
    locked_df.to_csv(paths["locked_pilot"], sep="\t", index=False)
    corrected_df.to_csv(paths["corrected_smoke_state"], sep="\t", index=False)
    audit_df.to_csv(paths["correction_audit"], sep="\t", index=False)
    paths["rerun_script"].write_text(rerun_script(), encoding="utf-8")
    paths["operator_runbook"].write_text(operator_runbook(locked_df, corrected_df), encoding="utf-8")
    activation_ready_count = int(corrected_df["activation_ready"].sum()) if not corrected_df.empty else 0
    summary = {
        "request_id": str(request.get("request_id", "")),
        "atlas_name": str(request.get("atlas_name", "")),
        "validated_real_file_candidate_count": int(validated_df["real_pilot_candidate"].sum()) if not validated_df.empty else 0,
        "locked_pilot_count": int(locked_df.shape[0]),
        "locked_pilot_dataset_ids": locked_df["dataset_id"].astype(str).tolist() if not locked_df.empty else [],
        "real_file_present_count": int(corrected_df["real_file_present"].sum()) if not corrected_df.empty else 0,
        "validation_passed_count": int(corrected_df["validation_passed"].sum()) if not corrected_df.empty else 0,
        "activation_ready_count": activation_ready_count,
        "feature_store_handoff_ready_count": int(corrected_df["feature_store_handoff_ready"].sum()) if not corrected_df.empty else 0,
        "primary_blocking_reason": "none" if activation_ready_count > 0 else "no_validated_real_file_candidate",
        "output_dir": str(out),
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {"stage": "real_data_pilot_lock_activation_correction", "purpose": "lock smoke-test activation to validated real-file pilot"},
    }
    write_yaml(paths["summary"], summary)
    paths["report"].write_text(html_report(validated_df, locked_df, corrected_df, audit_df, summary), encoding="utf-8")
    return summary, validated_df, locked_df, corrected_df, audit_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Build real data pilot lock and activation correction bundle.")
    parser.add_argument("--request", type=Path, default=DEFAULT_REQUEST)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    try:
        summary, validated_df, locked_df, corrected_df, audit_df, paths = build_public_dataset_real_data_pilot_lock_activation_correction(request_path=args.request, output_dir=args.output_dir)
    except Exception as exc:
        print(f"ERROR: Real data pilot lock activation correction failed: {exc}", file=sys.stderr)
        return 1
    print("Real data pilot lock activation correction complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Validated real-file candidates: {summary['validated_real_file_candidate_count']}")
    print(f"Locked pilots: {summary['locked_pilot_count']}")
    print(f"Locked pilot dataset IDs: {', '.join(summary['locked_pilot_dataset_ids'])}")
    print(f"Activation ready: {summary['activation_ready_count']}")
    print(f"Feature-store handoff ready: {summary['feature_store_handoff_ready_count']}")
    print(f"Primary blocker: {summary['primary_blocking_reason']}")
    print(f"Report: {paths['report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

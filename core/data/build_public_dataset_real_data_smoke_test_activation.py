#!/usr/bin/env python3
import argparse, html, sys
from pathlib import Path
import pandas as pd
import yaml

DEFAULT_REQUEST = Path("configs/public_data_sources/public_dataset_real_data_smoke_test_activation_request.yaml")


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


def status_for(df, dataset_id, col, default="not_available"):
    if df.empty or "dataset_id" not in df.columns or col not in df.columns:
        return default
    sub = df[df["dataset_id"].astype(str) == safe_str(dataset_id)]
    if sub.empty:
        return default
    return safe_str(sub.iloc[0][col]) or default


def detect_blocking_reason(row):
    if safe_int(row.get("real_file_present", 0)) == 0:
        return "missing_real_file"
    if safe_str(row.get("file_validation_status")) != "validated_real_file":
        return "file_validation_not_passed"
    if safe_str(row.get("schema_validation_status")) != "validated_modality_schema":
        return "modality_schema_validation_not_passed"
    return "none"


def build_smoke_test_state(orchestrator_df, selection_df, file_validation_df, schema_df):
    require_columns(orchestrator_df, {"dataset_id", "source_id", "modality", "target_local_path", "orchestrator_status"}, "pilot_execution_orchestrator_state")
    rows = []
    for _, row in orchestrator_df.iterrows():
        dataset_id = safe_str(row.get("dataset_id"))
        target = safe_str(row.get("target_local_path"))
        real_file_present = int(Path(target).exists()) if target else 0
        file_status = status_for(file_validation_df, dataset_id, "file_validation_status", safe_str(row.get("file_validation_status", "not_available")))
        schema_status = status_for(schema_df, dataset_id, "schema_validation_status", safe_str(row.get("schema_validation_status", "not_available")))
        validation_passed = int(file_status == "validated_real_file" and schema_status == "validated_modality_schema")
        activation_ready = validation_passed
        handoff_ready = validation_passed
        state = {
            "dataset_id": dataset_id,
            "source_id": safe_str(row.get("source_id")),
            "modality": safe_str(row.get("modality")),
            "target_local_path": target,
            "real_file_present": real_file_present,
            "file_validation_status": file_status,
            "schema_validation_status": schema_status,
            "validation_passed": validation_passed,
            "activation_ready": activation_ready,
            "feature_store_handoff_ready": handoff_ready,
            "previous_orchestrator_status": safe_str(row.get("orchestrator_status")),
        }
        state["blocking_reason"] = detect_blocking_reason(state)
        state["smoke_test_status"] = "passed_ready_for_activation" if validation_passed else "blocked"
        state["next_action"] = "Generate activated manifest and feature-store handoff artifacts" if validation_passed else ("Place selected real public TSV at target_local_path" if state["blocking_reason"] == "missing_real_file" else "Rerun validation gates and inspect failing validation output")
        rows.append(state)
    return pd.DataFrame(rows)


def build_blocker_report(state_df):
    if state_df.empty:
        return pd.DataFrame(columns=["blocking_reason", "dataset_count"])
    return state_df.groupby("blocking_reason", dropna=False).size().reset_index(name="dataset_count").sort_values("blocking_reason")


def build_activation_artifact_plan(state_df):
    rows = []
    for _, row in state_df.iterrows():
        dataset_id = safe_str(row.get("dataset_id"))
        ready = safe_int(row.get("activation_ready"))
        rows.append({
            "dataset_id": dataset_id,
            "activation_ready": ready,
            "activation_artifact_status": "ready_to_write_non_destructive_copy" if ready else "not_generated_until_validation_passes",
            "activated_manifest_path": f"outputs/public_data_acquisition/multi_cancer_realdata_pilot/real_data_smoke_test_activation/activated_manifests/{dataset_id}_activated_real_data_manifest.yaml",
            "activation_rule": "Only materialize activated manifest copy after file validation and modality schema validation pass.",
        })
    return pd.DataFrame(rows)


def build_feature_store_artifact_plan(state_df):
    rows = []
    for _, row in state_df.iterrows():
        dataset_id = safe_str(row.get("dataset_id"))
        modality = safe_str(row.get("modality"))
        ready = safe_int(row.get("feature_store_handoff_ready"))
        rows.append({
            "dataset_id": dataset_id,
            "modality": modality,
            "feature_store_handoff_ready": ready,
            "handoff_artifact_status": "ready_to_write_handoff_manifest" if ready else "not_generated_until_activation_ready",
            "feature_store_handoff_manifest": f"outputs/public_data_acquisition/multi_cancer_realdata_pilot/real_data_smoke_test_activation/feature_store_handoff/{dataset_id}_feature_store_handoff.yaml",
            "suggested_processor_stage": f"{modality}_feature_store_processor",
        })
    return pd.DataFrame(rows)


def rerun_script():
    return "\n".join([
        "# v0.4.0-a36 real-data smoke-test activation rerun plan",
        "# Use after placing the selected pilot real file at target_local_path.",
        "python -m core.data.validate_public_dataset_replacement_readiness",
        "python -m core.data.build_public_dataset_replacement_execution_scaffold",
        "python -m core.data.validate_public_dataset_replacement_files",
        "python -m core.data.build_public_dataset_real_file_intake_bundle",
        "python -m core.data.validate_public_dataset_modality_schemas",
        "python -m core.data.build_public_dataset_source_access_packet",
        "python -m core.data.build_public_dataset_real_acquisition_accelerator",
        "python -m core.data.build_public_dataset_first_real_pilot_activation",
        "python -m core.data.build_public_dataset_pilot_execution_orchestrator",
        "python -m core.data.build_public_dataset_real_data_smoke_test_activation",
        "",
    ])


def operator_runbook(state_df):
    lines = ["# Real Data Smoke-Test Activation Operator Runbook", ""]
    for _, row in state_df.iterrows():
        lines += [
            f"## {safe_str(row.get('dataset_id'))}",
            "",
            f"- smoke_test_status: `{safe_str(row.get('smoke_test_status'))}`",
            f"- blocking_reason: `{safe_str(row.get('blocking_reason'))}`",
            f"- target_local_path: `{safe_str(row.get('target_local_path'))}`",
            f"- next_action: {safe_str(row.get('next_action'))}",
            "",
        ]
    lines += ["## Full rerun block", "", "```powershell", rerun_script().strip(), "```", ""]
    return "\n".join(lines)


def html_report(state_df, blocker_df, activation_df, handoff_df, summary):
    title = "Real Data Smoke-Test Activation Report"
    return "\n".join([
        "<!DOCTYPE html>", "<html>", "<head>", "<meta charset='utf-8'>", f"<title>{escape_html(title)}</title>", "</head>", "<body>",
        f"<h1>{escape_html(title)}</h1>",
        f"<p><strong>Pilot datasets:</strong> {summary.get('pilot_dataset_count', 0)}</p>",
        f"<p><strong>Real files present:</strong> {summary.get('real_file_present_count', 0)}</p>",
        f"<p><strong>Validation passed:</strong> {summary.get('validation_passed_count', 0)}</p>",
        f"<p><strong>Activation ready:</strong> {summary.get('activation_ready_count', 0)}</p>",
        f"<p><strong>Feature-store handoff ready:</strong> {summary.get('feature_store_handoff_ready_count', 0)}</p>",
        "<h2>Smoke-test state</h2>", dataframe_to_html_table(state_df),
        "<h2>Blocker report</h2>", dataframe_to_html_table(blocker_df),
        "<h2>Activation artifact plan</h2>", dataframe_to_html_table(activation_df),
        "<h2>Feature-store handoff artifact plan</h2>", dataframe_to_html_table(handoff_df),
        "</body>", "</html>",
    ])


def build_public_dataset_real_data_smoke_test_activation(request_path=DEFAULT_REQUEST, output_dir=None):
    request = load_yaml_mapping(request_path)
    inputs = request.get("inputs", {}) or {}
    state_path = inputs.get("pilot_execution_orchestrator_state")
    summary_path = inputs.get("pilot_execution_summary")
    if not state_path:
        raise ValueError("Smoke-test request missing inputs.pilot_execution_orchestrator_state")
    if not summary_path:
        raise ValueError("Smoke-test request missing inputs.pilot_execution_summary")
    orchestrator_df = read_table(state_path)
    pilot_summary = load_yaml_mapping(summary_path)
    selection_df = read_table(inputs.get("first_real_pilot_selection", ""))
    file_validation_df = read_table(inputs.get("file_validation_table", ""))
    schema_df = read_table(inputs.get("modality_schema_validation_table", ""))
    out = ensure_dir(output_dir or (request.get("expected_outputs", {}) or {}).get("real_data_smoke_test_activation_dir", Path("outputs/public_data_acquisition") / request.get("atlas_name", "public_data_pilot") / "real_data_smoke_test_activation"))
    state_df = build_smoke_test_state(orchestrator_df, selection_df, file_validation_df, schema_df)
    blocker_df = build_blocker_report(state_df)
    activation_df = build_activation_artifact_plan(state_df)
    handoff_df = build_feature_store_artifact_plan(state_df)
    paths = {
        "smoke_test_state": out / "public_dataset_real_data_smoke_test_state.tsv",
        "blocker_report": out / "public_dataset_real_data_smoke_test_blocker_report.tsv",
        "activation_artifact_plan": out / "public_dataset_real_data_activation_artifact_plan.tsv",
        "feature_store_handoff_artifact_plan": out / "public_dataset_real_data_feature_store_handoff_artifact_plan.tsv",
        "rerun_script": out / "public_dataset_real_data_smoke_test_full_rerun_plan.ps1",
        "operator_runbook": out / "public_dataset_real_data_smoke_test_operator_runbook.md",
        "summary": out / "public_dataset_real_data_smoke_test_summary.yaml",
        "report": out / "public_dataset_real_data_smoke_test_report.html",
    }
    state_df.to_csv(paths["smoke_test_state"], sep="\t", index=False)
    blocker_df.to_csv(paths["blocker_report"], sep="\t", index=False)
    activation_df.to_csv(paths["activation_artifact_plan"], sep="\t", index=False)
    handoff_df.to_csv(paths["feature_store_handoff_artifact_plan"], sep="\t", index=False)
    paths["rerun_script"].write_text(rerun_script(), encoding="utf-8")
    paths["operator_runbook"].write_text(operator_runbook(state_df), encoding="utf-8")
    summary = {
        "request_id": str(request.get("request_id", "")),
        "atlas_name": str(request.get("atlas_name", "")),
        "upstream_pilot_execution_request_id": str(pilot_summary.get("request_id", "")),
        "pilot_dataset_count": int(state_df.shape[0]),
        "real_file_present_count": int(state_df["real_file_present"].sum()) if not state_df.empty else 0,
        "validation_passed_count": int(state_df["validation_passed"].sum()) if not state_df.empty else 0,
        "activation_ready_count": int(state_df["activation_ready"].sum()) if not state_df.empty else 0,
        "feature_store_handoff_ready_count": int(state_df["feature_store_handoff_ready"].sum()) if not state_df.empty else 0,
        "primary_blocking_reason": safe_str(blocker_df.iloc[0]["blocking_reason"]) if not blocker_df.empty else "none",
        "output_dir": str(out),
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {"stage": "public_dataset_real_data_smoke_test_activation_bundle", "purpose": "detect first-pilot real-data readiness and summarize activation/handoff blockers"},
    }
    write_yaml(paths["summary"], summary)
    paths["report"].write_text(html_report(state_df, blocker_df, activation_df, handoff_df, summary), encoding="utf-8")
    return summary, state_df, blocker_df, activation_df, handoff_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Build real data smoke-test activation bundle.")
    parser.add_argument("--request", type=Path, default=DEFAULT_REQUEST)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    try:
        summary, state_df, blocker_df, activation_df, handoff_df, paths = build_public_dataset_real_data_smoke_test_activation(request_path=args.request, output_dir=args.output_dir)
    except Exception as exc:
        print(f"ERROR: Real data smoke-test activation build failed: {exc}", file=sys.stderr)
        return 1
    print("Real data smoke-test activation bundle complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Pilot datasets: {summary['pilot_dataset_count']}")
    print(f"Real files present: {summary['real_file_present_count']}")
    print(f"Validation passed: {summary['validation_passed_count']}")
    print(f"Activation ready: {summary['activation_ready_count']}")
    print(f"Feature-store handoff ready: {summary['feature_store_handoff_ready_count']}")
    print(f"Primary blocker: {summary['primary_blocking_reason']}")
    print(f"Report: {paths['report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

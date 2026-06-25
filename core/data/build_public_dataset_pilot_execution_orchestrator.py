#!/usr/bin/env python3
import argparse, html, sys
from pathlib import Path
import pandas as pd
import yaml

DEFAULT_REQUEST = Path("configs/public_data_sources/public_dataset_pilot_execution_orchestrator_request.yaml")


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


def optional_status(df, dataset_id, status_col, default="not_available"):
    if df.empty or "dataset_id" not in df.columns or status_col not in df.columns:
        return default
    sub = df[df["dataset_id"].astype(str) == safe_str(dataset_id)]
    if sub.empty:
        return default
    return safe_str(sub.iloc[0][status_col]) or default


def build_state_table(selection_df, readiness_df, activation_df, handoff_df, file_validation_df, schema_df):
    require_columns(selection_df, {"dataset_id", "source_id", "accession_or_project_id", "modality", "target_local_path", "pilot_status"}, "first_real_pilot_selection")
    rows = []
    for _, row in selection_df.iterrows():
        dataset_id = safe_str(row.get("dataset_id"))
        target = safe_str(row.get("target_local_path"))
        target_present = int(Path(target).exists()) if target else 0
        file_status = optional_status(file_validation_df, dataset_id, "file_validation_status")
        schema_status = optional_status(schema_df, dataset_id, "schema_validation_status")
        readiness_status = optional_status(readiness_df, dataset_id, "readiness_status")
        activation_status = optional_status(activation_df, dataset_id, "activation_status")
        handoff_status = optional_status(handoff_df, dataset_id, "feature_store_handoff_status")
        validation_passed = int(file_status == "validated_real_file" and schema_status == "validated_modality_schema")
        if validation_passed:
            orchestrator_status = "ready_for_manifest_activation_and_handoff"
        elif target_present:
            orchestrator_status = "file_present_validation_required"
        else:
            orchestrator_status = "waiting_for_real_file"
        rows.append({
            "dataset_id": dataset_id,
            "source_id": safe_str(row.get("source_id")),
            "accession_or_project_id": safe_str(row.get("accession_or_project_id")),
            "modality": safe_str(row.get("modality")),
            "target_local_path": target,
            "target_file_present": target_present,
            "pilot_status": safe_str(row.get("pilot_status")),
            "pilot_readiness_status": readiness_status,
            "file_validation_status": file_status,
            "schema_validation_status": schema_status,
            "activation_status": activation_status,
            "feature_store_handoff_status": handoff_status,
            "validation_passed": validation_passed,
            "orchestrator_status": orchestrator_status,
            "next_action": "Place real public file at target_local_path" if not target_present else ("Run/re-run validation gates" if not validation_passed else "Create activated manifest copy and feature-store handoff manifest"),
        })
    return pd.DataFrame(rows)


def build_manifest_activation_queue(state_df):
    rows = []
    for _, row in state_df.iterrows():
        dataset_id = safe_str(row.get("dataset_id"))
        status = "queued_activation_ready" if safe_int(row.get("validation_passed")) else "blocked_until_validation_passes"
        rows.append({
            "dataset_id": dataset_id,
            "modality": safe_str(row.get("modality")),
            "target_local_path": safe_str(row.get("target_local_path")),
            "activation_queue_status": status,
            "activated_manifest_path": f"outputs/public_data_acquisition/multi_cancer_realdata_pilot/pilot_execution_orchestrator/activated_manifest_queue/{dataset_id}_activated_manifest.yaml",
            "activation_rule": "Non-destructive copy only; do not overwrite original manifests.",
        })
    return pd.DataFrame(rows)


def build_feature_store_queue(state_df):
    rows = []
    for _, row in state_df.iterrows():
        dataset_id = safe_str(row.get("dataset_id"))
        modality = safe_str(row.get("modality"))
        status = "queued_handoff_ready" if safe_int(row.get("validation_passed")) else "blocked_until_validated_manifest"
        rows.append({
            "dataset_id": dataset_id,
            "modality": modality,
            "target_local_path": safe_str(row.get("target_local_path")),
            "feature_store_queue_status": status,
            "handoff_manifest_path": f"outputs/public_data_acquisition/multi_cancer_realdata_pilot/pilot_execution_orchestrator/feature_store_handoff_queue/{dataset_id}_feature_store_handoff.yaml",
            "suggested_processor_stage": f"{modality}_feature_store_processor",
            "handoff_rule": "Run only after file and modality schema validation both pass.",
        })
    return pd.DataFrame(rows)


def build_gate_table(state_df):
    gate_rows = []
    for _, row in state_df.iterrows():
        dataset_id = safe_str(row.get("dataset_id"))
        gates = [
            ("real_file_present", safe_int(row.get("target_file_present")) == 1),
            ("basic_file_validation", safe_str(row.get("file_validation_status")) == "validated_real_file"),
            ("modality_schema_validation", safe_str(row.get("schema_validation_status")) == "validated_modality_schema"),
            ("manifest_activation_allowed", safe_int(row.get("validation_passed")) == 1),
            ("feature_store_handoff_allowed", safe_int(row.get("validation_passed")) == 1),
        ]
        for gate, passed in gates:
            gate_rows.append({"dataset_id": dataset_id, "gate": gate, "gate_passed": int(passed), "gate_status": "passed" if passed else "blocked"})
    return pd.DataFrame(gate_rows)


def rerun_script():
    return "\n".join([
        "# v0.4.0-a35 pilot execution orchestrator rerun plan",
        "# Run after placing the selected first pilot real file at target_local_path.",
        "python -m core.data.validate_public_dataset_replacement_readiness",
        "python -m core.data.build_public_dataset_replacement_execution_scaffold",
        "python -m core.data.validate_public_dataset_replacement_files",
        "python -m core.data.build_public_dataset_real_file_intake_bundle",
        "python -m core.data.validate_public_dataset_modality_schemas",
        "python -m core.data.build_public_dataset_source_access_packet",
        "python -m core.data.build_public_dataset_real_acquisition_accelerator",
        "python -m core.data.build_public_dataset_first_real_pilot_activation",
        "python -m core.data.build_public_dataset_pilot_execution_orchestrator",
        "",
    ])


def operator_runbook(state_df, activation_queue_df, handoff_queue_df):
    lines = ["# Public Dataset Pilot Execution Orchestrator Runbook", ""]
    for _, row in state_df.iterrows():
        lines += [
            f"## {safe_str(row.get('dataset_id'))}",
            "",
            f"- orchestrator_status: `{safe_str(row.get('orchestrator_status'))}`",
            f"- target_local_path: `{safe_str(row.get('target_local_path'))}`",
            f"- file_validation_status: `{safe_str(row.get('file_validation_status'))}`",
            f"- schema_validation_status: `{safe_str(row.get('schema_validation_status'))}`",
            f"- next_action: {safe_str(row.get('next_action'))}",
            "",
        ]
    lines += ["## Full rerun block", "", "```powershell", rerun_script().strip(), "```", ""]
    return "\n".join(lines)


def html_report(request, state_df, gate_df, activation_df, handoff_df, summary):
    title = "Public Dataset Pilot Execution Orchestrator Report"
    return "\n".join([
        "<!DOCTYPE html>", "<html>", "<head>", "<meta charset='utf-8'>", f"<title>{escape_html(title)}</title>", "</head>", "<body>",
        f"<h1>{escape_html(title)}</h1>",
        f"<p><strong>Dataset count:</strong> {summary.get('pilot_dataset_count', 0)}</p>",
        f"<p><strong>Waiting for real file:</strong> {summary.get('waiting_for_real_file_count', 0)}</p>",
        f"<p><strong>Ready for activation:</strong> {summary.get('ready_for_activation_count', 0)}</p>",
        "<h2>Orchestrator state</h2>", dataframe_to_html_table(state_df),
        "<h2>Gate table</h2>", dataframe_to_html_table(gate_df),
        "<h2>Manifest activation queue</h2>", dataframe_to_html_table(activation_df),
        "<h2>Feature-store handoff queue</h2>", dataframe_to_html_table(handoff_df),
        "</body>", "</html>",
    ])


def build_public_dataset_pilot_execution_orchestrator(request_path=DEFAULT_REQUEST, output_dir=None):
    request = load_yaml_mapping(request_path)
    inputs = request.get("inputs", {}) or {}
    selection_path = inputs.get("first_real_pilot_selection")
    summary_path = inputs.get("first_real_pilot_summary")
    if not selection_path:
        raise ValueError("Pilot orchestrator request missing inputs.first_real_pilot_selection")
    if not summary_path:
        raise ValueError("Pilot orchestrator request missing inputs.first_real_pilot_summary")
    selection_df = read_table(selection_path)
    readiness_df = read_table(inputs.get("first_real_pilot_readiness", ""))
    activation_plan_df = read_table(inputs.get("first_real_pilot_activation_plan", ""))
    handoff_plan_df = read_table(inputs.get("first_real_pilot_feature_store_handoff_plan", ""))
    pilot_summary = load_yaml_mapping(summary_path)
    file_validation_df = read_table(inputs.get("file_validation_table", ""))
    schema_df = read_table(inputs.get("modality_schema_validation_table", ""))
    out = ensure_dir(output_dir or (request.get("expected_outputs", {}) or {}).get("pilot_execution_orchestrator_dir", Path("outputs/public_data_acquisition") / request.get("atlas_name", "public_data_pilot") / "pilot_execution_orchestrator"))
    state_df = build_state_table(selection_df, readiness_df, activation_plan_df, handoff_plan_df, file_validation_df, schema_df)
    activation_queue_df = build_manifest_activation_queue(state_df)
    handoff_queue_df = build_feature_store_queue(state_df)
    gate_df = build_gate_table(state_df)
    paths = {
        "orchestrator_state": out / "public_dataset_pilot_execution_orchestrator_state.tsv",
        "validation_gate_table": out / "public_dataset_pilot_execution_validation_gate_table.tsv",
        "manifest_activation_queue": out / "public_dataset_pilot_manifest_activation_queue.tsv",
        "feature_store_handoff_queue": out / "public_dataset_pilot_feature_store_handoff_queue.tsv",
        "rerun_script": out / "public_dataset_pilot_execution_full_rerun_plan.ps1",
        "operator_runbook": out / "public_dataset_pilot_execution_operator_runbook.md",
        "summary": out / "public_dataset_pilot_execution_orchestrator_summary.yaml",
        "report": out / "public_dataset_pilot_execution_orchestrator_report.html",
    }
    state_df.to_csv(paths["orchestrator_state"], sep="\t", index=False)
    gate_df.to_csv(paths["validation_gate_table"], sep="\t", index=False)
    activation_queue_df.to_csv(paths["manifest_activation_queue"], sep="\t", index=False)
    handoff_queue_df.to_csv(paths["feature_store_handoff_queue"], sep="\t", index=False)
    paths["rerun_script"].write_text(rerun_script(), encoding="utf-8")
    paths["operator_runbook"].write_text(operator_runbook(state_df, activation_queue_df, handoff_queue_df), encoding="utf-8")
    status_counts = state_df["orchestrator_status"].value_counts().to_dict() if not state_df.empty else {}
    summary = {
        "request_id": str(request.get("request_id", "")),
        "atlas_name": str(request.get("atlas_name", "")),
        "upstream_first_real_pilot_request_id": str(pilot_summary.get("request_id", "")),
        "pilot_dataset_count": int(state_df.shape[0]),
        "waiting_for_real_file_count": int(status_counts.get("waiting_for_real_file", 0)),
        "file_present_validation_required_count": int(status_counts.get("file_present_validation_required", 0)),
        "ready_for_activation_count": int(status_counts.get("ready_for_manifest_activation_and_handoff", 0)),
        "manifest_activation_queue_count": int(activation_queue_df.shape[0]),
        "feature_store_handoff_queue_count": int(handoff_queue_df.shape[0]),
        "output_dir": str(out),
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {"stage": "public_dataset_pilot_execution_orchestrator_bundle", "purpose": "combine pilot validation gates, manifest activation queue, and feature-store handoff queue"},
    }
    write_yaml(paths["summary"], summary)
    paths["report"].write_text(html_report(request, state_df, gate_df, activation_queue_df, handoff_queue_df, summary), encoding="utf-8")
    return summary, state_df, gate_df, activation_queue_df, handoff_queue_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Build public dataset pilot execution orchestrator bundle.")
    parser.add_argument("--request", type=Path, default=DEFAULT_REQUEST)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    try:
        summary, state_df, gate_df, activation_queue_df, handoff_queue_df, paths = build_public_dataset_pilot_execution_orchestrator(request_path=args.request, output_dir=args.output_dir)
    except Exception as exc:
        print(f"ERROR: Pilot execution orchestrator build failed: {exc}", file=sys.stderr)
        return 1
    print("Public dataset pilot execution orchestrator complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Pilot datasets: {summary['pilot_dataset_count']}")
    print(f"Waiting for real file: {summary['waiting_for_real_file_count']}")
    print(f"File present validation required: {summary['file_present_validation_required_count']}")
    print(f"Ready for activation: {summary['ready_for_activation_count']}")
    print(f"Report: {paths['report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

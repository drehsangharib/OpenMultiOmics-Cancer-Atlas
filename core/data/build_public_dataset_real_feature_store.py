#!/usr/bin/env python3
import argparse
import html
import math
import sys
from pathlib import Path

import pandas as pd
import yaml

DEFAULT_REQUEST = Path("configs/public_data_sources/public_dataset_real_feature_store_request.yaml")
DEFAULT_KNOWN_MATRIX_PATHS = {
    "tcga_brca_transcriptomics": "data/public/multi_cancer_realdata_pilot/brca/transcriptomics/REPLACE_WITH_TCGA_BRCA_TRANSCRIPTOMICS.tsv",
}
DEFAULT_KNOWN_MODALITIES = {
    "tcga_brca_transcriptomics": "transcriptomics",
}


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


def load_optional_yaml_mapping(path):
    if path is None:
        return {}
    raw = safe_str(path).strip()
    if not raw:
        return {}
    path = Path(raw)
    if str(path) == "." or not path.exists() or path.is_dir():
        return {}
    return load_yaml_mapping(path)


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


def require_columns(df, required, name):
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"{name} missing columns: " + ", ".join(sorted(missing)))


def escape_html(value):
    return html.escape("" if value is None else str(value))


def dataframe_to_html_table(df, max_rows=100):
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


def get_policy_mapping(policy, key, fallback):
    value = policy.get(key, fallback)
    return value if isinstance(value, dict) else fallback


def lookup_value(df, dataset_id, column_name):
    if df.empty or "dataset_id" not in df.columns or column_name not in df.columns:
        return ""
    sub = df[df["dataset_id"].astype(str) == safe_str(dataset_id)]
    if sub.empty:
        return ""
    return safe_str(sub.iloc[0][column_name]).strip()


def resolve_pilot_metadata(pilot, corrected_df, policy):
    dataset_id = safe_str(pilot.get("dataset_id")).strip()
    resolved = dict(pilot)

    modality = safe_str(resolved.get("modality")).strip()
    target_path = safe_str(resolved.get("target_local_path")).strip()

    if not modality:
        modality = lookup_value(corrected_df, dataset_id, "modality")
    if not target_path:
        target_path = lookup_value(corrected_df, dataset_id, "target_local_path")

    known_modalities = get_policy_mapping(policy, "known_modalities", DEFAULT_KNOWN_MODALITIES)
    known_paths = get_policy_mapping(policy, "known_real_matrix_paths", DEFAULT_KNOWN_MATRIX_PATHS)
    fallback_enabled = bool(policy.get("fallback_known_real_matrix_paths", True))

    if not modality:
        modality = safe_str(known_modalities.get(dataset_id, "")).strip()
    if not target_path and fallback_enabled:
        target_path = safe_str(known_paths.get(dataset_id, "")).strip()

    resolved["modality"] = modality
    resolved["target_local_path"] = target_path
    resolved["metadata_resolution_used_known_fallback"] = int(
        (not safe_str(pilot.get("modality")).strip() and bool(modality))
        or (not safe_str(pilot.get("target_local_path")).strip() and bool(target_path))
    )
    return resolved


def select_locked_pilot(locked_df, corrected_df, policy):
    if locked_df.empty:
        raise ValueError("No locked real-data pilot table found or table is empty")
    require_columns(
        locked_df,
        {"dataset_id", "target_local_path", "validation_passed", "activation_ready", "feature_store_handoff_ready"},
        "locked_real_data_pilot",
    )
    candidates = locked_df.copy()
    if "modality" not in candidates.columns:
        candidates["modality"] = ""
    if bool(policy.get("require_activation_ready", True)):
        candidates = candidates[candidates["activation_ready"].apply(safe_int) == 1].copy()
    if bool(policy.get("require_feature_store_handoff_ready", True)):
        candidates = candidates[candidates["feature_store_handoff_ready"].apply(safe_int) == 1].copy()
    if candidates.empty:
        raise ValueError("No locked pilot satisfies activation and feature-store handoff readiness requirements")
    pilot = candidates.sort_values("dataset_id").head(1).iloc[0].to_dict()
    resolved = resolve_pilot_metadata(pilot, corrected_df, policy)
    if not safe_str(resolved.get("target_local_path")).strip():
        raise ValueError(f"Locked pilot {safe_str(resolved.get('dataset_id'))} has no target_local_path and no known fallback path")
    if not safe_str(resolved.get("modality")).strip():
        raise ValueError(f"Locked pilot {safe_str(resolved.get('dataset_id'))} has no modality and no known fallback modality")
    return resolved


def load_expression_matrix(path):
    raw_path = safe_str(path).strip()
    if not raw_path:
        raise ValueError("Real expression matrix path is blank")
    matrix_path = Path(raw_path)
    if str(matrix_path) == ".":
        raise ValueError("Real expression matrix path resolved to current directory; target_local_path is blank or invalid")
    if not matrix_path.exists():
        raise FileNotFoundError(f"Real expression matrix not found: {matrix_path}")
    if matrix_path.is_dir():
        raise ValueError(f"Real expression matrix path is a directory: {matrix_path}")
    df = pd.read_csv(matrix_path, sep="\t")
    if df.empty:
        raise ValueError(f"Real expression matrix is empty: {matrix_path}")
    if df.shape[1] < 2:
        raise ValueError("Expression matrix must have one feature column and at least one sample column")
    feature_col = df.columns[0]
    df = df.rename(columns={feature_col: "feature_id"})
    for col in df.columns[1:]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def log2_x_plus_1_dataframe(values):
    numeric = values.astype(float).clip(lower=0.0)
    return numeric.apply(lambda col: col.map(lambda x: math.log2(float(x) + 1.0)))


def materialize_feature_matrix(raw_df, policy):
    feature_ids = raw_df["feature_id"].astype(str)
    values = raw_df.drop(columns=["feature_id"]).copy()
    values = values.fillna(float(policy.get("missing_value_fill", 0)))
    transform = safe_str(policy.get("feature_matrix_transform", "log2_x_plus_1"))
    if transform == "log2_x_plus_1":
        values = log2_x_plus_1_dataframe(values)
    elif transform == "none":
        values = values.astype(float)
    else:
        raise ValueError(f"Unsupported feature_matrix_transform: {transform}")
    return pd.concat([feature_ids.rename("feature_id"), values], axis=1)


def build_gene_summary(raw_df, feature_df):
    raw_values = raw_df.drop(columns=["feature_id"])
    feat_values = feature_df.drop(columns=["feature_id"])
    rows = []
    for pos, feature_id in enumerate(raw_df["feature_id"].astype(str).tolist()):
        raw_row = pd.to_numeric(raw_values.iloc[pos], errors="coerce")
        feat_row = pd.to_numeric(feat_values.iloc[pos], errors="coerce")
        rows.append({
            "feature_id": feature_id,
            "raw_mean": float(raw_row.mean()),
            "raw_median": float(raw_row.median()),
            "raw_nonzero_count": int((raw_row.fillna(0) > 0).sum()),
            "feature_mean": float(feat_row.mean()),
            "feature_std": float(feat_row.std(ddof=0)),
            "missing_count": int(raw_row.isna().sum()),
        })
    return pd.DataFrame(rows)


def build_sample_summary(raw_df, feature_df):
    sample_cols = [c for c in raw_df.columns if c != "feature_id"]
    rows = []
    for col in sample_cols:
        raw_col = pd.to_numeric(raw_df[col], errors="coerce")
        feat_col = pd.to_numeric(feature_df[col], errors="coerce")
        rows.append({
            "sample_id": col,
            "raw_total_signal": float(raw_col.fillna(0).sum()),
            "raw_detected_features": int((raw_col.fillna(0) > 0).sum()),
            "raw_missing_features": int(raw_col.isna().sum()),
            "feature_mean": float(feat_col.mean()),
            "feature_std": float(feat_col.std(ddof=0)),
        })
    return pd.DataFrame(rows)


def build_html_report(summary, sample_df, gene_df, manifest):
    title = "Real Data Feature Store Materialization Report"
    return "\n".join([
        "<!DOCTYPE html>", "<html>", "<head><meta charset='utf-8'>", f"<title>{escape_html(title)}</title>", "</head><body>",
        f"<h1>{escape_html(title)}</h1>",
        f"<p><strong>Dataset:</strong> {escape_html(summary.get('dataset_id', ''))}</p>",
        f"<p><strong>Modality:</strong> {escape_html(summary.get('modality', ''))}</p>",
        f"<p><strong>Feature count:</strong> {summary.get('feature_count', 0)}</p>",
        f"<p><strong>Sample count:</strong> {summary.get('sample_count', 0)}</p>",
        f"<p><strong>Transform:</strong> {escape_html(summary.get('feature_matrix_transform', ''))}</p>",
        f"<p><strong>Metadata fallback used:</strong> {summary.get('metadata_resolution_used_known_fallback', 0)}</p>",
        "<h2>Sample summary preview</h2>", dataframe_to_html_table(sample_df, 50),
        "<h2>Gene/feature summary preview</h2>", dataframe_to_html_table(gene_df, 50),
        "<h2>Manifest</h2><pre>", escape_html(yaml.safe_dump(manifest, sort_keys=False)), "</pre>",
        "</body></html>",
    ])


def build_public_dataset_real_feature_store(request_path=DEFAULT_REQUEST, output_dir=None):
    request = load_yaml_mapping(request_path)
    inputs = request.get("inputs", {}) or {}
    policy = request.get("feature_store_policy", {}) or {}
    locked_df = read_table(inputs.get("locked_real_data_pilot"))
    corrected_df = read_table(inputs.get("corrected_smoke_test_state", ""))
    pilot_summary = load_optional_yaml_mapping(inputs.get("pilot_lock_summary"))
    pilot = select_locked_pilot(locked_df, corrected_df, policy)
    dataset_id = safe_str(pilot.get("dataset_id"))
    modality = safe_str(pilot.get("modality"))
    matrix_path = safe_str(pilot.get("target_local_path"))
    raw_df = load_expression_matrix(matrix_path)
    feature_df = materialize_feature_matrix(raw_df, policy)
    gene_df = build_gene_summary(raw_df, feature_df)
    sample_df = build_sample_summary(raw_df, feature_df)
    out = ensure_dir(output_dir or (request.get("expected_outputs", {}) or {}).get("real_feature_store_dir", Path("outputs/public_data_acquisition") / request.get("atlas_name", "public_data_pilot") / "real_feature_store"))
    prefix = dataset_id
    paths = {
        "ai_ready_feature_matrix": out / f"{prefix}_ai_ready_feature_matrix.tsv",
        "gene_summary": out / f"{prefix}_gene_summary.tsv",
        "sample_summary": out / f"{prefix}_sample_summary.tsv",
        "feature_store_manifest": out / f"{prefix}_feature_store_manifest.yaml",
        "feature_store_summary": out / f"{prefix}_feature_store_summary.yaml",
        "feature_store_report": out / f"{prefix}_feature_store_report.html",
    }
    feature_df.to_csv(paths["ai_ready_feature_matrix"], sep="\t", index=False)
    gene_df.to_csv(paths["gene_summary"], sep="\t", index=False)
    sample_df.to_csv(paths["sample_summary"], sep="\t", index=False)
    summary = {
        "request_id": str(request.get("request_id", "")),
        "atlas_name": str(request.get("atlas_name", "")),
        "dataset_id": dataset_id,
        "modality": modality,
        "source_real_matrix": matrix_path,
        "feature_count": int(feature_df.shape[0]),
        "sample_count": int(feature_df.shape[1] - 1),
        "feature_matrix_transform": safe_str(policy.get("feature_matrix_transform", "log2_x_plus_1")),
        "activation_ready": safe_int(pilot.get("activation_ready")),
        "feature_store_handoff_ready": safe_int(pilot.get("feature_store_handoff_ready")),
        "metadata_resolution_used_known_fallback": safe_int(pilot.get("metadata_resolution_used_known_fallback")),
        "upstream_pilot_lock_request_id": str(pilot_summary.get("request_id", "")),
        "output_dir": str(out),
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {"stage": "real_data_feature_store_materialization", "purpose": "materialize validated real BRCA transcriptomics matrix into AI-ready feature store"},
    }
    manifest = {
        "feature_store_id": f"{dataset_id}_real_feature_store_v1",
        "dataset_id": dataset_id,
        "modality": modality,
        "source_real_matrix": matrix_path,
        "ai_ready_feature_matrix": str(paths["ai_ready_feature_matrix"]),
        "gene_summary": str(paths["gene_summary"]),
        "sample_summary": str(paths["sample_summary"]),
        "feature_count": summary["feature_count"],
        "sample_count": summary["sample_count"],
        "transform": summary["feature_matrix_transform"],
        "ready_for_ai_model_input": True,
        "metadata_resolution_used_known_fallback": bool(summary["metadata_resolution_used_known_fallback"]),
    }
    write_yaml(paths["feature_store_manifest"], manifest)
    write_yaml(paths["feature_store_summary"], summary)
    paths["feature_store_report"].write_text(build_html_report(summary, sample_df, gene_df, manifest), encoding="utf-8")
    return summary, feature_df, gene_df, sample_df, manifest, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Materialize validated real public-data pilot into a feature store.")
    parser.add_argument("--request", type=Path, default=DEFAULT_REQUEST)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    try:
        summary, feature_df, gene_df, sample_df, manifest, paths = build_public_dataset_real_feature_store(request_path=args.request, output_dir=args.output_dir)
    except Exception as exc:
        print(f"ERROR: Real-data feature-store materialization failed: {exc}", file=sys.stderr)
        return 1
    print("Real-data feature-store materialization complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Dataset: {summary['dataset_id']}")
    print(f"Modality: {summary['modality']}")
    print(f"Features: {summary['feature_count']}")
    print(f"Samples: {summary['sample_count']}")
    print(f"Metadata fallback used: {summary['metadata_resolution_used_known_fallback']}")
    print(f"AI-ready matrix: {paths['ai_ready_feature_matrix']}")
    print(f"Report: {paths['feature_store_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

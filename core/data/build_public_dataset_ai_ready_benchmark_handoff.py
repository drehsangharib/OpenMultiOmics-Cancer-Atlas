#!/usr/bin/env python3
import argparse
import html
import random
import sys
from pathlib import Path

import pandas as pd
import yaml

DEFAULT_REQUEST = Path("configs/public_data_sources/public_dataset_ai_ready_benchmark_handoff_request.yaml")


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


def safe_float(value, default=0.0):
    text = safe_str(value).strip()
    if not text:
        return default
    try:
        return float(text)
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


def dataframe_to_html_table(df, max_rows=50):
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


def resolve_input_path(inputs, key, manifest, manifest_key=None):
    raw = safe_str(inputs.get(key, "")).strip()
    if raw:
        return raw
    if manifest_key:
        raw = safe_str(manifest.get(manifest_key, "")).strip()
    return raw


def load_feature_matrix(path):
    path = Path(path)
    if not path.exists() or path.is_dir():
        raise FileNotFoundError(f"AI-ready feature matrix not found: {path}")
    df = pd.read_csv(path, sep="\t")
    if df.empty or df.shape[1] < 2:
        raise ValueError("AI-ready feature matrix must contain feature_id and one or more sample columns")
    if df.columns[0] != "feature_id":
        df = df.rename(columns={df.columns[0]: "feature_id"})
    sample_cols = [c for c in df.columns if c != "feature_id"]
    for col in sample_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df


def build_feature_selection(feature_df, top_n, min_var):
    sample_cols = [c for c in feature_df.columns if c != "feature_id"]
    values = feature_df[sample_cols]
    selection = pd.DataFrame({
        "feature_id": feature_df["feature_id"].astype(str),
        "feature_mean": values.mean(axis=1),
        "feature_variance": values.var(axis=1, ddof=0),
        "missing_count": values.isna().sum(axis=1),
    })
    selection = selection[selection["feature_variance"] >= min_var].copy()
    selection = selection.sort_values(["feature_variance", "feature_id"], ascending=[False, True]).reset_index(drop=True)
    selection["feature_rank"] = range(1, len(selection) + 1)
    selection["selected_for_model_input"] = (selection["feature_rank"] <= top_n).astype(int)
    return selection


def build_model_input_matrix(feature_df, feature_selection):
    selected = feature_selection[feature_selection["selected_for_model_input"] == 1]["feature_id"].astype(str).tolist()
    selected_set = set(selected)
    subset = feature_df[feature_df["feature_id"].astype(str).isin(selected_set)].copy()
    subset["feature_id"] = pd.Categorical(subset["feature_id"].astype(str), categories=selected, ordered=True)
    subset = subset.sort_values("feature_id")
    subset["feature_id"] = subset["feature_id"].astype(str)
    sample_cols = [c for c in subset.columns if c != "feature_id"]
    transposed = subset.set_index("feature_id")[sample_cols].T.reset_index().rename(columns={"index": "sample_id"})
    return transposed


def build_sample_split(sample_ids, policy):
    train_fraction = safe_float(policy.get("train_fraction", 0.70), 0.70)
    validation_fraction = safe_float(policy.get("validation_fraction", 0.15), 0.15)
    seed = safe_int(policy.get("split_seed", 39037), 39037)
    label = safe_str(policy.get("unknown_label_value", "unlabeled")) or "unlabeled"
    sample_ids = list(sample_ids)
    rng = random.Random(seed)
    shuffled = sample_ids[:]
    rng.shuffle(shuffled)
    n = len(shuffled)
    n_train = int(round(n * train_fraction))
    n_validation = int(round(n * validation_fraction))
    if n_train + n_validation > n:
        n_validation = max(0, n - n_train)
    rows = []
    for idx, sample_id in enumerate(shuffled):
        if idx < n_train:
            split = "train"
        elif idx < n_train + n_validation:
            split = "validation"
        else:
            split = "test"
        rows.append({"sample_id": sample_id, "split": split, "target_label": label, "split_seed": seed})
    return pd.DataFrame(rows).sort_values(["split", "sample_id"]).reset_index(drop=True)


def build_split_summary(split_df):
    if split_df.empty:
        return pd.DataFrame(columns=["split", "sample_count"])
    return split_df.groupby("split").size().reset_index(name="sample_count").sort_values("split")


def build_html_report(summary, feature_selection, split_summary, manifest):
    title = "Real Data AI-Ready Benchmark Handoff Report"
    return "\n".join([
        "<!DOCTYPE html>", "<html>", "<head><meta charset='utf-8'>", f"<title>{escape_html(title)}</title>", "</head><body>",
        f"<h1>{escape_html(title)}</h1>",
        f"<p><strong>Dataset:</strong> {escape_html(summary.get('dataset_id', ''))}</p>",
        f"<p><strong>Samples:</strong> {summary.get('sample_count', 0)}</p>",
        f"<p><strong>Input features:</strong> {summary.get('input_feature_count', 0)}</p>",
        f"<p><strong>Selected features:</strong> {summary.get('selected_feature_count', 0)}</p>",
        "<h2>Split summary</h2>", dataframe_to_html_table(split_summary, 20),
        "<h2>Top selected features</h2>", dataframe_to_html_table(feature_selection[feature_selection['selected_for_model_input'] == 1], 50),
        "<h2>Model handoff manifest</h2><pre>", escape_html(yaml.safe_dump(manifest, sort_keys=False)), "</pre>",
        "</body></html>",
    ])


def build_public_dataset_ai_ready_benchmark_handoff(request_path=DEFAULT_REQUEST, output_dir=None):
    request = load_yaml_mapping(request_path)
    inputs = request.get("inputs", {}) or {}
    policy = request.get("handoff_policy", {}) or {}
    manifest_path = inputs.get("feature_store_manifest")
    if not safe_str(manifest_path).strip():
        raise ValueError("Request missing inputs.feature_store_manifest")
    feature_store_manifest = load_yaml_mapping(manifest_path)
    feature_store_summary = load_yaml_mapping(inputs.get("feature_store_summary")) if safe_str(inputs.get("feature_store_summary", "")).strip() else {}
    matrix_path = resolve_input_path(inputs, "ai_ready_feature_matrix", feature_store_manifest, "ai_ready_feature_matrix")
    sample_summary_path = resolve_input_path(inputs, "sample_summary", feature_store_manifest, "sample_summary")
    gene_summary_path = resolve_input_path(inputs, "gene_summary", feature_store_manifest, "gene_summary")
    feature_df = load_feature_matrix(matrix_path)
    sample_summary_df = read_table(sample_summary_path)
    gene_summary_df = read_table(gene_summary_path)
    top_n = safe_int(policy.get("top_variable_features", 5000), 5000)
    min_var = safe_float(policy.get("min_feature_variance", 0.0), 0.0)
    feature_selection = build_feature_selection(feature_df, top_n=top_n, min_var=min_var)
    model_input = build_model_input_matrix(feature_df, feature_selection)
    sample_ids = [c for c in feature_df.columns if c != "feature_id"]
    split_df = build_sample_split(sample_ids, policy)
    split_summary = build_split_summary(split_df)
    out = ensure_dir(output_dir or (request.get("expected_outputs", {}) or {}).get("ai_ready_benchmark_handoff_dir", Path("outputs/public_data_acquisition") / request.get("atlas_name", "public_data_pilot") / "ai_ready_benchmark_handoff"))
    dataset_id = safe_str(feature_store_manifest.get("dataset_id", feature_store_summary.get("dataset_id", "tcga_brca_transcriptomics")))
    prefix = dataset_id
    paths = {
        "model_input_matrix": out / f"{prefix}_model_input_matrix.tsv",
        "feature_selection_table": out / f"{prefix}_feature_selection_table.tsv",
        "sample_split_manifest": out / f"{prefix}_sample_split_manifest.tsv",
        "split_summary": out / f"{prefix}_split_summary.tsv",
        "model_handoff_manifest": out / f"{prefix}_model_handoff_manifest.yaml",
        "ai_ready_benchmark_summary": out / f"{prefix}_ai_ready_benchmark_summary.yaml",
        "ai_ready_benchmark_report": out / f"{prefix}_ai_ready_benchmark_report.html",
    }
    model_input.to_csv(paths["model_input_matrix"], sep="\t", index=False)
    feature_selection.to_csv(paths["feature_selection_table"], sep="\t", index=False)
    split_df.to_csv(paths["sample_split_manifest"], sep="\t", index=False)
    split_summary.to_csv(paths["split_summary"], sep="\t", index=False)
    summary = {
        "request_id": str(request.get("request_id", "")),
        "atlas_name": str(request.get("atlas_name", "")),
        "dataset_id": dataset_id,
        "modality": safe_str(feature_store_manifest.get("modality", feature_store_summary.get("modality", ""))),
        "source_feature_store_manifest": safe_str(manifest_path),
        "source_ai_ready_feature_matrix": matrix_path,
        "input_feature_count": int(feature_df.shape[0]),
        "sample_count": int(len(sample_ids)),
        "selected_feature_count": int(feature_selection["selected_for_model_input"].sum()),
        "top_variable_features_requested": top_n,
        "train_fraction": safe_float(policy.get("train_fraction", 0.70), 0.70),
        "validation_fraction": safe_float(policy.get("validation_fraction", 0.15), 0.15),
        "test_fraction": safe_float(policy.get("test_fraction", 0.15), 0.15),
        "split_seed": safe_int(policy.get("split_seed", 39037), 39037),
        "sample_summary_available": int(not sample_summary_df.empty),
        "gene_summary_available": int(not gene_summary_df.empty),
        "output_dir": str(out),
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {"stage": "real_data_ai_ready_benchmark_handoff", "purpose": "prepare deterministic AI-ready benchmark inputs from real TCGA-BRCA feature store"},
    }
    model_manifest = {
        "model_handoff_id": f"{dataset_id}_ai_ready_benchmark_handoff_v1",
        "dataset_id": dataset_id,
        "modality": summary["modality"],
        "model_input_matrix": str(paths["model_input_matrix"]),
        "sample_split_manifest": str(paths["sample_split_manifest"]),
        "feature_selection_table": str(paths["feature_selection_table"]),
        "sample_count": summary["sample_count"],
        "selected_feature_count": summary["selected_feature_count"],
        "target_label_status": "placeholder_unlabeled",
        "ready_for_baseline_modeling": True,
    }
    write_yaml(paths["model_handoff_manifest"], model_manifest)
    write_yaml(paths["ai_ready_benchmark_summary"], summary)
    paths["ai_ready_benchmark_report"].write_text(build_html_report(summary, feature_selection, split_summary, model_manifest), encoding="utf-8")
    return summary, model_input, feature_selection, split_df, model_manifest, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Build real-data AI-ready benchmark handoff bundle.")
    parser.add_argument("--request", type=Path, default=DEFAULT_REQUEST)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    try:
        summary, model_input, feature_selection, split_df, manifest, paths = build_public_dataset_ai_ready_benchmark_handoff(request_path=args.request, output_dir=args.output_dir)
    except Exception as exc:
        print(f"ERROR: AI-ready benchmark handoff failed: {exc}", file=sys.stderr)
        return 1
    print("AI-ready benchmark handoff complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Dataset: {summary['dataset_id']}")
    print(f"Samples: {summary['sample_count']}")
    print(f"Input features: {summary['input_feature_count']}")
    print(f"Selected features: {summary['selected_feature_count']}")
    print(f"Model input matrix: {paths['model_input_matrix']}")
    print(f"Report: {paths['ai_ready_benchmark_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3

import argparse
import html
import subprocess
import sys
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_SMOKE_REQUEST = Path("configs/public_data_sources/public_data_execution_smoke_request.yaml")
DEFAULT_OUTPUT_ROOT = Path("outputs/public_data_acquisition")
PROCESSOR_MODULES = {
    "transcriptomics": "core.modalities.process_transcriptomics_matrix",
    "proteomics": "core.modalities.process_proteomics_matrix",
    "epigenome": "core.modalities.process_epigenome_matrix",
    "metabolomics": "core.modalities.process_metabolomics_matrix",
}


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
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Table not found: {path}")
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_csv(path, sep="\t")


def ensure_dir(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def escape_html(value):
    if value is None:
        return ""
    return html.escape(str(value))


def dataframe_to_html_table(df, max_rows=100):
    if df.empty:
        return "<p>No records available.</p>"
    out = df.head(max_rows).copy()
    lines = ["<table border='1' cellspacing='0' cellpadding='5'>", "<thead><tr>"]
    for column in out.columns:
        lines.append(f"<th>{escape_html(column)}</th>")
    lines.append("</tr></thead><tbody>")
    for _, row in out.iterrows():
        lines.append("<tr>")
        for column in out.columns:
            lines.append(f"<td>{escape_html(row[column])}</td>")
        lines.append("</tr>")
    lines.append("</tbody></table>")
    return "\n".join(lines)


def infer_expected_feature_store(manifest_path):
    manifest = load_yaml_mapping(manifest_path)
    modality = str(manifest.get("modality", ""))
    atlas_name = str(manifest.get("atlas_name", ""))
    expected_outputs = manifest.get("expected_outputs", {}) or {}
    feature_store_dir = Path(expected_outputs.get("feature_store_dir", f"outputs/features/{modality}/{atlas_name}"))
    return manifest, feature_store_dir


def run_processor_for_manifest(manifest_path, python_executable=sys.executable):
    manifest, feature_store_dir = infer_expected_feature_store(manifest_path)
    modality = str(manifest.get("modality", ""))
    module = PROCESSOR_MODULES.get(modality)
    if module is None:
        return {
            "returncode": 1,
            "stdout": "",
            "stderr": f"Unsupported modality for smoke execution: {modality}",
            "processor_module": "",
            "feature_store_dir": str(feature_store_dir),
        }

    command = [python_executable, "-m", module, "--manifest", str(manifest_path)]
    completed = subprocess.run(command, capture_output=True, text=True)
    return {
        "returncode": int(completed.returncode),
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "processor_module": module,
        "feature_store_dir": str(feature_store_dir),
    }


def inspect_feature_store(feature_store_dir):
    feature_store_dir = Path(feature_store_dir)
    expected = {
        "normalized_matrix": feature_store_dir / "normalized_matrix.tsv",
        "sample_metadata": feature_store_dir / "sample_metadata.tsv",
        "feature_metadata": feature_store_dir / "feature_metadata.tsv",
        "qc_summary": feature_store_dir / "qc_summary.tsv",
        "feature_store_manifest": feature_store_dir / "feature_store_manifest.yaml",
    }
    exists_count = sum(int(path.exists()) for path in expected.values())
    return exists_count, expected


def build_html_report(request, smoke_df):
    title = "Public Data Execution Smoke Report"
    parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        f"<title>{escape_html(title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This report verifies whether materialized public-data manifest stubs execute through modality feature-store processors.</p>",
        f"<p><strong>Request:</strong> {escape_html(request.get('request_id', ''))}</p>",
        f"<p><strong>Atlas:</strong> {escape_html(request.get('atlas_name', ''))}</p>",
        "<h2>Smoke execution results</h2>",
        dataframe_to_html_table(smoke_df),
        "<h2>Interpretation</h2>",
        "<p>Passing smoke runs indicate that local materialized manifest stubs are structurally executable. Placeholder matrices should still be replaced by real public repository files before biological interpretation.</p>",
        "</body>",
        "</html>",
    ]
    return "\n".join(parts)


def run_public_data_execution_smoke(request_path=DEFAULT_SMOKE_REQUEST, output_dir=None):
    request = load_yaml_mapping(request_path)
    materialization_summary = load_yaml_mapping(request["materialization_summary"])
    manifest_inventory_df = read_table(request["materialized_manifest_inventory"])
    expected_outputs = request.get("expected_outputs", {}) or {}
    output_dir = ensure_dir(output_dir or expected_outputs.get("smoke_run_dir", DEFAULT_OUTPUT_ROOT / request.get("atlas_name", "public_data_pilot") / "execution_smoke"))
    policy = request.get("execution_policy", {}) or {}
    continue_on_failure = bool(policy.get("continue_on_failure", True))

    rows = []
    for _, row in manifest_inventory_df.iterrows():
        manifest_path = Path(str(row["materialized_manifest_stub"]))
        manifest = load_yaml_mapping(manifest_path)
        modality = str(manifest.get("modality", row.get("modality", "")))
        atlas_hint = str(manifest.get("atlas_name", row.get("atlas_hint", "")))
        result = run_processor_for_manifest(manifest_path)
        exists_count, expected_files = inspect_feature_store(result["feature_store_dir"])
        passed = int(result["returncode"] == 0 and exists_count >= 5)
        rows.append(
            {
                "atlas_hint": atlas_hint,
                "modality": modality,
                "manifest_path": str(manifest_path),
                "processor_module": result["processor_module"],
                "returncode": result["returncode"],
                "passed": passed,
                "feature_store_dir": result["feature_store_dir"],
                "feature_store_artifacts_found": int(exists_count),
                "stdout_preview": result["stdout"][:500],
                "stderr_preview": result["stderr"][:500],
            }
        )
        if not passed and not continue_on_failure:
            break

    smoke_df = pd.DataFrame(rows)
    paths = {
        "execution_smoke_results": Path(output_dir) / "execution_smoke_results.tsv",
        "execution_smoke_summary": Path(output_dir) / "execution_smoke_summary.yaml",
        "execution_smoke_report": Path(output_dir) / "execution_smoke_report.html",
    }
    smoke_df.to_csv(paths["execution_smoke_results"], sep="\t", index=False)

    summary = {
        "request_id": str(request.get("request_id", "")),
        "atlas_name": str(request.get("atlas_name", "")),
        "source_materialization_summary": str(request["materialization_summary"]),
        "source_materialized_manifest_inventory": str(request["materialized_manifest_inventory"]),
        "materialized_manifest_count": int(materialization_summary.get("materialized_manifest_stub_count", manifest_inventory_df.shape[0])),
        "smoke_run_count": int(smoke_df.shape[0]),
        "smoke_pass_count": int(smoke_df["passed"].sum()) if not smoke_df.empty else 0,
        "smoke_fail_count": int(smoke_df.shape[0] - smoke_df["passed"].sum()) if not smoke_df.empty else 0,
        "output_dir": str(output_dir),
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {
            "stage": "public_data_execution_smoke_test",
            "purpose": "verify that materialized public-data manifest stubs execute through modality feature-store processors",
        },
    }
    write_yaml(paths["execution_smoke_summary"], summary)
    paths["execution_smoke_report"].write_text(build_html_report(request, smoke_df), encoding="utf-8")
    return summary, smoke_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Run public-data execution smoke tests against materialized manifest stubs."
    )
    parser.add_argument("--request", type=Path, default=DEFAULT_SMOKE_REQUEST)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        summary, smoke_df, paths = run_public_data_execution_smoke(
            request_path=args.request,
            output_dir=args.output_dir,
        )
    except Exception as exc:
        print(f"ERROR: Public data execution smoke run failed: {exc}", file=sys.stderr)
        return 1

    print("Public data execution smoke run complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Smoke runs: {summary['smoke_run_count']}")
    print(f"Smoke passed: {summary['smoke_pass_count']}")
    print(f"Smoke failed: {summary['smoke_fail_count']}")
    print(f"Report: {paths['execution_smoke_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

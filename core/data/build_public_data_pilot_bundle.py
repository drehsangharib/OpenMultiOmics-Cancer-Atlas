#!/usr/bin/env python3

import argparse
import html
import shutil
import sys
import zipfile
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_BUNDLE_REQUEST = Path("configs/public_data_sources/public_data_pilot_bundle_request.yaml")
DEFAULT_OUTPUT_ROOT = Path("outputs/public_data_acquisition")


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


def dataframe_to_html_table(df, max_rows=150):
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


def expected_feature_store_artifacts(feature_store_dir):
    feature_store_dir = Path(feature_store_dir)
    return {
        "normalized_matrix": feature_store_dir / "normalized_matrix.tsv",
        "sample_metadata": feature_store_dir / "sample_metadata.tsv",
        "feature_metadata": feature_store_dir / "feature_metadata.tsv",
        "qc_summary": feature_store_dir / "qc_summary.tsv",
        "feature_store_manifest": feature_store_dir / "feature_store_manifest.yaml",
    }


def validate_smoke_results(smoke_df, require_all_smoke_passed=True):
    if smoke_df.empty:
        raise ValueError("Smoke results table is empty")
    if "passed" not in smoke_df.columns:
        raise ValueError("Smoke results table must contain a passed column")
    smoke_df = smoke_df.copy()
    smoke_df["passed_int"] = smoke_df["passed"].astype(int)
    failed = smoke_df.loc[smoke_df["passed_int"] != 1]
    if require_all_smoke_passed and not failed.empty:
        failed_labels = "; ".join((failed["atlas_hint"].astype(str) + ":" + failed["modality"].astype(str)).tolist())
        raise ValueError(f"Cannot build pilot bundle because smoke failures exist: {failed_labels}")
    return smoke_df


def build_feature_store_bundle_inventory(smoke_df):
    rows = []
    for _, row in smoke_df.iterrows():
        feature_store_dir = Path(str(row["feature_store_dir"]))
        artifacts = expected_feature_store_artifacts(feature_store_dir)
        artifact_count = sum(int(path.exists()) for path in artifacts.values())
        rows.append(
            {
                "atlas_hint": str(row.get("atlas_hint", "")),
                "modality": str(row.get("modality", "")),
                "feature_store_dir": str(feature_store_dir),
                "processor_module": str(row.get("processor_module", "")),
                "smoke_passed": int(row.get("passed_int", row.get("passed", 0))),
                "artifact_count": int(artifact_count),
                "normalized_matrix": str(artifacts["normalized_matrix"]),
                "sample_metadata": str(artifacts["sample_metadata"]),
                "feature_metadata": str(artifacts["feature_metadata"]),
                "qc_summary": str(artifacts["qc_summary"]),
                "feature_store_manifest": str(artifacts["feature_store_manifest"]),
            }
        )
    return pd.DataFrame(rows)


def copy_bundle_artifacts(bundle_inventory_df, bundle_dir):
    copied_rows = []
    artifacts_dir = ensure_dir(Path(bundle_dir) / "feature_stores")
    artifact_columns = [
        "normalized_matrix",
        "sample_metadata",
        "feature_metadata",
        "qc_summary",
        "feature_store_manifest",
    ]
    for _, row in bundle_inventory_df.iterrows():
        modality = str(row["modality"])
        atlas_hint = str(row["atlas_hint"])
        destination_dir = ensure_dir(artifacts_dir / modality / atlas_hint)
        for column in artifact_columns:
            source_path = Path(str(row[column]))
            destination_path = destination_dir / source_path.name
            exists = source_path.exists()
            if exists:
                shutil.copy2(source_path, destination_path)
            copied_rows.append(
                {
                    "atlas_hint": atlas_hint,
                    "modality": modality,
                    "artifact_type": column,
                    "source_path": str(source_path),
                    "copied_path": str(destination_path),
                    "source_exists": int(exists),
                    "copied_exists": int(destination_path.exists()),
                    "copied_size_bytes": int(destination_path.stat().st_size) if destination_path.exists() else 0,
                }
            )
    return pd.DataFrame(copied_rows)


def summarize_bundle(bundle_inventory_df, copied_artifacts_df):
    rows = []
    for modality, sub in bundle_inventory_df.groupby("modality"):
        rows.append(
            {
                "modality": modality,
                "atlas_count": int(sub["atlas_hint"].nunique()),
                "feature_store_count": int(sub.shape[0]),
                "smoke_passed_count": int(sub["smoke_passed"].astype(int).sum()),
                "mean_artifact_count": float(sub["artifact_count"].mean()) if not sub.empty else 0.0,
            }
        )
    return pd.DataFrame(rows).sort_values("modality").reset_index(drop=True)


def make_bundle_archive(bundle_dir, archive_path):
    bundle_dir = Path(bundle_dir)
    archive_path = Path(archive_path)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in bundle_dir.rglob("*"):
            if path.is_file() and path.resolve() != archive_path.resolve():
                archive.write(path, path.relative_to(bundle_dir))
    return archive_path


def build_html_report(request, bundle_inventory_df, modality_summary_df, copied_artifacts_df, summary):
    title = "Public Data Pilot Feature-Store Bundle Report"
    parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        f"<title>{escape_html(title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This report collects smoke-tested public-data feature stores into a reusable pilot bundle.</p>",
        f"<p><strong>Request:</strong> {escape_html(request.get('request_id', ''))}</p>",
        f"<p><strong>Atlas:</strong> {escape_html(request.get('atlas_name', ''))}</p>",
        f"<p><strong>Feature stores:</strong> {summary.get('feature_store_count', 0)}</p>",
        f"<p><strong>Copied artifacts:</strong> {summary.get('copied_artifact_count', 0)}</p>",
        "<h2>Modality summary</h2>",
        dataframe_to_html_table(modality_summary_df),
        "<h2>Feature-store bundle inventory</h2>",
        dataframe_to_html_table(bundle_inventory_df),
        "<h2>Copied artifacts</h2>",
        dataframe_to_html_table(copied_artifacts_df),
        "<h2>Next step</h2>",
        "<p>Use the bundled feature-store manifests as inputs to the multi-omics integration layer, then run the end-to-end demo runner on the pilot bundle.</p>",
        "</body>",
        "</html>",
    ]
    return "\n".join(parts)


def build_public_data_pilot_bundle(request_path=DEFAULT_BUNDLE_REQUEST, output_dir=None):
    request = load_yaml_mapping(request_path)
    execution_summary = load_yaml_mapping(request["execution_smoke_summary"])
    smoke_df = read_table(request["execution_smoke_results"])
    policy = request.get("bundle_policy", {}) or {}
    smoke_df = validate_smoke_results(smoke_df, bool(policy.get("require_all_smoke_passed", True)))

    expected_outputs = request.get("expected_outputs", {}) or {}
    bundle_dir = ensure_dir(output_dir or expected_outputs.get("pilot_bundle_dir", DEFAULT_OUTPUT_ROOT / request.get("atlas_name", "public_data_pilot") / "pilot_feature_store_bundle"))

    bundle_inventory_df = build_feature_store_bundle_inventory(smoke_df)
    copied_artifacts_df = copy_bundle_artifacts(bundle_inventory_df, bundle_dir)
    modality_summary_df = summarize_bundle(bundle_inventory_df, copied_artifacts_df)

    paths = {
        "bundle_inventory": Path(bundle_dir) / "pilot_feature_store_bundle_inventory.tsv",
        "copied_artifact_inventory": Path(bundle_dir) / "copied_feature_store_artifacts.tsv",
        "modality_summary": Path(bundle_dir) / "pilot_bundle_modality_summary.tsv",
        "bundle_manifest": Path(bundle_dir) / "pilot_feature_store_bundle_manifest.yaml",
        "bundle_report": Path(bundle_dir) / "pilot_feature_store_bundle_report.html",
        "bundle_archive": Path(bundle_dir) / "OpenMultiOmics_public_data_pilot_feature_store_bundle.zip",
    }

    bundle_inventory_df.to_csv(paths["bundle_inventory"], sep="\t", index=False)
    copied_artifacts_df.to_csv(paths["copied_artifact_inventory"], sep="\t", index=False)
    modality_summary_df.to_csv(paths["modality_summary"], sep="\t", index=False)

    summary = {
        "request_id": str(request.get("request_id", "")),
        "atlas_name": str(request.get("atlas_name", "")),
        "source_execution_smoke_summary": str(request["execution_smoke_summary"]),
        "source_execution_smoke_results": str(request["execution_smoke_results"]),
        "smoke_run_count": int(execution_summary.get("smoke_run_count", smoke_df.shape[0])),
        "smoke_pass_count": int(execution_summary.get("smoke_pass_count", smoke_df["passed_int"].sum() if "passed_int" in smoke_df.columns else smoke_df.shape[0])),
        "feature_store_count": int(bundle_inventory_df.shape[0]),
        "copied_artifact_count": int(copied_artifacts_df["copied_exists"].sum()) if not copied_artifacts_df.empty else 0,
        "bundle_dir": str(bundle_dir),
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {
            "stage": "public_data_pilot_feature_store_bundling",
            "purpose": "collect smoke-tested public-data feature stores into a pilot bundle for downstream integration and demo execution",
        },
    }

    write_yaml(paths["bundle_manifest"], summary)
    paths["bundle_report"].write_text(build_html_report(request, bundle_inventory_df, modality_summary_df, copied_artifacts_df, summary), encoding="utf-8")
    make_bundle_archive(bundle_dir, paths["bundle_archive"])
    return summary, bundle_inventory_df, copied_artifacts_df, modality_summary_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Build a public-data pilot feature-store bundle from smoke-tested feature stores."
    )
    parser.add_argument("--request", type=Path, default=DEFAULT_BUNDLE_REQUEST)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        summary, bundle_inventory_df, copied_artifacts_df, modality_summary_df, paths = build_public_data_pilot_bundle(
            request_path=args.request,
            output_dir=args.output_dir,
        )
    except Exception as exc:
        print(f"ERROR: Public data pilot bundle build failed: {exc}", file=sys.stderr)
        return 1

    print("Public data pilot feature-store bundle complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Feature stores: {summary['feature_store_count']}")
    print(f"Copied artifacts: {summary['copied_artifact_count']}")
    print(f"Bundle manifest: {paths['bundle_manifest']}")
    print(f"Bundle archive: {paths['bundle_archive']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

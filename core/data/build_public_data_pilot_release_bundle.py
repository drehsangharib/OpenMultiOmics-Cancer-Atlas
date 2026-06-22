#!/usr/bin/env python3

import argparse
import html
import shutil
import sys
import zipfile
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_RELEASE_REQUEST = Path("configs/public_data_sources/public_data_pilot_release_bundle_request.yaml")
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


def require_existing(paths):
    missing = [str(Path(path)) for path in paths if not Path(path).exists()]
    if missing:
        raise FileNotFoundError("Missing required release input artifacts: " + "; ".join(missing))


def copy_named_artifact(label, source_path, release_dir, subdir="source_artifacts"):
    source_path = Path(source_path)
    destination_dir = ensure_dir(Path(release_dir) / subdir)
    destination_path = destination_dir / source_path.name
    shutil.copy2(source_path, destination_path)
    return {
        "artifact_label": label,
        "source_path": str(source_path),
        "release_path": str(destination_path),
        "source_exists": int(source_path.exists()),
        "release_exists": int(destination_path.exists()),
        "size_bytes": int(destination_path.stat().st_size) if destination_path.exists() else 0,
    }


def build_release_readme(summary):
    lines = [
        f"# {summary.get('release_id', '')} — {summary.get('release_name', '')}",
        "",
        "## Purpose",
        "",
        "This bundle packages the public-data pilot integration run into a reproducible release artifact.",
        "",
        "## Atlas",
        "",
        f"```text\n{summary.get('atlas_name', '')}\n```",
        "",
        "## Public-data pilot path",
        "",
        "```text",
        "public source registry",
        "-> acquisition plan",
        "-> local file materialization",
        "-> execution smoke tests",
        "-> pilot feature-store bundle",
        "-> public-data pilot multi-omics integration",
        "-> AI analysis and biological interpretation chain",
        "-> public-data pilot release bundle",
        "```",
        "",
        "## Interpretation status",
        "",
        "This bundle may still use placeholder public-data matrices unless those placeholders have been replaced with real exported public repository files.",
    ]
    return "\n".join(lines) + "\n"


def build_release_report(summary, release_inventory_df, source_artifact_df):
    title = "Public-Data Pilot Release Bundle Report"
    parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        f"<title>{escape_html(title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{escape_html(title)}</h1>",
        f"<p><strong>Release:</strong> {escape_html(summary.get('release_id', ''))}</p>",
        f"<p><strong>Atlas:</strong> {escape_html(summary.get('atlas_name', ''))}</p>",
        f"<p><strong>Integrated samples:</strong> {summary.get('integrated_samples', 0)}</p>",
        f"<p><strong>Integrated features:</strong> {summary.get('integrated_features', 0)}</p>",
        f"<p><strong>External evidence rows:</strong> {summary.get('external_evidence_rows', 0)}</p>",
        "<h2>Release inventory</h2>",
        dataframe_to_html_table(release_inventory_df),
        "<h2>Source artifacts</h2>",
        dataframe_to_html_table(source_artifact_df),
        "<h2>Next step</h2>",
        "<p>Replace placeholder matrices with real exported public repository files and rerun the public-data pilot chain for evidence-backed interpretation.</p>",
        "</body>",
        "</html>",
    ]
    return "\n".join(parts)


def make_archive(release_dir, archive_path):
    release_dir = Path(release_dir)
    archive_path = Path(archive_path)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in release_dir.rglob("*"):
            if path.is_file() and path.resolve() != archive_path.resolve():
                archive.write(path, path.relative_to(release_dir))
    return archive_path


def build_public_data_pilot_release_bundle(request_path=DEFAULT_RELEASE_REQUEST, output_dir=None):
    request = load_yaml_mapping(request_path)
    required_inputs = [
        request["source_integration_summary"],
        request["source_integration_artifact_inventory"],
        request["source_integration_report"],
        request["source_pilot_bundle_manifest"],
    ]
    require_existing(required_inputs)

    integration_summary = load_yaml_mapping(request["source_integration_summary"])
    integration_inventory_df = read_table(request["source_integration_artifact_inventory"])
    expected_outputs = request.get("expected_outputs", {}) or {}
    release_dir = ensure_dir(output_dir or expected_outputs.get("release_dir", DEFAULT_OUTPUT_ROOT / request.get("atlas_name", "public_data_pilot") / "pilot_release_bundle"))

    copied_rows = []
    copied_rows.append(copy_named_artifact("source_integration_summary", request["source_integration_summary"], release_dir))
    copied_rows.append(copy_named_artifact("source_integration_artifact_inventory", request["source_integration_artifact_inventory"], release_dir))
    copied_rows.append(copy_named_artifact("source_integration_report", request["source_integration_report"], release_dir))
    copied_rows.append(copy_named_artifact("source_pilot_bundle_manifest", request["source_pilot_bundle_manifest"], release_dir, subdir="source_manifests"))
    copied_artifacts_df = pd.DataFrame(copied_rows)

    release_manifest_path = Path(release_dir) / "public_data_pilot_release_manifest.yaml"
    release_inventory_path = Path(release_dir) / "public_data_pilot_release_inventory.tsv"
    release_report_path = Path(release_dir) / "public_data_pilot_release_report.html"
    release_readme_path = Path(release_dir) / "README.md"
    release_archive_path = Path(release_dir) / "OpenMultiOmics_public_data_pilot_release_bundle.zip"

    release_summary = {
        "request_id": str(request.get("request_id", "")),
        "release_id": str(request.get("release_id", "v0.4.0-a20")),
        "release_name": str(request.get("release_name", "Public-data pilot integration release bundle")),
        "atlas_name": str(request.get("atlas_name", integration_summary.get("atlas_name", ""))),
        "source_integration_summary": str(request["source_integration_summary"]),
        "source_pilot_bundle_manifest": str(request["source_pilot_bundle_manifest"]),
        "input_feature_store_count": int(integration_summary.get("input_feature_store_count", 0)),
        "integrated_samples": int(integration_summary.get("integrated_samples", 0)),
        "integrated_features": int(integration_summary.get("integrated_features", 0)),
        "external_evidence_rows": int(integration_summary.get("external_evidence_rows", 0)),
        "copied_source_artifact_count": int(copied_artifacts_df["release_exists"].sum()) if not copied_artifacts_df.empty else 0,
        "release_dir": str(release_dir),
        "outputs": {
            "release_manifest": str(release_manifest_path),
            "release_inventory": str(release_inventory_path),
            "release_report": str(release_report_path),
            "release_readme": str(release_readme_path),
            "release_archive": str(release_archive_path),
        },
        "agent_role": {
            "stage": "public_data_pilot_release_packaging",
            "purpose": "package public-data pilot integration outputs into a reproducible release bundle",
        },
    }

    copied_artifacts_df.to_csv(release_inventory_path, sep="\t", index=False)
    write_yaml(release_manifest_path, release_summary)
    release_readme_path.write_text(build_release_readme(release_summary), encoding="utf-8")
    release_report_path.write_text(build_release_report(release_summary, copied_artifacts_df, integration_inventory_df), encoding="utf-8")
    make_archive(release_dir, release_archive_path)

    return release_summary, copied_artifacts_df, integration_inventory_df, {
        "release_manifest": release_manifest_path,
        "release_inventory": release_inventory_path,
        "release_report": release_report_path,
        "release_readme": release_readme_path,
        "release_archive": release_archive_path,
    }


def build_arg_parser():
    parser = argparse.ArgumentParser(description="Build a public-data pilot release bundle.")
    parser.add_argument("--request", type=Path, default=DEFAULT_RELEASE_REQUEST)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        release_summary, copied_artifacts_df, integration_inventory_df, paths = build_public_data_pilot_release_bundle(
            request_path=args.request,
            output_dir=args.output_dir,
        )
    except Exception as exc:
        print(f"ERROR: Public-data pilot release bundle build failed: {exc}", file=sys.stderr)
        return 1

    print("Public-data pilot release bundle complete.")
    print(f"Release: {release_summary['release_id']}")
    print(f"Atlas: {release_summary['atlas_name']}")
    print(f"Integrated samples: {release_summary['integrated_samples']}")
    print(f"Integrated features: {release_summary['integrated_features']}")
    print(f"Release manifest: {paths['release_manifest']}")
    print(f"Release archive: {paths['release_archive']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

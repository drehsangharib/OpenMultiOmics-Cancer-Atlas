#!/usr/bin/env python3

import argparse
import html
import shutil
import sys
import zipfile
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_RELEASE_CONFIG = Path("configs/releases/v0_4_0_a14_release_bundle.yaml")
DEFAULT_RELEASE_DIR = Path("outputs/releases/v0.4.0-a14")


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


def resolve_release_config(config_path):
    config = load_yaml_mapping(config_path)
    expected_outputs = config.get("expected_outputs", {})
    release_dir = Path(expected_outputs.get("release_dir", DEFAULT_RELEASE_DIR))
    return config, release_dir


def require_existing_files(paths):
    missing = [str(path) for path in paths if not Path(path).exists()]
    if missing:
        raise FileNotFoundError("Missing required source artifacts: " + "; ".join(missing))


def copy_if_exists(source_path, release_dir, subdir="source_reports"):
    source_path = Path(source_path)
    if not source_path.exists():
        return None
    destination_dir = ensure_dir(Path(release_dir) / subdir)
    destination = destination_dir / source_path.name
    shutil.copy2(source_path, destination)
    return destination


def build_release_artifact_inventory(source_inventory_df, copied_paths, generated_paths):
    rows = []

    if not source_inventory_df.empty:
        for _, row in source_inventory_df.iterrows():
            source_path = Path(str(row.get("path", "")))
            rows.append(
                {
                    "artifact_group": "end_to_end_source_artifact",
                    "artifact_label": str(row.get("artifact_label", "")),
                    "path": str(source_path),
                    "exists": int(source_path.exists()),
                    "size_bytes": int(source_path.stat().st_size) if source_path.exists() else 0,
                }
            )

    for label, path in copied_paths.items():
        if path is None:
            continue
        path = Path(path)
        rows.append(
            {
                "artifact_group": "copied_release_source",
                "artifact_label": label,
                "path": str(path),
                "exists": int(path.exists()),
                "size_bytes": int(path.stat().st_size) if path.exists() else 0,
            }
        )

    for label, path in generated_paths.items():
        path = Path(path)
        rows.append(
            {
                "artifact_group": "generated_release_artifact",
                "artifact_label": label,
                "path": str(path),
                "exists": int(path.exists()),
                "size_bytes": int(path.stat().st_size) if path.exists() else 0,
            }
        )

    return pd.DataFrame(rows)


def build_release_readme_text(release_manifest):
    release_id = release_manifest.get("release_id", "")
    release_name = release_manifest.get("release_name", "")
    atlas_name = release_manifest.get("atlas_name", "")
    lines = [
        f"# {release_id} — {release_name}",
        "",
        "## Purpose",
        "",
        "This release bundle packages the OpenMultiOmics end-to-end demo outputs into a reproducible, auditable, and shareable release artifact.",
        "",
        "## Atlas",
        "",
        f"```text\n{atlas_name}\n```",
        "",
        "## Platform path",
        "",
        "```text",
        "feature stores",
        "-> multi-omics integration manifest",
        "-> integrated feature table",
        "-> AI analysis context",
        "-> baseline AI analysis",
        "-> biological insight seed report",
        "-> program annotation scaffold",
        "-> pathway-ready evidence layer",
        "-> external annotation connector scaffold",
        "-> release bundle",
        "```",
        "",
        "## Main artifacts",
        "",
        "```text",
        "release_manifest.yaml",
        "release_artifact_inventory.tsv",
        "release_capability_map.tsv",
        "release_summary_report.html",
        "OpenMultiOmics_v0.4.0-a14_release_bundle.zip",
        "```",
        "",
        "## Interpretation status",
        "",
        "This demo release contains scaffold-level synthetic demonstration evidence and is intended as a reproducible platform validation artifact, not as a final biological conclusion.",
    ]
    return "\n".join(lines) + "\n"


def build_release_html_report(release_manifest, artifact_inventory_df, capability_map_df):
    title = "OpenMultiOmics Release Bundle Report"
    parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        f"<title>{escape_html(title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{escape_html(title)}</h1>",
        f"<p><strong>Release:</strong> {escape_html(release_manifest.get('release_id', ''))}</p>",
        f"<p><strong>Name:</strong> {escape_html(release_manifest.get('release_name', ''))}</p>",
        f"<p><strong>Atlas:</strong> {escape_html(release_manifest.get('atlas_name', ''))}</p>",
        f"<p><strong>Artifact count:</strong> {release_manifest.get('artifact_count', 0)}</p>",
        "<h2>Capability map</h2>",
        dataframe_to_html_table(capability_map_df),
        "<h2>Release artifact inventory</h2>",
        dataframe_to_html_table(artifact_inventory_df),
        "<h2>Release meaning</h2>",
        "<p>This release validates the end-to-end OpenMultiOmics demo path from modality feature stores to external annotation evidence scaffold.</p>",
        "</body>",
        "</html>",
    ]
    return "\n".join(parts)


def make_release_archive(release_dir, archive_path):
    release_dir = Path(release_dir)
    archive_path = Path(archive_path)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in release_dir.rglob("*"):
            if path.is_file() and path.resolve() != archive_path.resolve():
                bundle.write(path, path.relative_to(release_dir))
    return archive_path


def build_end_to_end_release_bundle(config_path=DEFAULT_RELEASE_CONFIG, release_dir=None):
    config, configured_release_dir = resolve_release_config(config_path)
    release_dir = ensure_dir(release_dir or configured_release_dir)

    source_reports = config.get("source_reports", {})
    required_sources = [Path(path) for path in source_reports.values()]
    require_existing_files(required_sources)

    end_to_end_summary = load_yaml_mapping(source_reports["end_to_end_demo_summary"])
    source_inventory_df = read_table(source_reports["end_to_end_artifact_inventory"])
    capability_map_df = read_table(source_reports["platform_capability_map"])

    copied_paths = {}
    for label, source_path in source_reports.items():
        copied_paths[label] = copy_if_exists(source_path, release_dir, subdir="source_reports")

    release_manifest_path = release_dir / "release_manifest.yaml"
    release_inventory_path = release_dir / "release_artifact_inventory.tsv"
    release_capability_map_path = release_dir / "release_capability_map.tsv"
    release_report_path = release_dir / "release_summary_report.html"
    release_readme_path = release_dir / "README.md"
    release_archive_path = release_dir / "OpenMultiOmics_v0.4.0-a14_release_bundle.zip"

    capability_map_df.to_csv(release_capability_map_path, sep="\t", index=False)

    preliminary_generated_paths = {
        "release_manifest": release_manifest_path,
        "release_artifact_inventory": release_inventory_path,
        "release_capability_map": release_capability_map_path,
        "release_summary_report": release_report_path,
        "release_readme": release_readme_path,
        "release_archive": release_archive_path,
    }

    release_manifest = {
        "release_id": str(config.get("release_id", "v0.4.0-a14")),
        "release_name": str(config.get("release_name", "End-to-end platform release bundle")),
        "atlas_name": str(config.get("atlas_name", end_to_end_summary.get("atlas_name", ""))),
        "release_type": str(config.get("release_type", "reproducible_demo_release")),
        "source_demo_run_id": str(end_to_end_summary.get("demo_run_id", "")),
        "source_final_stage": str(end_to_end_summary.get("final_stage", "")),
        "integrated_samples": int(end_to_end_summary.get("integrated_samples", 0)),
        "integrated_features": int(end_to_end_summary.get("integrated_features", 0)),
        "external_evidence_rows": int(end_to_end_summary.get("external_evidence_rows", 0)),
        "artifact_count": 0,
        "outputs": {key: str(path) for key, path in preliminary_generated_paths.items()},
        "agent_role": {
            "stage": "release_bundle_generation",
            "purpose": "package the demonstrable end-to-end AI multi-omics analysis workflow into a reproducible release artifact",
        },
    }

    release_readme_path.write_text(build_release_readme_text(release_manifest), encoding="utf-8")

    artifact_inventory_df = build_release_artifact_inventory(
        source_inventory_df=source_inventory_df,
        copied_paths=copied_paths,
        generated_paths=preliminary_generated_paths,
    )
    release_manifest["artifact_count"] = int(artifact_inventory_df.shape[0])

    artifact_inventory_df.to_csv(release_inventory_path, sep="\t", index=False)
    release_report_path.write_text(build_release_html_report(release_manifest, artifact_inventory_df, capability_map_df), encoding="utf-8")
    write_yaml(release_manifest_path, release_manifest)
    make_release_archive(release_dir, release_archive_path)

    final_generated_paths = preliminary_generated_paths.copy()
    artifact_inventory_df = build_release_artifact_inventory(
        source_inventory_df=source_inventory_df,
        copied_paths=copied_paths,
        generated_paths=final_generated_paths,
    )
    artifact_inventory_df.to_csv(release_inventory_path, sep="\t", index=False)
    release_manifest["artifact_count"] = int(artifact_inventory_df.shape[0])
    write_yaml(release_manifest_path, release_manifest)

    return release_manifest, artifact_inventory_df, capability_map_df, final_generated_paths


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Build a reproducible OpenMultiOmics end-to-end release bundle."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_RELEASE_CONFIG)
    parser.add_argument("--release-dir", type=Path, default=None)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        release_manifest, artifact_inventory_df, capability_map_df, paths = build_end_to_end_release_bundle(
            config_path=args.config,
            release_dir=args.release_dir,
        )
    except Exception as exc:
        print(f"ERROR: End-to-end release bundle build failed: {exc}", file=sys.stderr)
        return 1

    print("End-to-end release bundle complete.")
    print(f"Release: {release_manifest['release_id']}")
    print(f"Atlas: {release_manifest['atlas_name']}")
    print(f"Artifact count: {release_manifest['artifact_count']}")
    print(f"Release manifest: {paths['release_manifest']}")
    print(f"Release archive: {paths['release_archive']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

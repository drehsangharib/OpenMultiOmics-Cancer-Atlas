#!/usr/bin/env python3

import argparse
import html
import shutil
import sys
from pathlib import Path

import pandas as pd
import yaml

from core.integration.build_multiomics_integration_manifest import build_multiomics_integration_manifest
from core.integration.build_multiomics_feature_table import build_integrated_feature_table
from core.agent.build_ai_multiomics_analysis_context import build_ai_multiomics_analysis_context
from core.agent.run_baseline_multiomics_analysis import run_baseline_multiomics_analysis
from core.agent.build_biological_insight_seed import build_biological_insight_seed
from core.agent.build_program_annotation_report import build_program_annotation_report
from core.agent.build_pathway_ready_evidence_layer import build_pathway_ready_evidence_layer
from core.agent.build_external_annotation_evidence import build_external_annotation_evidence


DEFAULT_INTEGRATION_REQUEST = Path("configs/public_data_sources/public_data_pilot_integration_request.yaml")
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


def collect_feature_store_manifests(bundle_inventory_df, require_all=True):
    if bundle_inventory_df.empty:
        raise ValueError("Pilot bundle inventory is empty")
    if "feature_store_manifest" not in bundle_inventory_df.columns:
        raise ValueError("Pilot bundle inventory must contain feature_store_manifest")
    paths = [Path(str(path)) for path in bundle_inventory_df["feature_store_manifest"].tolist()]
    missing = [str(path) for path in paths if not path.exists()]
    if missing and require_all:
        raise FileNotFoundError("Missing feature-store manifests in pilot bundle: " + "; ".join(missing))
    return [path for path in paths if path.exists()]


def collect_integration_artifact_inventory(artifact_paths):
    rows = []
    for label, path in artifact_paths.items():
        path = Path(path)
        rows.append(
            {
                "artifact_label": label,
                "path": str(path),
                "exists": int(path.exists()),
                "size_bytes": int(path.stat().st_size) if path.exists() else 0,
            }
        )
    return pd.DataFrame(rows)


def build_html_report(request, summary, artifact_inventory_df, bundle_inventory_df):
    title = "Public Data Pilot Integration Report"
    parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        f"<title>{escape_html(title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This report summarizes the multi-omics integration and AI interpretation chain run on the bundled public-data pilot feature stores.</p>",
        f"<p><strong>Request:</strong> {escape_html(request.get('request_id', ''))}</p>",
        f"<p><strong>Atlas:</strong> {escape_html(summary.get('atlas_name', ''))}</p>",
        f"<p><strong>Integrated samples:</strong> {summary.get('integrated_samples', 0)}</p>",
        f"<p><strong>Integrated features:</strong> {summary.get('integrated_features', 0)}</p>",
        f"<p><strong>External evidence rows:</strong> {summary.get('external_evidence_rows', 0)}</p>",
        "<h2>Input pilot bundle</h2>",
        dataframe_to_html_table(bundle_inventory_df),
        "<h2>Generated integration artifacts</h2>",
        dataframe_to_html_table(artifact_inventory_df),
        "<h2>Next step</h2>",
        "<p>Package this public-data pilot integration output into a public-data release bundle and then replace placeholders with real exported public repository files.</p>",
        "</body>",
        "</html>",
    ]
    return "\n".join(parts)


def run_public_data_pilot_integration(request_path=DEFAULT_INTEGRATION_REQUEST, output_dir=None):
    request = load_yaml_mapping(request_path)
    bundle_manifest = load_yaml_mapping(request["pilot_bundle_manifest"])
    bundle_inventory_df = read_table(request["pilot_bundle_inventory"])
    policy = request.get("integration_policy", {}) or {}
    require_all = bool(policy.get("require_all_feature_store_manifests", True))
    atlas_name = str(request.get("atlas_name", "multi_cancer_public_data_pilot"))
    expected_outputs = request.get("expected_outputs", {}) or {}
    output_dir = ensure_dir(output_dir or expected_outputs.get("integration_run_dir", DEFAULT_OUTPUT_ROOT / atlas_name / "pilot_integration_run"))

    feature_store_manifests = collect_feature_store_manifests(bundle_inventory_df, require_all=require_all)

    integration_manifest, alignment_df, modality_inventory_df, alignment_qc_df, integration_paths = build_multiomics_integration_manifest(
        atlas_name=atlas_name,
        manifest_paths=feature_store_manifests,
        integrated_root=Path(output_dir) / "integrated",
    )

    integrated_df, feature_block_df, integrated_qc_df, feature_table_paths = build_integrated_feature_table(
        integration_manifest_path=integration_paths["multiomics_integration_manifest"],
        output_dir=Path(integration_paths["output_dir"]),
        complete_cases_only=bool(policy.get("complete_cases_only", True)),
    )

    context, context_path = build_ai_multiomics_analysis_context(
        integration_manifest_path=integration_paths["multiomics_integration_manifest"],
        integrated_feature_matrix_path=feature_table_paths["integrated_feature_matrix"],
        feature_block_inventory_path=feature_table_paths["feature_block_inventory"],
        integrated_feature_qc_summary_path=feature_table_paths["integrated_feature_qc_summary"],
    )

    baseline_summary, embedding_df, clusters_df, feature_rankings_df, modality_summary_df, baseline_paths = run_baseline_multiomics_analysis(
        analysis_context_path=context_path,
        output_dir=Path(output_dir) / "baseline_ai_analysis",
    )

    insight_summary, annotated_features_df, modality_program_df, themes_df, insight_paths = build_biological_insight_seed(
        analysis_context_path=context_path,
        baseline_analysis_dir=Path(baseline_paths["baseline_analysis_summary"]).parent,
        output_dir=Path(output_dir) / "biological_insight_seed",
    )

    program_summary, program_annotations_df, program_level_df, priority_df, program_paths = build_program_annotation_report(
        biological_insight_seed_dir=Path(insight_paths["biological_insight_seed_summary"]).parent,
        output_dir=Path(output_dir) / "program_annotation",
    )

    pathway_summary, feature_evidence_df, program_evidence_df, pathway_priority_df, pathway_paths = build_pathway_ready_evidence_layer(
        program_annotation_dir=Path(program_paths["program_annotation_summary"]).parent,
        output_dir=Path(output_dir) / "pathway_ready_evidence",
    )

    external_summary, external_evidence_df, external_term_df, connector_inventory_df, readiness_df, external_paths = build_external_annotation_evidence(
        pathway_ready_evidence_dir=Path(pathway_paths["pathway_ready_evidence_summary"]).parent,
        output_dir=Path(output_dir) / "external_annotation_evidence",
    )

    artifact_paths = {
        "multiomics_integration_manifest": integration_paths["multiomics_integration_manifest"],
        "sample_alignment": integration_paths["sample_alignment"],
        "integrated_feature_matrix": feature_table_paths["integrated_feature_matrix"],
        "ai_multiomics_analysis_context": context_path,
        "baseline_analysis_summary": baseline_paths["baseline_analysis_summary"],
        "biological_insight_seed_summary": insight_paths["biological_insight_seed_summary"],
        "program_annotation_summary": program_paths["program_annotation_summary"],
        "pathway_ready_evidence_summary": pathway_paths["pathway_ready_evidence_summary"],
        "external_annotation_summary": external_paths["external_annotation_summary"],
        "external_annotation_report": external_paths["external_annotation_report"],
    }

    artifact_inventory_df = collect_integration_artifact_inventory(artifact_paths)
    artifact_inventory_path = Path(output_dir) / "public_data_pilot_integration_artifact_inventory.tsv"
    summary_path = Path(output_dir) / "public_data_pilot_integration_summary.yaml"
    report_path = Path(output_dir) / "public_data_pilot_integration_report.html"
    copied_bundle_manifest_path = Path(output_dir) / "source_pilot_feature_store_bundle_manifest.yaml"
    shutil.copy2(request["pilot_bundle_manifest"], copied_bundle_manifest_path)

    artifact_inventory_df.to_csv(artifact_inventory_path, sep="\t", index=False)

    summary = {
        "request_id": str(request.get("request_id", "")),
        "atlas_name": atlas_name,
        "source_pilot_bundle_manifest": str(request["pilot_bundle_manifest"]),
        "source_pilot_bundle_inventory": str(request["pilot_bundle_inventory"]),
        "input_feature_store_count": int(len(feature_store_manifests)),
        "modality_count": int(modality_inventory_df.shape[0]),
        "integrated_samples": int(integrated_df.shape[0]),
        "integrated_features": int(max(integrated_df.shape[1] - 1, 0)),
        "baseline_clusters": int(baseline_summary.get("clusters_observed", 0)),
        "candidate_theme_count": int(insight_summary.get("candidate_theme_count", 0)),
        "program_count": int(program_summary.get("program_count", 0)),
        "pathway_ready_evidence_rows": int(pathway_summary.get("feature_evidence_count", 0)),
        "external_evidence_rows": int(external_summary.get("external_evidence_rows", 0)),
        "output_dir": str(output_dir),
        "outputs": {
            "artifact_inventory": str(artifact_inventory_path),
            "summary": str(summary_path),
            "report": str(report_path),
            "source_pilot_bundle_manifest": str(copied_bundle_manifest_path),
        },
        "agent_role": {
            "stage": "public_data_pilot_integration_execution",
            "purpose": "run multi-omics integration and AI interpretation on public-data pilot feature-store bundles",
        },
    }

    write_yaml(summary_path, summary)
    report_path.write_text(build_html_report(request, summary, artifact_inventory_df, bundle_inventory_df), encoding="utf-8")
    return summary, artifact_inventory_df, bundle_inventory_df, artifact_paths


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Run multi-omics integration and AI analysis on a public-data pilot feature-store bundle."
    )
    parser.add_argument("--request", type=Path, default=DEFAULT_INTEGRATION_REQUEST)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    try:
        summary, artifact_inventory_df, bundle_inventory_df, artifact_paths = run_public_data_pilot_integration(
            request_path=args.request,
            output_dir=args.output_dir,
        )
    except Exception as exc:
        print(f"ERROR: Public data pilot integration failed: {exc}", file=sys.stderr)
        return 1

    print("Public data pilot integration complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Input feature stores: {summary['input_feature_store_count']}")
    print(f"Integrated samples: {summary['integrated_samples']}")
    print(f"Integrated features: {summary['integrated_features']}")
    print(f"External evidence rows: {summary['external_evidence_rows']}")
    print(f"Report: {summary['outputs']['report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

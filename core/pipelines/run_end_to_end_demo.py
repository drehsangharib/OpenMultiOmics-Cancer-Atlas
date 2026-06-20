#!/usr/bin/env python3

import argparse
import html
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


DEFAULT_DEMO_CONFIG = Path("configs/demo_runs/multi_cancer_demo_run.yaml")
DEFAULT_ATLAS_NAME = "multi_cancer_demo"
DEFAULT_REPORT_DIR = Path("outputs/reports/end_to_end_demo")
DEFAULT_FEATURE_STORE_MANIFESTS = [
    Path("outputs/features/transcriptomics/brca/feature_store_manifest.yaml"),
    Path("outputs/features/proteomics/luad/feature_store_manifest.yaml"),
    Path("outputs/features/epigenome/gbm/feature_store_manifest.yaml"),
    Path("outputs/features/metabolomics/multi_cancer/feature_store_manifest.yaml"),
]


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


def ensure_dir(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_table(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Table not found: {path}")
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_csv(path, sep="\t")


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


def resolve_demo_config(config_path=None, atlas_name=None, report_dir=None, manifest_paths=None):
    config = {}
    if config_path and Path(config_path).exists():
        config = load_yaml_mapping(config_path)

    resolved_atlas = atlas_name or config.get("atlas_name", DEFAULT_ATLAS_NAME)
    resolved_report_dir = Path(report_dir or config.get("expected_outputs", {}).get("final_report_dir", DEFAULT_REPORT_DIR))

    if manifest_paths:
        resolved_manifests = [Path(path) for path in manifest_paths]
    else:
        configured = config.get("feature_store_manifests", [])
        resolved_manifests = [Path(path) for path in configured] if configured else DEFAULT_FEATURE_STORE_MANIFESTS

    return {
        "demo_run_id": config.get("demo_run_id", f"{resolved_atlas}_end_to_end_demo"),
        "atlas_name": resolved_atlas,
        "report_dir": resolved_report_dir,
        "feature_store_manifests": resolved_manifests,
    }


def assert_required_paths(paths):
    missing = [str(path) for path in paths if not Path(path).exists()]
    if missing:
        raise FileNotFoundError("Missing required input paths: " + "; ".join(missing))


def collect_artifact_inventory(artifact_paths):
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


def build_capability_map():
    return pd.DataFrame(
        [
            {"layer": "A1", "capability": "data manifest registry", "status": "available"},
            {"layer": "A2-A5", "capability": "modality feature-store pipelines", "status": "available"},
            {"layer": "A6", "capability": "multi-omics sample alignment and integration manifest", "status": "available"},
            {"layer": "A7", "capability": "integrated feature table and AI analysis context", "status": "available"},
            {"layer": "A8", "capability": "baseline AI multi-omics analysis", "status": "available"},
            {"layer": "A9", "capability": "biological insight seed report", "status": "available"},
            {"layer": "A10", "capability": "biological program annotation scaffold", "status": "available"},
            {"layer": "A11", "capability": "pathway-ready evidence layer", "status": "available"},
            {"layer": "A12", "capability": "external annotation connector scaffold", "status": "available"},
            {"layer": "A13", "capability": "end-to-end demo runner and release report", "status": "current"},
        ]
    )


def build_html_report(summary, capability_df, artifact_inventory_df):
    title = "OpenMultiOmics End-to-End Demo Report"
    parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        f"<title>{escape_html(title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This report summarizes the complete demo path from modality feature stores to external annotation evidence.</p>",
        f"<p><strong>Atlas:</strong> {escape_html(summary.get('atlas_name', ''))}</p>",
        f"<p><strong>Final stage:</strong> {escape_html(summary.get('final_stage', ''))}</p>",
        f"<p><strong>Artifacts generated:</strong> {summary.get('artifact_count', 0)}</p>",
        "<h2>Capability map</h2>",
        dataframe_to_html_table(capability_df),
        "<h2>Artifact inventory</h2>",
        dataframe_to_html_table(artifact_inventory_df),
        "<h2>Recommended next steps</h2>",
        "<ul>",
        "<li>Add true external annotation connectors for real pathway, ontology, and gene-set resources.</li>",
        "<li>Add richer biological report generation with cohort/cluster-level interpretation.</li>",
        "<li>Add public real-data acquisition runners to replace synthetic demonstration matrices.</li>",
        "<li>Add release packaging for all generated reports and manifests.</li>",
        "</ul>",
        "</body>",
        "</html>",
    ]
    return "\n".join(parts)


def run_end_to_end_demo(config_path=DEFAULT_DEMO_CONFIG, atlas_name=None, report_dir=None, manifest_paths=None):
    cfg = resolve_demo_config(
        config_path=config_path,
        atlas_name=atlas_name,
        report_dir=report_dir,
        manifest_paths=manifest_paths,
    )
    atlas = cfg["atlas_name"]
    report_dir = ensure_dir(cfg["report_dir"])
    feature_store_manifests = cfg["feature_store_manifests"]
    assert_required_paths(feature_store_manifests)

    integration_manifest, alignment_df, modality_inventory_df, alignment_qc_df, integration_paths = build_multiomics_integration_manifest(
        atlas_name=atlas,
        manifest_paths=feature_store_manifests,
    )

    integrated_df, feature_block_df, integrated_qc_df, feature_table_paths = build_integrated_feature_table(
        integration_manifest_path=integration_paths["multiomics_integration_manifest"]
    )

    context, context_path = build_ai_multiomics_analysis_context(
        integration_manifest_path=integration_paths["multiomics_integration_manifest"],
        integrated_feature_matrix_path=feature_table_paths["integrated_feature_matrix"],
        feature_block_inventory_path=feature_table_paths["feature_block_inventory"],
        integrated_feature_qc_summary_path=feature_table_paths["integrated_feature_qc_summary"],
    )

    baseline_summary, embedding_df, clusters_df, feature_rankings_df, modality_summary_df, baseline_paths = run_baseline_multiomics_analysis(
        analysis_context_path=context_path
    )

    insight_summary, annotated_features_df, modality_program_df, themes_df, insight_paths = build_biological_insight_seed(
        analysis_context_path=context_path,
        baseline_analysis_dir=Path(baseline_paths["baseline_analysis_summary"]).parent,
    )

    program_summary, program_annotations_df, program_level_df, priority_df, program_paths = build_program_annotation_report(
        biological_insight_seed_dir=Path(insight_paths["biological_insight_seed_summary"]).parent
    )

    pathway_summary, feature_evidence_df, program_evidence_df, pathway_priority_df, pathway_paths = build_pathway_ready_evidence_layer(
        program_annotation_dir=Path(program_paths["program_annotation_summary"]).parent
    )

    external_summary, external_evidence_df, external_term_df, connector_inventory_df, readiness_df, external_paths = build_external_annotation_evidence(
        pathway_ready_evidence_dir=Path(pathway_paths["pathway_ready_evidence_summary"]).parent
    )

    artifact_paths = {
        "multiomics_integration_manifest": integration_paths["multiomics_integration_manifest"],
        "sample_alignment": integration_paths["sample_alignment"],
        "integrated_feature_matrix": feature_table_paths["integrated_feature_matrix"],
        "ai_multiomics_analysis_context": context_path,
        "baseline_analysis_summary": baseline_paths["baseline_analysis_summary"],
        "baseline_multiomics_insight_report": baseline_paths["baseline_multiomics_insight_report"],
        "biological_insight_seed_summary": insight_paths["biological_insight_seed_summary"],
        "biological_insight_seed_report": insight_paths["biological_insight_seed_report"],
        "program_annotation_summary": program_paths["program_annotation_summary"],
        "program_annotation_report": program_paths["program_annotation_report"],
        "pathway_ready_evidence_summary": pathway_paths["pathway_ready_evidence_summary"],
        "pathway_ready_evidence_report": pathway_paths["pathway_ready_evidence_report"],
        "external_annotation_summary": external_paths["external_annotation_summary"],
        "external_annotation_report": external_paths["external_annotation_report"],
    }

    artifact_inventory_df = collect_artifact_inventory(artifact_paths)
    capability_df = build_capability_map()

    artifact_inventory_path = report_dir / "end_to_end_artifact_inventory.tsv"
    capability_map_path = report_dir / "platform_capability_map.tsv"
    summary_path = report_dir / "end_to_end_demo_summary.yaml"
    report_html_path = report_dir / "end_to_end_demo_report.html"

    artifact_inventory_df.to_csv(artifact_inventory_path, sep="\t", index=False)
    capability_df.to_csv(capability_map_path, sep="\t", index=False)

    summary = {
        "demo_run_id": cfg["demo_run_id"],
        "atlas_name": atlas,
        "final_stage": "external_annotation_connector_scaffold",
        "feature_store_manifest_count": int(len(feature_store_manifests)),
        "modality_count": int(modality_inventory_df.shape[0]),
        "integrated_samples": int(integrated_df.shape[0]),
        "integrated_features": int(max(integrated_df.shape[1] - 1, 0)),
        "baseline_clusters": int(baseline_summary.get("clusters_observed", 0)),
        "biological_themes": int(insight_summary.get("candidate_theme_count", 0)),
        "program_count": int(program_summary.get("program_count", 0)),
        "pathway_ready_evidence_rows": int(pathway_summary.get("feature_evidence_count", 0)),
        "external_evidence_rows": int(external_summary.get("external_evidence_rows", 0)),
        "artifact_count": int(artifact_inventory_df.shape[0]),
        "outputs": {
            "artifact_inventory": str(artifact_inventory_path),
            "capability_map": str(capability_map_path),
            "summary": str(summary_path),
            "html_report": str(report_html_path),
        },
        "agent_role": {
            "stage": "end_to_end_demo_orchestration",
            "purpose": "demonstrate the full AI multi-omics analysis system path from feature stores to external annotation evidence scaffold",
        },
    }

    write_yaml(summary_path, summary)
    report_html_path.write_text(build_html_report(summary, capability_df, artifact_inventory_df), encoding="utf-8")

    paths = {
        "summary": summary_path,
        "html_report": report_html_path,
        "artifact_inventory": artifact_inventory_path,
        "capability_map": capability_map_path,
    }

    return summary, artifact_inventory_df, capability_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Run the OpenMultiOmics end-to-end demo from feature stores to external annotation evidence."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_DEMO_CONFIG)
    parser.add_argument("--atlas", default=None)
    parser.add_argument("--report-dir", type=Path, default=None)
    parser.add_argument("--manifest-paths", nargs="*", default=None)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        summary, artifact_inventory_df, capability_df, paths = run_end_to_end_demo(
            config_path=args.config,
            atlas_name=args.atlas,
            report_dir=args.report_dir,
            manifest_paths=args.manifest_paths,
        )
    except Exception as exc:
        print(f"ERROR: End-to-end demo run failed: {exc}", file=sys.stderr)
        return 1

    print("End-to-end OpenMultiOmics demo complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Final stage: {summary['final_stage']}")
    print(f"Integrated samples: {summary['integrated_samples']}")
    print(f"Integrated features: {summary['integrated_features']}")
    print(f"External evidence rows: {summary['external_evidence_rows']}")
    print(f"Report: {paths['html_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

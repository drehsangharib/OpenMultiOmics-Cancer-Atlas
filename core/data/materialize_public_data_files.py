#!/usr/bin/env python3

import argparse
import html
import sys
from pathlib import Path

import pandas as pd
import yaml


DEFAULT_MATERIALIZATION_REQUEST = Path("configs/public_data_sources/local_file_materialization_request.yaml")
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


def get_template_input_file(template):
    input_files = template.get("input_files", [])
    if not isinstance(input_files, list) or not input_files:
        raise ValueError("Manifest template must contain at least one input_files entry")
    first = input_files[0]
    if not isinstance(first, dict):
        raise ValueError("input_files[0] must be a mapping")
    return first


def infer_placeholder_matrix(modality):
    if modality == "transcriptomics":
        return "sample_id\tGENE1\tGENE2\tGENE3\nS1\t1\t2\t3\nS2\t2\t3\t4\nS3\t3\t4\t5\n"
    if modality == "proteomics":
        return "sample_id\tPROT1\tPROT2\tPROT3\nS1\t10\t20\t30\nS2\t20\t30\t40\nS3\t30\t40\t50\n"
    if modality == "epigenome":
        return "sample_id\tCG0001\tCG0002\tCG0003\nS1\t0.2\t0.3\t0.4\nS2\t0.5\t0.6\t0.7\nS3\t0.8\t0.9\t1.0\n"
    if modality == "metabolomics":
        return "sample_id\tMET1\tMET2\tMET3\nS1\t100\t200\t300\nS2\t200\t300\t400\nS3\t300\t400\t500\n"
    return "sample_id\tFEATURE1\tFEATURE2\nS1\t1\t2\nS2\t2\t3\n"


def modality_defaults(modality):
    defaults = {
        "transcriptomics": {
            "data_type": "gene_expression_matrix",
            "assay": "rna_seq",
            "feature_id_type": "gene_symbol_or_ensembl_id",
            "normalization": "log2_tpm_plus_one",
            "missing_value_strategy": "median_feature_imputation",
            "feature_filtering": "remove_zero_variance_features",
        },
        "proteomics": {
            "data_type": "protein_abundance_matrix",
            "assay": "mass_spectrometry",
            "feature_id_type": "protein_id_or_gene_symbol",
            "normalization": "median_centering",
            "missing_value_strategy": "half_minimum_imputation",
            "feature_filtering": "remove_high_missingness_features",
        },
        "epigenome": {
            "data_type": "dna_methylation_matrix",
            "assay": "methylation_array",
            "feature_id_type": "cpg_probe_id",
            "normalization": "beta_value_clipping",
            "missing_value_strategy": "median_feature_imputation",
            "feature_filtering": "remove_high_missingness_features",
        },
        "metabolomics": {
            "data_type": "metabolite_abundance_matrix",
            "assay": "mass_spectrometry_or_nmr",
            "feature_id_type": "metabolite_name_or_identifier",
            "normalization": "log_transform_then_scale",
            "missing_value_strategy": "half_minimum_imputation",
            "feature_filtering": "remove_high_missingness_features",
        },
    }
    return defaults.get(modality, defaults["transcriptomics"])


def source_url_for_source(source_name):
    source_name = str(source_name).lower()
    if source_name == "gdc_tcga":
        return "https://portal.gdc.cancer.gov/"
    if source_name == "cptac":
        return "https://proteomic.datacommons.cancer.gov/"
    if source_name == "metabolomics_workbench":
        return "https://www.metabolomicsworkbench.org/"
    return "https://example.org/public-data-placeholder"


def build_realdata_manifest_stub(template, local_file_path, atlas_name):
    modality = str(template.get("modality", "unknown"))
    defaults = modality_defaults(modality)
    input_file = get_template_input_file(template)
    atlas_hint = str(template.get("atlas_name", atlas_name))
    source_name = str(template.get("source_name", "public_data_source"))

    feature_store_dir = Path("outputs") / "features" / modality / atlas_hint

    manifest = {
        "manifest_id": str(template.get("manifest_id", f"{atlas_hint}_{modality}_materialized_manifest")).replace(
            "public_data_manifest", "materialized_public_data_manifest"
        ),
        "atlas_name": atlas_hint,
        "modality": modality,
        "data_type": defaults["data_type"],
        "assay": str(template.get("assay", defaults["assay"])),
        "species": str(template.get("species", "human")),
        "source_name": source_name,
        "source_url": str(template.get("source_url", source_url_for_source(source_name))),
        "source_query": str(template.get("source_query", "")),
        "access_level": str(template.get("access_level", "public_or_user_exported_manifest")),
        "input_files": [dict(input_file)],
        "sample_metadata": {
            "path": str(Path(local_file_path).parent / f"{atlas_hint}_{modality}_sample_metadata_placeholder.tsv"),
            "sample_id_column": "sample_id",
        },
        "feature_metadata": {
            "path": str(Path(local_file_path).parent / f"{atlas_hint}_{modality}_feature_metadata_placeholder.tsv"),
            "feature_id_column": "feature_id",
        },
        "processing_plan": dict(template.get("processing_plan", {})),
        "expected_outputs": {
            "feature_store_dir": str(feature_store_dir),
            "normalized_matrix": str(feature_store_dir / "normalized_matrix.tsv"),
            "sample_metadata": str(feature_store_dir / "sample_metadata.tsv"),
            "feature_metadata": str(feature_store_dir / "feature_metadata.tsv"),
            "qc_summary": str(feature_store_dir / "qc_summary.tsv"),
        },
        "agent_role": {
            "stage": "materialized_public_data_manifest_stub",
            "purpose": "provide a local execution-ready manifest stub that can be switched to real public files",
        },
        "materialization_status": "placeholder_ready_replace_with_real_public_file",
    }

    manifest["input_files"][0]["path"] = str(local_file_path)
    manifest["input_files"][0]["file_format"] = str(input_file.get("file_format", "tsv"))
    manifest["input_files"][0]["matrix_orientation"] = str(input_file.get("matrix_orientation", "samples_by_features"))
    manifest["input_files"][0]["sample_id_column"] = str(input_file.get("sample_id_column", "sample_id"))
    manifest["input_files"][0]["feature_id_type"] = defaults["feature_id_type"]

    manifest["processing_plan"].update(
        {
            "normalization": defaults["normalization"],
            "missing_value_strategy": defaults["missing_value_strategy"],
            "batch_correction": str(manifest["processing_plan"].get("batch_correction", "none")),
            "feature_filtering": defaults["feature_filtering"],
            "max_missing_fraction": float(manifest["processing_plan"].get("max_missing_fraction", 0.5)),
        }
    )

    return manifest


def materialize_templates(request, template_inventory_df):
    atlas_name = str(request.get("atlas_name", "public_data_pilot"))
    local_data_root = Path(request.get("local_data_root", f"data/public/{atlas_name}"))
    policy = request.get("materialization_policy", {}) or {}
    create_placeholders = bool(policy.get("create_placeholder_files", True))
    overwrite_placeholders = bool(policy.get("overwrite_existing_placeholders", False))

    rows = []
    manifests = []
    for _, template_row in template_inventory_df.iterrows():
        template_path = Path(str(template_row["manifest_template"]))
        template = load_yaml_mapping(template_path)
        modality = str(template.get("modality", template_row.get("modality", "unknown")))
        atlas_hint = str(template.get("atlas_name", template_row.get("atlas_hint", atlas_name)))
        local_dir = ensure_dir(local_data_root / atlas_hint / modality)
        local_file_path = local_dir / f"{atlas_hint}_{modality}_public_matrix_placeholder.tsv"

        if create_placeholders and (overwrite_placeholders or not local_file_path.exists()):
            local_file_path.write_text(infer_placeholder_matrix(modality), encoding="utf-8")

        manifest_stub = build_realdata_manifest_stub(template, local_file_path, atlas_name)
        manifests.append((template_path, manifest_stub, atlas_hint, modality, local_file_path))
        rows.append(
            {
                "atlas_hint": atlas_hint,
                "modality": modality,
                "template_manifest": str(template_path),
                "local_file_path": str(local_file_path),
                "local_file_exists": int(local_file_path.exists()),
                "placeholder_created_or_present": int(local_file_path.exists()),
                "materialization_status": "placeholder_ready_replace_with_real_public_file" if local_file_path.exists() else "awaiting_user_file",
            }
        )
    return pd.DataFrame(rows), manifests


def write_materialized_manifest_stubs(manifests, output_dir):
    manifest_dir = ensure_dir(Path(output_dir) / "materialized_manifest_stubs")
    rows = []
    for template_path, manifest_stub, atlas_hint, modality, local_file_path in manifests:
        out_path = manifest_dir / f"{atlas_hint}_{modality}_materialized_public_data_manifest.yaml"
        write_yaml(out_path, manifest_stub)
        rows.append(
            {
                "atlas_hint": atlas_hint,
                "modality": modality,
                "template_manifest": str(template_path),
                "materialized_manifest_stub": str(out_path),
                "local_file_path": str(local_file_path),
            }
        )
    return pd.DataFrame(rows)


def build_html_report(request, file_requirements_df, manifest_inventory_df):
    title = "Public Data Local File Materialization Report"
    parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='utf-8'>",
        f"<title>{escape_html(title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{escape_html(title)}</h1>",
        "<p>This report converts public-data acquisition manifest templates into local file requirements and execution-ready manifest stubs.</p>",
        f"<p><strong>Request:</strong> {escape_html(request.get('request_id', ''))}</p>",
        f"<p><strong>Atlas:</strong> {escape_html(request.get('atlas_name', ''))}</p>",
        "<h2>Local file requirements</h2>",
        dataframe_to_html_table(file_requirements_df),
        "<h2>Materialized manifest stubs</h2>",
        dataframe_to_html_table(manifest_inventory_df),
        "<h2>Important next step</h2>",
        "<p>Replace placeholder local matrices with real downloaded public repository files, then run the modality feature-store processors.</p>",
        "</body>",
        "</html>",
    ]
    return "\n".join(parts)


def materialize_public_data_files(request_path=DEFAULT_MATERIALIZATION_REQUEST, output_dir=None):
    request = load_yaml_mapping(request_path)
    acquisition_summary = load_yaml_mapping(request["acquisition_summary"])
    template_inventory_df = read_table(request["manifest_template_inventory"])
    expected_outputs = request.get("expected_outputs", {})
    output_dir = ensure_dir(
        output_dir
        or expected_outputs.get(
            "materialization_dir",
            DEFAULT_OUTPUT_ROOT / request.get("atlas_name", "public_data_pilot") / "local_file_materialization",
        )
    )

    file_requirements_df, manifests = materialize_templates(request, template_inventory_df)
    manifest_inventory_df = write_materialized_manifest_stubs(manifests, output_dir)

    paths = {
        "local_file_requirements": Path(output_dir) / "local_file_requirements.tsv",
        "materialized_manifest_inventory": Path(output_dir) / "materialized_manifest_inventory.tsv",
        "materialization_summary": Path(output_dir) / "local_file_materialization_summary.yaml",
        "materialization_report": Path(output_dir) / "local_file_materialization_report.html",
    }

    file_requirements_df.to_csv(paths["local_file_requirements"], sep="\t", index=False)
    manifest_inventory_df.to_csv(paths["materialized_manifest_inventory"], sep="\t", index=False)

    summary = {
        "request_id": str(request.get("request_id", "")),
        "atlas_name": str(request.get("atlas_name", "")),
        "source_acquisition_request": str(request_path),
        "source_acquisition_summary": str(request["acquisition_summary"]),
        "requested_dataset_count": int(acquisition_summary.get("requested_dataset_count", file_requirements_df.shape[0])),
        "local_file_requirement_count": int(file_requirements_df.shape[0]),
        "materialized_manifest_stub_count": int(manifest_inventory_df.shape[0]),
        "placeholder_file_count": int(file_requirements_df["placeholder_created_or_present"].sum()) if not file_requirements_df.empty else 0,
        "output_dir": str(output_dir),
        "outputs": {key: str(path) for key, path in paths.items()},
        "agent_role": {
            "stage": "public_data_local_file_materialization",
            "purpose": "prepare local file placeholders and execution-ready manifest stubs for real public-data pilots",
        },
    }

    write_yaml(paths["materialization_summary"], summary)
    paths["materialization_report"].write_text(build_html_report(request, file_requirements_df, manifest_inventory_df), encoding="utf-8")

    return summary, file_requirements_df, manifest_inventory_df, paths


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Materialize public-data acquisition manifest templates into local file requirements and manifest stubs."
    )
    parser.add_argument("--request", type=Path, default=DEFAULT_MATERIALIZATION_REQUEST)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        summary, file_requirements_df, manifest_inventory_df, paths = materialize_public_data_files(
            request_path=args.request,
            output_dir=args.output_dir,
        )
    except Exception as exc:
        print(f"ERROR: Public data file materialization failed: {exc}", file=sys.stderr)
        return 1

    print("Public data local file materialization complete.")
    print(f"Atlas: {summary['atlas_name']}")
    print(f"Local file requirements: {summary['local_file_requirement_count']}")
    print(f"Manifest stubs: {summary['materialized_manifest_stub_count']}")
    print(f"Placeholder files: {summary['placeholder_file_count']}")
    print(f"Report: {paths['materialization_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

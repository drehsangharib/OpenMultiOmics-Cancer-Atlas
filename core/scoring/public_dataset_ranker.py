#!/usr/bin/env python3
"""
OpenMultiOmics-Cancer-Atlas
Milestone 1: Public Dataset Inventory + Relevance Ranking Engine

This script is public-data-only. It creates/ranks a cancer atlas dataset inventory.
"""

import argparse
from pathlib import Path
from datetime import datetime
import yaml
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "configs"
ATLAS_DIR = PROJECT_ROOT / "atlases"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

REQUIRED_COLUMNS = [
    "dataset_id", "repository", "title", "cancer_type", "omics_type", "organism",
    "disease", "tissue", "sample_count", "raw_data_available", "processed_data_available",
    "metadata_quality", "matched_multiomics", "species_context", "download_url",
    "publication", "notes"
]


def load_yaml(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing YAML file: {path}")
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def normalize_text(value):
    if pd.isna(value):
        return ""
    return str(value).strip()


def classify_sample_size(n):
    try:
        n = int(n)
    except Exception:
        return "unknown"
    if n >= 50:
        return "high_n_ge_50"
    if 10 <= n <= 49:
        return "medium_n_10_to_49"
    if 3 <= n <= 9:
        return "low_n_3_to_9"
    if n < 3:
        return "very_low_n_lt_3"
    return "unknown"


def classify_data_access(raw_data_available, processed_data_available):
    raw = normalize_text(raw_data_available).lower()
    processed = normalize_text(processed_data_available).lower()
    raw_yes = raw in ["yes", "true", "available", "partial"]
    processed_yes = processed in ["yes", "true", "available", "partial"]
    if raw_yes and processed_yes:
        return "both_raw_and_processed_available"
    if processed_yes:
        return "processed_matrix_available"
    if raw_yes:
        return "raw_data_available"
    if raw in ["controlled", "controlled_access"] or processed in ["controlled", "controlled_access"]:
        return "controlled_access_only"
    if raw in ["no", "false", "unavailable"] and processed in ["no", "false", "unavailable"]:
        return "unavailable"
    return "unknown"


def map_cancer_match(row_cancer_type, target_atlas):
    row_cancer = normalize_text(row_cancer_type).lower()
    target = normalize_text(target_atlas).lower()
    if target == "pan_cancer":
        return "pan_cancer"
    if row_cancer == target:
        return "exact_cancer_type"
    if target in row_cancer or row_cancer in target:
        return "related_cancer_type"
    if row_cancer in ["pan_cancer", "pancancer"]:
        return "pan_cancer"
    if row_cancer:
        return "cancer_general"
    return "none"


def map_tissue_key(tissue, target_atlas):
    t = normalize_text(tissue).lower()
    target = normalize_text(target_atlas).lower()
    if target == "gbm" and ("brain" in t or "cortex" in t or "central nervous" in t):
        return "exact_tissue"
    if "microenvironment" in t:
        return "tumor_microenvironment"
    if "cell line" in t or "cell_line" in t:
        return "cell_line"
    if t:
        return "related_tissue"
    return "unrelated"


def map_organism_key(organism):
    o = normalize_text(organism).lower()
    if "homo" in o or "human" in o or o == "homo_sapiens":
        return "Homo_sapiens"
    if "mus" in o or "mouse" in o or o == "mus_musculus":
        return "Mus_musculus"
    if "rat" in o or "rattus" in o:
        return "Rattus_norvegicus"
    return "other"


def map_omics_key(omics_type):
    o = normalize_text(omics_type).lower()
    mapping = {
        "scrnaseq": "single_cell_transcriptomics",
        "scrna-seq": "single_cell_transcriptomics",
        "single-cell rna-seq": "single_cell_transcriptomics",
        "single_cell_transcriptomics": "single_cell_transcriptomics",
        "rnaseq": "transcriptomics",
        "rna-seq": "transcriptomics",
        "bulk_rnaseq": "transcriptomics",
        "transcriptomics": "transcriptomics",
        "proteomics": "proteomics",
        "phosphoproteomics": "phosphoproteomics",
        "atacseq": "epigenomics",
        "atac-seq": "epigenomics",
        "chipseq": "epigenomics",
        "chip-seq": "epigenomics",
        "methylation": "epigenomics",
        "epigenomics": "epigenomics",
        "metabolomics": "metabolomics",
        "genomics": "genomics",
        "clinical": "clinical",
    }
    return mapping.get(o, "unknown")


def map_metadata_quality_key(metadata_quality):
    m = normalize_text(metadata_quality).lower()
    if m in ["complete_sample_metadata", "complete", "high"]:
        return "complete_sample_metadata"
    if m in ["partial_metadata", "partial", "medium"]:
        return "partial_metadata"
    if m in ["poor_metadata", "poor", "low"]:
        return "poor_metadata"
    return "unknown_metadata"


def map_multiomics_key(value):
    v = normalize_text(value).lower()
    if v in ["same_samples_multiomics", "same samples", "matched", "yes"]:
        return "same_samples_multiomics"
    if v in ["related_multiomics_not_same_samples", "related", "partial"]:
        return "related_multiomics_not_same_samples"
    if v in ["single_omics_only", "single", "no"]:
        return "single_omics_only"
    return "unknown"


def score_row(row, scoring_rules, target_atlas):
    scores = scoring_rules["dataset_relevance_scoring"]
    weights = scoring_rules.get("weights", {})
    keys = {
        "disease_match": map_cancer_match(row.get("cancer_type", ""), target_atlas),
        "tissue_match": map_tissue_key(row.get("tissue", ""), target_atlas),
        "organism_match": map_organism_key(row.get("organism", "")),
        "omics_priority": map_omics_key(row.get("omics_type", "")),
        "metadata_quality": map_metadata_quality_key(row.get("metadata_quality", "")),
        "data_access": classify_data_access(row.get("raw_data_available", ""), row.get("processed_data_available", "")),
        "sample_size": classify_sample_size(row.get("sample_count", "")),
        "matched_multiomics": map_multiomics_key(row.get("matched_multiomics", "")),
    }
    raw_scores = {name: scores[name].get(key, 0) for name, key in keys.items()}
    weighted_scores = {name: value * float(weights.get(name, 1.0)) for name, value in raw_scores.items()}
    final_score = round(sum(weighted_scores.values()), 2)
    thresholds = scoring_rules.get("rank_thresholds", {})
    if final_score >= thresholds.get("excellent", 32):
        rank_label = "excellent"
    elif final_score >= thresholds.get("high", 24):
        rank_label = "high"
    elif final_score >= thresholds.get("medium", 15):
        rank_label = "medium"
    elif final_score >= thresholds.get("low", 5):
        rank_label = "low"
    else:
        rank_label = "very_low"
    return keys, raw_scores, weighted_scores, final_score, rank_label


def validate_inventory(df):
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError("Missing required inventory columns: " + ", ".join(missing))


def generate_report(ranked_df, atlas, report_file):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rank_counts = ranked_df["rank_label"].value_counts().to_dict()
    rank_items = "\n".join([f"<li><b>{k}</b>: {v}</li>" for k, v in rank_counts.items()])
    top_html = ranked_df.head(25).to_html(index=False, escape=False)
    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>OpenMultiOmics Cancer Atlas - {atlas} v0.1</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.5; color: #222; }}
h1, h2 {{ color: #1f4e79; }}
table {{ border-collapse: collapse; width: 100%; font-size: 12px; }}
th, td {{ border: 1px solid #ccc; padding: 6px; text-align: left; vertical-align: top; }}
th {{ background-color: #e8f1fa; }}
.box {{ border: 1px solid #ccc; padding: 16px; border-radius: 8px; background-color: #fafafa; }}
</style>
</head>
<body>
<h1>OpenMultiOmics-Cancer-Atlas: {atlas.upper()} Public Dataset Ranking Report</h1>
<div class="box">
<p><b>Generated:</b> {now}</p>
<p><b>Atlas:</b> {atlas}</p>
<p><b>Total datasets:</b> {len(ranked_df)}</p>
</div>
<h2>Rank Summary</h2>
<ul>{rank_items}</ul>
<h2>Top Ranked Datasets</h2>
{top_html}
<h2>Governance Note</h2>
<p>This report is generated from public or placeholder dataset inventory only. Do not commit unpublished/private datasets.</p>
</body>
</html>
"""
    report_file.write_text(html, encoding="utf-8")


def run(atlas):
    scoring_rules = load_yaml(CONFIG_DIR / "scoring_rules_general.yaml")
    _database_registry = load_yaml(CONFIG_DIR / "database_registry.yaml")
    _cancer_registry = load_yaml(CONFIG_DIR / "cancer_type_registry.yaml")
    _species_rules = load_yaml(CONFIG_DIR / "species_mapping_rules.yaml")

    atlas_path = ATLAS_DIR / atlas
    if not atlas_path.exists():
        raise FileNotFoundError(f"Unknown atlas directory: {atlas_path}")

    inventory_file = atlas_path / f"{atlas}_dataset_inventory.tsv"
    if not inventory_file.exists():
        raise FileNotFoundError(f"Missing inventory file: {inventory_file}")

    df = pd.read_csv(inventory_file, sep="\t")
    validate_inventory(df)

    rows = []
    for _, row in df.iterrows():
        keys, raw_scores, weighted_scores, final_score, rank_label = score_row(row, scoring_rules, atlas)
        out = row.to_dict()
        out.update({f"mapped_{k}": v for k, v in keys.items()})
        out.update({f"raw_score_{k}": v for k, v in raw_scores.items()})
        out.update({f"weighted_score_{k}": round(v, 2) for k, v in weighted_scores.items()})
        out["relevance_score"] = final_score
        out["rank_label"] = rank_label
        rows.append(out)

    ranked_df = pd.DataFrame(rows).sort_values(["relevance_score", "sample_count"], ascending=[False, False])

    (OUTPUT_DIR / "dataset_inventory").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "ranked_datasets").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "reports").mkdir(parents=True, exist_ok=True)

    copied_inventory = OUTPUT_DIR / "dataset_inventory" / "public_dataset_inventory.tsv"
    ranked_file = OUTPUT_DIR / "ranked_datasets" / f"ranked_{atlas}_public_datasets.tsv"
    report_file = OUTPUT_DIR / "reports" / f"OpenMultiOmics_Cancer_Atlas_{atlas.upper()}_v0.1_report.html"

    df.to_csv(copied_inventory, sep="\t", index=False)
    ranked_df.to_csv(ranked_file, sep="\t", index=False)
    generate_report(ranked_df, atlas, report_file)

    print("Milestone 1 complete.")
    print(f"Inventory: {copied_inventory}")
    print(f"Ranked datasets: {ranked_file}")
    print(f"Report: {report_file}")


def main():
    parser = argparse.ArgumentParser(description="Rank public datasets for an OpenMultiOmics cancer atlas module.")
    parser.add_argument("--atlas", default="gbm", help="Atlas module name, e.g. gbm or pan_cancer")
    args = parser.parse_args()
    run(args.atlas)


if __name__ == "__main__":
    main()

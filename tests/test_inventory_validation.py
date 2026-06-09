from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_gbm_inventory_has_required_columns():
    path = ROOT / "atlases" / "gbm" / "gbm_dataset_inventory.tsv"
    df = pd.read_csv(path, sep="\t")
    required = [
        "dataset_id", "repository", "title", "cancer_type", "omics_type", "organism",
        "disease", "tissue", "sample_count", "raw_data_available", "processed_data_available",
        "metadata_quality", "matched_multiomics", "species_context", "download_url",
        "publication", "notes"
    ]
    for col in required:
        assert col in df.columns

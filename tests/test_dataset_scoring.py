from core.scoring.public_dataset_ranker import classify_sample_size, classify_data_access, map_omics_key


def test_sample_size_classifier():
    assert classify_sample_size(50) == "high_n_ge_50"
    assert classify_sample_size(12) == "medium_n_10_to_49"
    assert classify_sample_size(5) == "low_n_3_to_9"


def test_data_access_classifier():
    assert classify_data_access("yes", "yes") == "both_raw_and_processed_available"
    assert classify_data_access("no", "yes") == "processed_matrix_available"
    assert classify_data_access("yes", "no") == "raw_data_available"


def test_omics_mapping():
    assert map_omics_key("RNA-seq") == "transcriptomics"
    assert map_omics_key("scRNA-seq") == "single_cell_transcriptomics"
    assert map_omics_key("ATAC-seq") == "epigenomics"

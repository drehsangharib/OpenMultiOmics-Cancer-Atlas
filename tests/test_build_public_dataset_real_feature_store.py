from pathlib import Path
import pandas as pd
import yaml
from core.data.build_public_dataset_real_feature_store import build_arg_parser, build_public_dataset_real_feature_store


def test_build_public_dataset_real_feature_store(tmp_path: Path):
    matrix = tmp_path / "brca.tsv"
    matrix.write_text("gene_id\tS1\tS2\nENSG1\t0\t3\nENSG2\t7\t1\n", encoding="utf-8")
    locked = tmp_path / "locked.tsv"
    corrected = tmp_path / "corrected.tsv"
    pilot_summary = tmp_path / "summary.yaml"
    request = tmp_path / "request.yaml"
    out = tmp_path / "feature_store"
    pd.DataFrame([{"dataset_id":"tcga_brca_transcriptomics","modality":"transcriptomics","target_local_path":str(matrix),"validation_passed":1,"activation_ready":1,"feature_store_handoff_ready":1}]).to_csv(locked, sep="\t", index=False)
    pd.DataFrame([{"dataset_id":"tcga_brca_transcriptomics","blocking_reason":"none"}]).to_csv(corrected, sep="\t", index=False)
    with pilot_summary.open("w", encoding="utf-8") as h:
        yaml.safe_dump({"request_id":"upstream_a37"}, h, sort_keys=False)
    with request.open("w", encoding="utf-8") as h:
        yaml.safe_dump({"request_id":"test_feature_store","atlas_name":"test_public","inputs":{"locked_real_data_pilot":str(locked),"corrected_smoke_test_state":str(corrected),"pilot_lock_summary":str(pilot_summary)},"expected_outputs":{"real_feature_store_dir":str(out)}}, h, sort_keys=False)
    summary, feature_df, gene_df, sample_df, manifest, paths = build_public_dataset_real_feature_store(request_path=request)
    assert paths["ai_ready_feature_matrix"].exists()
    assert paths["gene_summary"].exists()
    assert paths["sample_summary"].exists()
    assert paths["feature_store_manifest"].exists()
    assert paths["feature_store_summary"].exists()
    assert paths["feature_store_report"].exists()
    assert summary["dataset_id"] == "tcga_brca_transcriptomics"
    assert summary["feature_count"] == 2
    assert summary["sample_count"] == 2
    assert manifest["ready_for_ai_model_input"] is True
    assert not feature_df.empty
    assert not gene_df.empty
    assert not sample_df.empty


def test_missing_optional_pilot_lock_summary_does_not_resolve_to_current_directory(tmp_path: Path):
    matrix = tmp_path / "brca.tsv"
    matrix.write_text("gene_id\tS1\nENSG1\t3\n", encoding="utf-8")
    locked = tmp_path / "locked.tsv"
    request = tmp_path / "request.yaml"
    out = tmp_path / "feature_store"
    pd.DataFrame([{"dataset_id":"tcga_brca_transcriptomics","modality":"transcriptomics","target_local_path":str(matrix),"validation_passed":1,"activation_ready":1,"feature_store_handoff_ready":1}]).to_csv(locked, sep="\t", index=False)
    with request.open("w", encoding="utf-8") as h:
        yaml.safe_dump({"request_id":"test_missing_optional_summary","atlas_name":"test_public","inputs":{"locked_real_data_pilot":str(locked),"pilot_lock_summary":""},"expected_outputs":{"real_feature_store_dir":str(out)}}, h, sort_keys=False)
    summary, feature_df, gene_df, sample_df, manifest, paths = build_public_dataset_real_feature_store(request_path=request)
    assert summary["upstream_pilot_lock_request_id"] == ""
    assert paths["feature_store_summary"].exists()


def test_blank_locked_metadata_uses_known_brca_fallback(tmp_path: Path):
    matrix = tmp_path / "REPLACE_WITH_TCGA_BRCA_TRANSCRIPTOMICS.tsv"
    matrix.write_text("gene_id\tS1\nENSG1\t3\n", encoding="utf-8")
    locked = tmp_path / "locked.tsv"
    corrected = tmp_path / "corrected.tsv"
    request = tmp_path / "request.yaml"
    out = tmp_path / "feature_store"
    pd.DataFrame([{"dataset_id":"tcga_brca_transcriptomics","modality":"","target_local_path":"","validation_passed":1,"activation_ready":1,"feature_store_handoff_ready":1}]).to_csv(locked, sep="\t", index=False)
    pd.DataFrame([{"dataset_id":"tcga_brca_transcriptomics","modality":"","target_local_path":"","blocking_reason":"none"}]).to_csv(corrected, sep="\t", index=False)
    with request.open("w", encoding="utf-8") as h:
        yaml.safe_dump({
            "request_id":"test_blank_metadata_fallback",
            "atlas_name":"test_public",
            "inputs":{"locked_real_data_pilot":str(locked),"corrected_smoke_test_state":str(corrected),"pilot_lock_summary":""},
            "expected_outputs":{"real_feature_store_dir":str(out)},
            "feature_store_policy":{
                "known_real_matrix_paths":{"tcga_brca_transcriptomics":str(matrix)},
                "known_modalities":{"tcga_brca_transcriptomics":"transcriptomics"},
                "fallback_known_real_matrix_paths":True,
            },
        }, h, sort_keys=False)
    summary, feature_df, gene_df, sample_df, manifest, paths = build_public_dataset_real_feature_store(request_path=request)
    assert summary["dataset_id"] == "tcga_brca_transcriptomics"
    assert summary["modality"] == "transcriptomics"
    assert summary["metadata_resolution_used_known_fallback"] == 1
    assert summary["sample_count"] == 1
    assert paths["ai_ready_feature_matrix"].exists()


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--request", "request.yaml", "--output-dir", "out"])
    assert str(args.request).endswith("request.yaml")
    assert str(args.output_dir).endswith("out")

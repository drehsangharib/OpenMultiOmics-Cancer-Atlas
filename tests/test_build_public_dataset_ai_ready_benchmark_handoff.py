from pathlib import Path
import pandas as pd
import yaml
from core.data.build_public_dataset_ai_ready_benchmark_handoff import build_arg_parser, build_public_dataset_ai_ready_benchmark_handoff


def test_build_public_dataset_ai_ready_benchmark_handoff(tmp_path: Path):
    feature_matrix = tmp_path / "feature_matrix.tsv"
    feature_matrix.write_text("feature_id\tS1\tS2\tS3\tS4\nF1\t0\t1\t2\t3\nF2\t5\t5\t5\t5\nF3\t0\t10\t0\t10\n", encoding="utf-8")
    sample_summary = tmp_path / "sample_summary.tsv"
    gene_summary = tmp_path / "gene_summary.tsv"
    pd.DataFrame([{"sample_id":"S1"}]).to_csv(sample_summary, sep="\t", index=False)
    pd.DataFrame([{"feature_id":"F1"}]).to_csv(gene_summary, sep="\t", index=False)
    fs_manifest = tmp_path / "feature_store_manifest.yaml"
    write_manifest = {
        "dataset_id":"tcga_brca_transcriptomics",
        "modality":"transcriptomics",
        "ai_ready_feature_matrix":str(feature_matrix),
        "sample_summary":str(sample_summary),
        "gene_summary":str(gene_summary),
        "ready_for_ai_model_input":True,
    }
    with fs_manifest.open("w", encoding="utf-8") as h:
        yaml.safe_dump(write_manifest, h, sort_keys=False)
    request = tmp_path / "request.yaml"
    out = tmp_path / "handoff"
    with request.open("w", encoding="utf-8") as h:
        yaml.safe_dump({"request_id":"test_handoff","atlas_name":"test_public","inputs":{"feature_store_manifest":str(fs_manifest)},"expected_outputs":{"ai_ready_benchmark_handoff_dir":str(out)},"handoff_policy":{"top_variable_features":2,"split_seed":7}}, h, sort_keys=False)
    summary, model_input, feature_selection, split_df, manifest, paths = build_public_dataset_ai_ready_benchmark_handoff(request_path=request)
    assert paths["model_input_matrix"].exists()
    assert paths["feature_selection_table"].exists()
    assert paths["sample_split_manifest"].exists()
    assert paths["model_handoff_manifest"].exists()
    assert paths["ai_ready_benchmark_summary"].exists()
    assert paths["ai_ready_benchmark_report"].exists()
    assert summary["sample_count"] == 4
    assert summary["input_feature_count"] == 3
    assert summary["selected_feature_count"] == 2
    assert manifest["ready_for_baseline_modeling"] is True
    assert model_input.shape[0] == 4
    assert not split_df.empty


def test_build_arg_parser():
    parser = build_arg_parser()
    args = parser.parse_args(["--request", "request.yaml", "--output-dir", "out"])
    assert str(args.request).endswith("request.yaml")
    assert str(args.output_dir).endswith("out")

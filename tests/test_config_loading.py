from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_required_configs_load():
    required = [
        "database_registry.yaml",
        "scoring_rules_general.yaml",
        "cancer_type_registry.yaml",
        "omics_modality_registry.yaml",
        "species_mapping_rules.yaml",
    ]
    for name in required:
        path = ROOT / "configs" / name
        assert path.exists(), f"Missing config: {path}"
        with open(path, "r", encoding="utf-8") as handle:
            assert yaml.safe_load(handle) is not None

param([string]$RepoRoot = "D:\AI project\OpenMultiOmics-Cancer-Atlas")
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
cd $RepoRoot
python -m py_compile core\data\build_public_dataset_first_real_pilot_activation.py
python -m py_compile tests\test_build_public_dataset_first_real_pilot_activation.py
python -m pytest tests\test_build_public_dataset_first_real_pilot_activation.py -q
python -m pytest -q
python -m core.data.build_public_dataset_first_real_pilot_activation

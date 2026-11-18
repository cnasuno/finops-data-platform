import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from quality import evaluate_quality


def test_quality_pass():
    results = {
        "invalid_amount": 0,
        "null_values": 0,
        "duplicate_ids": 0,
        "invalid_fk": 0,
        "pipeline_count_mismatch": 0
    }

    assert evaluate_quality(results) == "PASS"


def test_quality_fail():
    results = {
        "invalid_amount": 0,
        "null_values": 0,
        "duplicate_ids": 0,
        "invalid_fk": 0,
        "pipeline_count_mismatch": 1
    }

    assert evaluate_quality(results) == "FAIL"


def test_quality_multiple_failures():
    results = {
        "invalid_amount": 3,
        "null_values": 2,
        "duplicate_ids": 0,
        "invalid_fk": 1,
        "pipeline_count_mismatch": 0
    }

    assert evaluate_quality(results) == "FAIL"

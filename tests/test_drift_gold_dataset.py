"""Drift gold dataset tests — validates gold dataset structure and quality metrics."""
import json
import pytest
from pathlib import Path
from tools.check_drift_quality import (
    DriftQualityMetrics,
    evaluate_case,
    compute_metrics,
    check_thresholds,
)


def test_gold_dataset_exists():
    """Gold dataset directory and manifest should exist."""
    gold_dir = Path("tests/fixtures/drift_gold")
    assert gold_dir.exists()
    assert (gold_dir / "gold_manifest.json").exists()


def test_gold_dataset_has_cases():
    """Gold dataset should have at least 5 cases."""
    manifest = json.loads(Path("tests/fixtures/drift_gold/gold_manifest.json").read_text())
    assert manifest["case_count"] >= 5
    assert manifest["positive_cases"] >= 3
    assert manifest["negative_cases"] >= 1


def test_gold_case_structure():
    """Each gold case should have required files."""
    gold_dir = Path("tests/fixtures/drift_gold")
    manifest = json.loads((gold_dir / "gold_manifest.json").read_text())
    for case in manifest["cases"]:
        case_dir = gold_dir / "cases" / case["case_id"]
        assert (case_dir / "input_summary.json").exists()
        assert (case_dir / "canon_anchor.json").exists()
        assert (case_dir / "expected.json").exists()


def test_evaluate_case_tp():
    assert evaluate_case(True, True) == "tp"


def test_evaluate_case_fp():
    assert evaluate_case(True, False) == "fp"


def test_evaluate_case_tn():
    assert evaluate_case(False, False) == "tn"


def test_evaluate_case_fn():
    assert evaluate_case(False, True) == "fn"


def test_metrics_perfect():
    results = ["tp", "tp", "tn", "tn"]
    m = compute_metrics(results)
    assert m.precision == 1.0
    assert m.recall == 1.0
    assert m.f1 == 1.0


def test_metrics_with_fp():
    results = ["tp", "fp", "tn"]
    m = compute_metrics(results)
    assert m.precision == 0.5
    assert m.false_positive_rate == 0.5


def test_thresholds_pass():
    m = DriftQualityMetrics(true_positive=8, false_positive=1, true_negative=8, false_negative=2)
    failures = check_thresholds(m)
    assert len(failures) == 0


def test_thresholds_fail_precision():
    m = DriftQualityMetrics(true_positive=2, false_positive=8, true_negative=5, false_negative=0)
    failures = check_thresholds(m)
    assert any("precision" in f for f in failures)

"""Drift Quality Checker — validates drift detection against gold dataset.

Computes precision, recall, false positive rate, and F1 score.
"""
import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DriftQualityMetrics:
    """Drift detection quality metrics."""
    true_positive: int = 0
    false_positive: int = 0
    true_negative: int = 0
    false_negative: int = 0

    @property
    def precision(self) -> float:
        denom = self.true_positive + self.false_positive
        return self.true_positive / denom if denom > 0 else 0.0

    @property
    def recall(self) -> float:
        denom = self.true_positive + self.false_negative
        return self.true_positive / denom if denom > 0 else 0.0

    @property
    def false_positive_rate(self) -> float:
        denom = self.false_positive + self.true_negative
        return self.false_positive / denom if denom > 0 else 0.0

    @property
    def f1(self) -> float:
        denom = self.precision + self.recall
        return 2 * self.precision * self.recall / denom if denom > 0 else 0.0


# Default thresholds from TEMP.md
THRESHOLDS = {
    "precision_min": 0.80,
    "recall_min": 0.70,
    "false_positive_rate_max": 0.20,
    "f1_min": 0.75,
}


def evaluate_case(predicted_positive: bool, expected_positive: bool) -> str:
    """Classify a prediction vs expected result."""
    if predicted_positive and expected_positive:
        return "tp"
    elif predicted_positive and not expected_positive:
        return "fp"
    elif not predicted_positive and not expected_positive:
        return "tn"
    else:
        return "fn"


def compute_metrics(results: list[str]) -> DriftQualityMetrics:
    """Compute metrics from a list of classification results."""
    m = DriftQualityMetrics()
    for r in results:
        if r == "tp":
            m.true_positive += 1
        elif r == "fp":
            m.false_positive += 1
        elif r == "tn":
            m.true_negative += 1
        elif r == "fn":
            m.false_negative += 1
    return m


def check_thresholds(metrics: DriftQualityMetrics) -> list[str]:
    """Check metrics against thresholds. Returns list of failures."""
    failures = []
    if metrics.precision < THRESHOLDS["precision_min"]:
        failures.append(f"precision={metrics.precision:.2f} < {THRESHOLDS['precision_min']}")
    if metrics.recall < THRESHOLDS["recall_min"]:
        failures.append(f"recall={metrics.recall:.2f} < {THRESHOLDS['recall_min']}")
    if metrics.false_positive_rate > THRESHOLDS["false_positive_rate_max"]:
        failures.append(f"fpr={metrics.false_positive_rate:.2f} > {THRESHOLDS['false_positive_rate_max']}")
    if metrics.f1 < THRESHOLDS["f1_min"]:
        failures.append(f"f1={metrics.f1:.2f} < {THRESHOLDS['f1_min']}")
    return failures


def main():
    parser = argparse.ArgumentParser(description="Drift Quality Checker")
    parser.add_argument("--gold-dir", default="tests/fixtures/drift_gold")
    parser.add_argument("--results-json", required=True, help="JSON file with predictions")
    args = parser.parse_args()

    gold_dir = Path(args.gold_dir)
    results = json.loads(Path(args.results_json).read_text())

    classifications = []
    for r in results:
        cls = evaluate_case(r["predicted_positive"], r["expected_positive"])
        classifications.append(cls)

    metrics = compute_metrics(classifications)
    failures = check_thresholds(metrics)

    output = {
        "schema_version": "DRIFT_QUALITY_REPORT_V1",
        "case_count": len(results),
        "metrics": {
            "true_positive": metrics.true_positive,
            "false_positive": metrics.false_positive,
            "true_negative": metrics.true_negative,
            "false_negative": metrics.false_negative,
            "precision": round(metrics.precision, 3),
            "recall": round(metrics.recall, 3),
            "false_positive_rate": round(metrics.false_positive_rate, 3),
            "f1": round(metrics.f1, 3),
        },
        "thresholds": THRESHOLDS,
        "status": "pass" if not failures else "fail",
        "failures": failures,
    }

    print(json.dumps(output, indent=2))
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    main()

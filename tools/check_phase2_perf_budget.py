"""Phase 2 Performance Hard Gate checker.

Checks context sizes against hard limits from TEMP.md Patch 7.10.
"""
import argparse
import json
import sys
from dataclasses import dataclass


# Hard limits from TEMP.md Patch 7.10 (30 chapters)
HARD_LIMITS = {
    "writer_context_chars": 35000,
    "auditor_context_chars": 40000,
    "extractor_context_chars": 12000,
}


@dataclass
class PerfCheckResult:
    metric: str
    actual: int
    limit: int
    status: str  # "pass" or "fail"


def check_context_budget(context_chars: int, role: str) -> PerfCheckResult:
    """Check if context size exceeds hard limit for a role."""
    key = f"{role}_context_chars"
    limit = HARD_LIMITS.get(key, 12000)
    status = "pass" if context_chars <= limit else "fail"
    return PerfCheckResult(metric=key, actual=context_chars, limit=limit, status=status)


def main():
    parser = argparse.ArgumentParser(description="Phase 2 Performance Hard Gate")
    parser.add_argument("--writer-chars", type=int, default=0)
    parser.add_argument("--auditor-chars", type=int, default=0)
    parser.add_argument("--extractor-chars", type=int, default=0)
    parser.add_argument("--output", default=None, help="Output JSON path")
    args = parser.parse_args()

    results = [
        check_context_budget(args.writer_chars, "writer"),
        check_context_budget(args.auditor_chars, "auditor"),
        check_context_budget(args.extractor_chars, "extractor"),
    ]

    all_pass = all(r.status == "pass" for r in results)
    output = {
        "schema_version": "PERF_HARD_GATE_V1",
        "status": "pass" if all_pass else "fail",
        "checks": [
            {"metric": r.metric, "actual": r.actual, "limit": r.limit, "status": r.status}
            for r in results
        ],
    }

    if args.output:
        from pathlib import Path
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print(json.dumps(output, indent=2))
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()

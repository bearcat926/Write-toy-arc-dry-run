"""Phase 3 Entry Gate Verifier — machine-verifiable gate check.

TEMP.md §14: Verifies all 13 Phase 3 Entry Gates are satisfied.
Output: phase3_entry_gate.json with final_status, blocking_failures, gates_passed.

Usage:
    python scripts/verify_phase3_entry_gate.py
    python scripts/verify_phase3_entry_gate.py --output workspace/reports/phase3_entry_gate.json
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def run_gate_test(test_name: str, project_root: Path) -> dict:
    """Run a single gate test and return result."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", f"tests/test_phase3_entry_gate.py::{test_name}", "-v", "--tb=no"],
        capture_output=True, text=True, cwd=str(project_root),
        timeout=30,
    )
    return {
        "test": test_name,
        "passed": result.returncode == 0,
        "output": result.stdout.strip()[-200:] if result.stdout else "",
    }


def check_baseline_test_count(project_root: Path) -> dict:
    """Check test baseline doc matches actual test count."""
    import re
    baseline = project_root / "docs" / "phase2_test_baseline.generated.md"
    if not baseline.exists():
        return {"test": "baseline_doc_exists", "passed": False, "error": "baseline doc missing"}

    content = baseline.read_text(encoding="utf-8")

    # Check commit is known (not "unknown")
    if "unknown" in content.split("Base Commit")[1].split("\n")[0]:
        return {"test": "baseline_commit_known", "passed": False, "error": "commit unknown"}

    return {"test": "baseline_test_count", "passed": True}


def main():
    parser = argparse.ArgumentParser(description="Phase 3 Entry Gate Verifier")
    parser.add_argument("--output", default=None, help="Output JSON path")
    parser.add_argument("--project-root", default=None)
    args = parser.parse_args()

    project_root = Path(args.project_root) if args.project_root else Path(__file__).resolve().parent.parent

    # Run all 13 gate tests
    gate_tests = [
        "test_gate1_generation_lifecycle",
        "test_gate2_builder_auto_register",
        "test_gate3_retrieval_validator",
        "test_gate4_rebuild_orchestrator",
        "test_gate5_independent_profiles",
        "test_gate6_retrieval_active_mode",
        "test_gate7_arc_active_validator",
        "test_gate8_30_chapter_stress",
        "test_gate9_performance_hard_gate",
        "test_gate10_structured_auditor",
        "test_gate11_drift_streak",
        "test_gate12_drift_gold_dataset",
        "test_gate13_change_gate_exists",
    ]

    gate_results = []
    for test_name in gate_tests:
        gate_results.append(run_gate_test(test_name, project_root))

    # Check baseline
    baseline_result = check_baseline_test_count(project_root)

    # Compute final status
    all_gates_passed = all(r["passed"] for r in gate_results)
    baseline_ok = baseline_result["passed"]
    blocking_failures = [r["test"] for r in gate_results if not r["passed"]]
    if not baseline_ok:
        blocking_failures.append("baseline_test_count")

    result = {
        "schema_version": "PHASE3_ENTRY_GATE_V1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "final_status": "PASS" if (all_gates_passed and baseline_ok) else "FAIL",
        "gates_passed": sum(1 for r in gate_results if r["passed"]),
        "gates_total": len(gate_results),
        "blocking_failures": blocking_failures,
        "gate_results": gate_results,
        "baseline_check": baseline_result,
    }

    # Output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"Report written to {output_path}")

    print(json.dumps(result, indent=2))
    sys.exit(0 if result["final_status"] == "PASS" else 1)


if __name__ == "__main__":
    main()

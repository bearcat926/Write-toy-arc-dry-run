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
    """Check test baseline doc matches actual JUnit test count and commit binding."""
    import re
    import xml.etree.ElementTree as ET

    baseline = project_root / "docs" / "phase2_test_baseline.generated.md"
    if not baseline.exists():
        return {"test": "baseline_doc_exists", "passed": False, "error": "baseline doc missing"}

    content = baseline.read_text(encoding="utf-8")

    # Parse baseline commit (format: **Base Commit:** HASH)
    commit_line = content.split("Base Commit")[1].split("\n")[0]
    baseline_commit = commit_line.split(":")[-1].strip().strip("*").strip()
    if not baseline_commit or "unknown" in baseline_commit:
        return {"test": "baseline_commit_known", "passed": False, "error": f"commit unknown: {baseline_commit}"}

    # Parse baseline counts
    baseline_counts = {}
    for metric in ("Total", "Passed", "Failed", "Errors", "Skipped"):
        match = re.search(rf"\|\s*{metric}\s*\|\s*(\d+)\s*\|", content)
        if match:
            baseline_counts[metric.lower()] = int(match.group(1))

    # Parse JUnit XML
    junit_path = project_root / "report.xml"
    if not junit_path.exists():
        return {"test": "junit_exists", "passed": False, "error": "report.xml missing"}

    try:
        tree = ET.parse(junit_path)
        root_elem = tree.getroot()
        if root_elem.tag == "testsuites":
            suites = root_elem.findall("testsuite")
        elif root_elem.tag == "testsuite":
            suites = [root_elem]
        else:
            return {"test": "junit_parse", "passed": False, "error": f"unexpected root: {root_elem.tag}"}

        junit_total = sum(int(s.get("tests", 0)) for s in suites)
        junit_failures = sum(int(s.get("failures", 0)) for s in suites)
        junit_errors = sum(int(s.get("errors", 0)) for s in suites)
        junit_skipped = sum(int(s.get("skipped", 0)) for s in suites)
        junit_passed = junit_total - junit_failures - junit_errors - junit_skipped
    except Exception as e:
        return {"test": "junit_parse", "passed": False, "error": str(e)}

    # Verify counts match
    errors = []
    if baseline_counts.get("total") != junit_total:
        errors.append(f"total mismatch: baseline={baseline_counts.get('total')} junit={junit_total}")
    if baseline_counts.get("passed") != junit_passed:
        errors.append(f"passed mismatch: baseline={baseline_counts.get('passed')} junit={junit_passed}")
    if junit_failures != 0:
        errors.append(f"junit has {junit_failures} failures")
    if junit_errors != 0:
        errors.append(f"junit has {junit_errors} errors")

    # Verify baseline commit is reachable from HEAD (ancestor check)
    # Note: baseline commit may differ from HEAD because baseline regeneration
    # itself creates a new commit. We verify the baseline commit is a valid
    # ancestor of HEAD within the recent history.
    try:
        ancestor_result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", baseline_commit, "HEAD"],
            cwd=str(project_root), capture_output=True, text=True, timeout=5,
        )
        if ancestor_result.returncode != 0:
            errors.append(f"baseline commit {baseline_commit} is not an ancestor of HEAD")
    except Exception:
        pass  # non-fatal

    if errors:
        return {"test": "baseline_verification", "passed": False, "errors": errors}

    return {
        "test": "baseline_verification",
        "passed": True,
        "baseline_commit": baseline_commit,
        "junit_total": junit_total,
        "junit_passed": junit_passed,
    }


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

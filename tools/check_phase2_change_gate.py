"""Phase 2 Change Gate machine check script.

Usage:
    python tools/check_phase2_change_gate.py --target-change milestone0
    python tools/check_phase2_change_gate.py --target-change change1
"""
import argparse
import json
import sys
from pathlib import Path


def check_milestone0(project_root: Path) -> list[str]:
    """Check Milestone 0 exit gates."""
    failures = []
    baseline = project_root / "docs" / "phase2_test_baseline.generated.md"
    if not baseline.exists():
        failures.append("docs/phase2_test_baseline.generated.md missing")
    return failures


def check_change1(project_root: Path) -> list[str]:
    """Check Change 1 exit gates."""
    failures = []
    # Registry tests exist
    registry_test = project_root / "tests" / "test_phase2_artifact_registry.py"
    if not registry_test.exists():
        failures.append("tests/test_phase2_artifact_registry.py missing")
    # Retrieval schema tests exist
    schema_test = project_root / "tests" / "test_phase2_retrieval_schema.py"
    if not schema_test.exists():
        failures.append("tests/test_phase2_retrieval_schema.py missing")
    # ContextProvider exists
    provider = project_root / "src" / "novel_workflow" / "system_scripts" / "context_provider.py"
    if not provider.exists():
        failures.append("context_provider.py missing")
    # Trace write test exists
    trace_test = project_root / "tests" / "test_phase2_retrieval_trace_write.py"
    if not trace_test.exists():
        failures.append("tests/test_phase2_retrieval_trace_write.py missing")
    return failures


def check_change2(project_root: Path) -> list[str]:
    """Check Change 2 entry gates."""
    failures = []
    # Change 1 gates must pass first
    failures.extend([f"[change1] {f}" for f in check_change1(project_root)])
    # Manifest schema exists
    manifest_schema = project_root / "src" / "novel_workflow" / "schemas" / "manifest.py"
    if not manifest_schema.exists():
        failures.append("schemas/manifest.py missing")
    # Manifest schema test exists
    manifest_test = project_root / "tests" / "test_phase2_manifest_schema.py"
    if not manifest_test.exists():
        failures.append("tests/test_phase2_manifest_schema.py missing")
    # failure_isolation config test exists
    fi_test = project_root / "tests" / "test_phase2_failure_isolation_config.py"
    if not fi_test.exists():
        failures.append("tests/test_phase2_failure_isolation_config.py missing")
    # failure_isolation config exists
    config_path = project_root / "src" / "novel_workflow" / "config.py"
    if config_path.exists():
        content = config_path.read_text()
        if "FAILURE_ISOLATION_DEFAULTS" not in content:
            failures.append("FAILURE_ISOLATION_DEFAULTS not in config.py")
    else:
        failures.append("config.py missing")
    return failures


def main():
    parser = argparse.ArgumentParser(description="Phase 2 Change Gate check")
    parser.add_argument("--target-change", required=True,
                        choices=["milestone0", "change1", "change2"])
    parser.add_argument("--project-root", default=None)
    args = parser.parse_args()

    project_root = Path(args.project_root) if args.project_root else Path.cwd()

    checkers = {
        "milestone0": check_milestone0,
        "change1": check_change1,
        "change2": check_change2,
    }

    failures = checkers[args.target_change](project_root)
    result = {
        "target_change": args.target_change,
        "status": "pass" if not failures else "fail",
        "failed_gates": failures,
        "project_root": str(project_root),
    }
    print(json.dumps(result, indent=2))
    sys.exit(0 if not failures else 1)


if __name__ == "__main__":
    main()

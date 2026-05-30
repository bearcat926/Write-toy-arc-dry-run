"""Phase 2 Change Gate script tests."""
import json
import subprocess
import sys
from pathlib import Path


def test_change_gate_milestone0_pass(project_root: Path):
    """milestone0 should pass when baseline doc exists."""
    docs_dir = project_root / "docs"
    docs_dir.mkdir(exist_ok=True)
    baseline = docs_dir / "phase2_test_baseline.generated.md"
    baseline.write_text("# baseline")
    result = subprocess.run(
        [sys.executable, "tools/check_phase2_change_gate.py",
         "--target-change", "milestone0", "--project-root", str(project_root)],
        capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    assert data["status"] == "pass"


def test_change_gate_milestone0_fail(project_root: Path):
    """milestone0 should fail when baseline doc missing."""
    result = subprocess.run(
        [sys.executable, "tools/check_phase2_change_gate.py",
         "--target-change", "milestone0", "--project-root", str(project_root)],
        capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    assert data["status"] == "fail"


def test_change_gate_change1_pass(project_root: Path):
    """change1 should pass when all required files exist."""
    # Create required files
    tests_dir = project_root / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "test_phase2_artifact_registry.py").write_text("# test")
    (tests_dir / "test_phase2_retrieval_schema.py").write_text("# test")
    (tests_dir / "test_phase2_retrieval_trace_write.py").write_text("# test")
    src_dir = project_root / "src" / "novel_workflow" / "system_scripts"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "context_provider.py").write_text("# cp")
    result = subprocess.run(
        [sys.executable, "tools/check_phase2_change_gate.py",
         "--target-change", "change1", "--project-root", str(project_root)],
        capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    assert data["status"] == "pass"

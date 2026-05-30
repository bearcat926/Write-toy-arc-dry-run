"""Performance hard gate tests."""
import subprocess
import sys
import json
import pytest
from pathlib import Path
from tools.check_phase2_perf_budget import check_context_budget


def test_within_limits():
    result = check_context_budget(10000, "writer")
    assert result.status == "pass"


def test_exceeds_writer_limit():
    result = check_context_budget(40000, "writer")
    assert result.status == "fail"


def test_exceeds_auditor_limit():
    result = check_context_budget(50000, "auditor")
    assert result.status == "fail"


def test_extractor_within_limit():
    result = check_context_budget(12000, "extractor")
    assert result.status == "pass"


def test_cli_pass(tmp_path: Path):
    result = subprocess.run(
        [sys.executable, "tools/check_phase2_perf_budget.py",
         "--writer-chars", "10000", "--auditor-chars", "10000", "--extractor-chars", "5000"],
        capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    assert data["status"] == "pass"


def test_cli_fail(tmp_path: Path):
    result = subprocess.run(
        [sys.executable, "tools/check_phase2_perf_budget.py",
         "--writer-chars", "50000", "--auditor-chars", "10000", "--extractor-chars", "5000"],
        capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    assert data["status"] == "fail"

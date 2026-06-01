import subprocess
import sys

import pytest

from tools import verify_test_baseline


def test_resolve_base_commit_uses_explicit_value_without_git(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("git should not be called for explicit commits")

    monkeypatch.setattr(subprocess, "run", fail_if_called)

    assert verify_test_baseline.resolve_base_commit(
        "abc1234", verify_test_baseline.project_root()
    ) == "abc1234"


def test_resolve_base_commit_defaults_to_git_head(monkeypatch, tmp_path):
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, stdout="3723c00\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert verify_test_baseline.resolve_base_commit(None, tmp_path) == "3723c00"
    assert calls[0][0] == ["git", "rev-parse", "--short", "HEAD"]
    assert calls[0][1]["cwd"] == tmp_path


def test_resolve_base_commit_fails_when_git_head_unavailable(monkeypatch, tmp_path):
    def fake_run(args, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=128,
            cmd=args,
            stderr="fatal: not a git repository",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(SystemExit) as exc:
        verify_test_baseline.resolve_base_commit(None, tmp_path)

    assert exc.value.code == 2


def test_main_without_commit_writes_git_head(monkeypatch, tmp_path):
    junit = tmp_path / "report.xml"
    junit.write_text(
        '<testsuite name="pytest" errors="0" failures="0" skipped="0" tests="1">'
        '<testcase classname="tests.sample" name="test_ok" />'
        "</testsuite>",
        encoding="utf-8",
    )
    output = tmp_path / "baseline.md"

    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args, 0, stdout="3723c00\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "verify_test_baseline.py",
            "--junit",
            str(junit),
            "--output",
            str(output),
            "--python",
            "3.13",
        ],
    )

    verify_test_baseline.main()

    assert "**Base Commit:** 3723c00" in output.read_text(encoding="utf-8")

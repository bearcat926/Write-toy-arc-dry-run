"""Milestone 3: Derived artifact policy + symlink escape tests."""
import os
import pytest
from pathlib import Path
from novel_workflow.validators.derived_artifact_policy import (
    is_derived_artifact,
    resolve_under_root,
    assert_safe_derived_path,
    assert_not_derived_source,
)
from novel_workflow.validators.error_codes import (
    DERIVED_ARTIFACT_NOT_ALLOWED,
    DERIVED_PATH_OUTSIDE_WORKSPACE,
    SYMLINK_DERIVED_PATH_REJECTED,
    PATH_ESCAPE_REJECTED,
)


def test_is_derived_artifact():
    assert is_derived_artifact("workspace/summaries/ch_001_summary.json")
    assert is_derived_artifact("workspace/reports/arc_health_report.md")
    assert is_derived_artifact("workspace/retrieval_traces/ch_001.jsonl")
    assert is_derived_artifact("workspace/phase2/meta.json")
    assert not is_derived_artifact("arcs/arc_001/drafts/ch_001.md")
    assert not is_derived_artifact("canon/approved_outline.md")
    assert not is_derived_artifact("ledgers/timeline.json")


def test_assert_not_derived_source_passes():
    assert_not_derived_source("arcs/arc_001/drafts/ch_001.md")


def test_assert_not_derived_source_rejects_workspace():
    with pytest.raises(ValueError, match=DERIVED_ARTIFACT_NOT_ALLOWED):
        assert_not_derived_source("workspace/summaries/ch_001_summary.json")


def test_resolve_under_root_valid(tmp_path: Path):
    (tmp_path / "canon").mkdir()
    (tmp_path / "canon" / "test.md").write_text("ok")
    resolved = resolve_under_root(tmp_path, "canon/test.md")
    assert str(resolved).startswith(str(tmp_path.resolve()))


def test_resolve_under_root_rejects_traversal(tmp_path: Path):
    with pytest.raises(ValueError, match=PATH_ESCAPE_REJECTED):
        resolve_under_root(tmp_path, "../escape.txt")


def test_assert_safe_derived_path_valid(tmp_path: Path):
    (tmp_path / "workspace" / "summaries").mkdir(parents=True)
    (tmp_path / "workspace" / "summaries" / "ch_001_summary.json").write_text("{}")
    assert_safe_derived_path(tmp_path, "workspace/summaries/ch_001_summary.json")


def test_assert_safe_derived_path_rejects_non_workspace(tmp_path: Path):
    with pytest.raises(ValueError, match=DERIVED_PATH_OUTSIDE_WORKSPACE):
        assert_safe_derived_path(tmp_path, "canon/test.md")


def test_symlink_derived_rejected(tmp_path: Path):
    """Symlinked derived artifacts must be rejected."""
    (tmp_path / "workspace" / "summaries").mkdir(parents=True)
    (tmp_path / "canon").mkdir(parents=True)
    (tmp_path / "canon" / "real.json").write_text("{}")

    symlink_path = tmp_path / "workspace" / "summaries" / "ch_001_summary.json"
    try:
        os.symlink(str(tmp_path / "canon" / "real.json"), str(symlink_path))
    except OSError:
        pytest.skip("Symlink creation not supported (requires admin on Windows)")

    with pytest.raises(ValueError, match=SYMLINK_DERIVED_PATH_REJECTED):
        assert_safe_derived_path(tmp_path, "workspace/summaries/ch_001_summary.json")


def test_symlink_to_outside_rejected(tmp_path: Path):
    """Symlink pointing outside root must be rejected."""
    outside = tmp_path.parent / "outside.json"
    outside.write_text("{}")
    (tmp_path / "workspace" / "summaries").mkdir(parents=True)
    symlink_path = tmp_path / "workspace" / "summaries" / "escape.json"
    try:
        os.symlink(str(outside), str(symlink_path))
    except OSError:
        pytest.skip("Symlink creation not supported (requires admin on Windows)")

    with pytest.raises(ValueError):
        assert_safe_derived_path(tmp_path, "workspace/summaries/escape.json")

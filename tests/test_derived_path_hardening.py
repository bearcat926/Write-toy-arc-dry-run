"""P1-1: Derived path hardening — prefix collision + symlink walk tests."""
import os
import pytest
from pathlib import Path
from novel_workflow.validators.derived_artifact_policy import (
    resolve_under_root,
    assert_safe_derived_path,
    assert_no_symlink_in_path,
)
from novel_workflow.validators.error_codes import (
    PATH_ESCAPE_REJECTED,
    SYMLINK_DERIVED_PATH_REJECTED,
    DERIVED_PATH_OUTSIDE_WORKSPACE,
)


def test_prefix_collision_not_escaped(tmp_path: Path):
    """workspace_foo/ must NOT be confused with workspace/ under str.startswith."""
    (tmp_path / "workspace_foo").mkdir()
    (tmp_path / "workspace_foo" / "test.json").write_text("{}")
    resolved = resolve_under_root(tmp_path, "workspace_foo/test.json")
    assert resolved.exists()


def test_relative_to_escape_rejected(tmp_path: Path):
    """Path traversal via ../ escaping root must be rejected."""
    (tmp_path / "canon").mkdir()
    (tmp_path / "canon" / "test.json").write_text("{}")
    with pytest.raises(ValueError, match=PATH_ESCAPE_REJECTED):
        resolve_under_root(tmp_path, "workspace/../../../etc/passwd")


def test_parent_symlink_rejected(tmp_path: Path):
    """workspace directory itself being a symlink must be rejected."""
    real_dir = tmp_path / "real_workspace"
    real_dir.mkdir()
    (real_dir / "summaries").mkdir()
    (real_dir / "summaries" / "ch_001.json").write_text("{}")

    ws_link = tmp_path / "workspace"
    from tests.symlink_helper import SymlinkFallback
    with SymlinkFallback(str(real_dir), str(ws_link)):
        with pytest.raises(ValueError, match=SYMLINK_DERIVED_PATH_REJECTED):
            assert_safe_derived_path(tmp_path, "workspace/summaries/ch_001.json")


def test_intermediate_dir_symlink_rejected(tmp_path: Path):
    """A symlink at any intermediate directory level must be rejected."""
    real_summaries = tmp_path / "real_summaries"
    real_summaries.mkdir()
    (real_summaries / "ch_001.json").write_text("{}")

    (tmp_path / "workspace").mkdir()
    summaries_link = tmp_path / "workspace" / "summaries"
    from tests.symlink_helper import SymlinkFallback
    with SymlinkFallback(str(real_summaries), str(summaries_link)):
        with pytest.raises(ValueError, match=SYMLINK_DERIVED_PATH_REJECTED):
            assert_safe_derived_path(tmp_path, "workspace/summaries/ch_001.json")


def test_assert_no_symlink_in_path_clean(tmp_path: Path):
    """No-op when path has no symlinks."""
    (tmp_path / "workspace" / "summaries").mkdir(parents=True)
    assert_no_symlink_in_path(tmp_path, "workspace/summaries/ch_001.json")

"""Derived artifact policy — prevents workspace derived files from entering fact chain."""
from pathlib import Path, PurePosixPath

from ..validators.error_codes import (
    DERIVED_ARTIFACT_NOT_ALLOWED,
    DERIVED_PATH_OUTSIDE_WORKSPACE,
    SYMLINK_DERIVED_PATH_REJECTED,
    PATH_ESCAPE_REJECTED,
)


DERIVED_PATH_PREFIXES = (
    "workspace/summaries/",
    "workspace/reports/",
    "workspace/retrieval_traces/",
    "workspace/phase2/",
)


def is_derived_artifact(path: str) -> bool:
    """Check if a path is a workspace derived artifact."""
    return any(path.startswith(p) for p in DERIVED_PATH_PREFIXES)


def resolve_under_root(root: Path, rel_path: str) -> Path:
    """Resolve a relative path under root, rejecting escapes."""
    root_resolved = root.resolve()
    target = (root / PurePosixPath(rel_path)).resolve()

    try:
        target.relative_to(root_resolved)
    except ValueError:
        raise ValueError(PATH_ESCAPE_REJECTED)

    return target


def assert_no_symlink_in_path(root: Path, rel_path: str) -> None:
    """Walk each path component and reject if any intermediate is a symlink."""
    root_resolved = root.resolve()
    parts = PurePosixPath(rel_path).parts
    current = root_resolved
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(SYMLINK_DERIVED_PATH_REJECTED)


def assert_safe_derived_path(root: Path, rel_path: str) -> None:
    """Assert that a derived path is safe: under workspace/, no symlinks."""
    if not rel_path.startswith("workspace/"):
        raise ValueError(DERIVED_PATH_OUTSIDE_WORKSPACE)
    assert_no_symlink_in_path(root, rel_path)
    resolve_under_root(root, rel_path)


def assert_not_derived_source(source_artifact: str) -> None:
    """Assert that a source artifact is not a workspace derived file."""
    if is_derived_artifact(source_artifact):
        raise ValueError(DERIVED_ARTIFACT_NOT_ALLOWED)

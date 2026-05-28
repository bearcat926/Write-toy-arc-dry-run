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

    if not str(target).startswith(str(root_resolved)):
        raise ValueError(PATH_ESCAPE_REJECTED)

    return target


def assert_safe_derived_path(root: Path, rel_path: str) -> None:
    """Assert that a derived path is safe: under workspace/, not a symlink."""
    resolved = resolve_under_root(root, rel_path)

    if not rel_path.startswith("workspace/"):
        raise ValueError(DERIVED_PATH_OUTSIDE_WORKSPACE)

    # Phase 2 MVP: forbid symlinked derived artifacts entirely
    if resolved.exists() and resolved.is_symlink():
        raise ValueError(SYMLINK_DERIVED_PATH_REJECTED)


def assert_not_derived_source(source_artifact: str) -> None:
    """Assert that a source artifact is not a workspace derived file."""
    if is_derived_artifact(source_artifact):
        raise ValueError(DERIVED_ARTIFACT_NOT_ALLOWED)

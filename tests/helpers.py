"""Test helpers — shared skip conditions and utilities."""

import os
import sys
import pytest


def can_create_symlink() -> bool:
    """Check if we can create real symlinks (requires admin on Windows)."""
    import tempfile
    try:
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, 'src')
            dst = os.path.join(d, 'dst')
            with open(src, 'w') as f:
                f.write('test')
            os.symlink(src, dst)
            return True
    except (OSError, PermissionError, NotImplementedError):
        return False


def has_crewai() -> bool:
    """Check if crewai package is importable."""
    try:
        import crewai  # noqa: F401
        return True
    except ImportError:
        return False


requires_symlink = pytest.mark.skipif(
    not can_create_symlink(),
    reason="Symlink creation requires admin privileges on Windows",
)

requires_crewai = pytest.mark.skipif(
    not has_crewai(),
    reason="crewai package not installed",
)

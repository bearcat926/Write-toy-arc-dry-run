import os
import sys
import pytest
from pathlib import Path


def _can_create_symlink() -> bool:
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


def _has_crewai() -> bool:
    """Check if crewai package is importable."""
    try:
        import crewai  # noqa: F401
        return True
    except ImportError:
        return False


# Register custom markers
requires_symlink = pytest.mark.skipif(
    not _can_create_symlink(),
    reason="Symlink creation requires admin privileges on Windows",
)

requires_crewai = pytest.mark.skipif(
    not _has_crewai(),
    reason="crewai package not installed",
)


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Create a minimal toy project directory structure."""
    root = tmp_path / "toy_project"
    for d in [
        "canon/manuscript",
        "canon/characters/character_mind_cards",
        "ledgers",
        "arcs/arc_001/drafts",
        "arcs/arc_001/reviews",
        "arcs/arc_001/proposals",
        "arcs/arc_001/reports",
        "arcs/arc_001/gates",
        "arcs/arc_001/checkpoints",
        "arcs/arc_001/archive",
        "gates",
        "workspace",
        "inspiration",
        "prompts",
        "variants",
        "profiles",
        "plugins",
    ]:
        (root / d).mkdir(parents=True, exist_ok=True)
    return root

import pytest
from pathlib import Path


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

from pathlib import Path
from novel_workflow.project_init import init_project


def test_init_creates_structure(tmp_path: Path):
    root = tmp_path / "new_project"
    init_project(root)
    assert (root / "canon" / "manuscript").is_dir()
    assert (root / "canon" / "characters" / "character_mind_cards").is_dir()
    assert (root / "ledgers").is_dir()
    assert (root / "gates").is_dir()
    assert (root / "workspace").is_dir()

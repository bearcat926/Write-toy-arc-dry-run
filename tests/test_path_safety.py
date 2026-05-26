import pytest
from pathlib import Path
from novel_workflow.guards.path_safety import PathSafetyGuard, PathSafetyError


@pytest.fixture
def guard(project_root: Path) -> PathSafetyGuard:
    return PathSafetyGuard(project_root)


def test_valid_path(guard: PathSafetyGuard, project_root: Path):
    result = guard.check_write_path("arcs/arc_001/drafts/ch_001.md", "agent")
    assert result == project_root / "arcs" / "arc_001" / "drafts" / "ch_001.md"


def test_traversal_rejected(guard: PathSafetyGuard):
    with pytest.raises(PathSafetyError, match="PATH_TRAVERSAL"):
        guard.check_write_path("../../../etc/passwd", "agent")


def test_absolute_rejected(guard: PathSafetyGuard):
    with pytest.raises(PathSafetyError, match="ABSOLUTE_PATH"):
        guard.check_write_path("/etc/passwd", "agent")


def test_agent_cannot_write_canon(guard: PathSafetyGuard):
    with pytest.raises(PathSafetyError, match="AGENT_WRITE_DENIED"):
        guard.check_write_path("canon/canon_state.json", "agent")


def test_system_script_can_write_arc_working_state(guard: PathSafetyGuard):
    result = guard.check_write_path("arcs/arc_001/arc_working_state.json", "system_script")
    assert result.name == "arc_working_state.json"


def test_plugin_cannot_write_canon(guard: PathSafetyGuard):
    with pytest.raises(PathSafetyError, match="PLUGIN_WRITE_DENIED"):
        guard.check_write_path("canon/canon_state.json", "plugin")


def test_plugin_can_write_inspiration(guard: PathSafetyGuard):
    result = guard.check_write_path("inspiration/idea_001.md", "plugin")
    assert result.name == "idea_001.md"

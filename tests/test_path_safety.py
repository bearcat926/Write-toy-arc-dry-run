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
    result = guard.check_write_path("arcs/arc_001/arc_working_state.json", "system_script", artifact_type="arc_working_state")
    assert result.name == "arc_working_state.json"


def test_system_script_can_write_canon_manuscript(guard: PathSafetyGuard):
    result = guard.check_write_path("canon/manuscript/ch_001.md", "system_script", artifact_type="canon_manuscript")
    assert result.name == "ch_001.md"


def test_system_script_can_write_ledgers(guard: PathSafetyGuard):
    result = guard.check_write_path("ledgers/timeline.json", "system_script", artifact_type="ledgers")
    assert result.name == "timeline.json"


def test_system_script_can_write_gate_record(guard: PathSafetyGuard):
    result = guard.check_write_path("gates/direction_gate.json", "system_script", artifact_type="gate_record")
    assert result.name == "direction_gate.json"


def test_system_script_can_write_progress(guard: PathSafetyGuard):
    result = guard.check_write_path("workspace/progress.jsonl", "system_script", artifact_type="progress")
    assert result.name == "progress.jsonl"


def test_system_script_artifact_mismatch_rejected(guard: PathSafetyGuard):
    with pytest.raises(PathSafetyError, match="SYSTEM_SCRIPT_ARTIFACT_MISMATCH"):
        guard.check_write_path("canon/manuscript/ch_001.md", "system_script", artifact_type="ledgers")


def test_system_script_unknown_artifact_type_rejected(guard: PathSafetyGuard):
    with pytest.raises(PathSafetyError, match="UNKNOWN_ARTIFACT_TYPE"):
        guard.check_write_path("some/path.txt", "system_script", artifact_type="unknown_type")


def test_system_script_missing_artifact_type_rejected(guard: PathSafetyGuard):
    with pytest.raises(PathSafetyError, match="MISSING_ARTIFACT_TYPE"):
        guard.check_write_path("arcs/arc_001/arc_working_state.json", "system_script")


def test_system_script_unrelated_path_rejected(guard: PathSafetyGuard):
    with pytest.raises(PathSafetyError, match="SYSTEM_SCRIPT_ARTIFACT_MISMATCH"):
        guard.check_write_path("workspace/some_random_file.txt", "system_script", artifact_type="progress")


def test_plugin_cannot_write_canon(guard: PathSafetyGuard):
    with pytest.raises(PathSafetyError, match="PLUGIN_WRITE_DENIED"):
        guard.check_write_path("canon/canon_state.json", "plugin")


def test_plugin_can_write_inspiration(guard: PathSafetyGuard):
    result = guard.check_write_path("inspiration/idea_001.md", "plugin")
    assert result.name == "idea_001.md"

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


def test_system_script_arc_contract_succeeds(guard: PathSafetyGuard, project_root: Path):
    result = guard.check_write_path("arcs/arc_001/arc_contract.md", "system_script", artifact_type="arc_contract")
    assert result.name == "arc_contract.md"


def test_system_script_canon_manuscript_copy_succeeds(guard: PathSafetyGuard, project_root: Path):
    result = guard.check_write_path("canon/manuscript/ch_001.md", "system_script", artifact_type="canon_manuscript_copy")
    assert result.name == "ch_001.md"


def test_system_script_canon_character_update_succeeds(guard: PathSafetyGuard, project_root: Path):
    result = guard.check_write_path(
        "canon/characters/character_mind_cards/hero.json", "system_script", artifact_type="canon_character_update"
    )
    assert result.name == "hero.json"


def test_system_script_inverse_diff_succeeds(guard: PathSafetyGuard, project_root: Path):
    result = guard.check_write_path("arcs/arc_001/reports/inverse_diff.json", "system_script", artifact_type="inverse_diff")
    assert result.name == "inverse_diff.json"


def test_system_script_inverse_diff_wrong_path_rejected(guard: PathSafetyGuard):
    with pytest.raises(PathSafetyError, match="SYSTEM_SCRIPT_ARTIFACT_MISMATCH"):
        guard.check_write_path("arcs/arc_001/reports/other.json", "system_script", artifact_type="inverse_diff")


def test_system_script_known_types_succeed_unknown_rejected(guard: PathSafetyGuard):
    """Known artifact types should succeed; unknown types should be rejected."""
    known_artifacts = [
        ("arcs/arc_001/arc_working_state.json", "arc_working_state"),
        ("workspace/progress.jsonl", "progress"),
        ("arcs/arc_001/reports/ledger_diff.json", "ledger_diff"),
        ("workspace/consumed_hashes.json", "consumed_hashes"),
        ("workspace/dashboard_report.md", "dashboard"),
        ("arcs/arc_001/reports/apply_record.json", "apply_record"),
        ("arcs/arc_001/arc_contract.md", "arc_contract"),
    ]
    for path, artifact_type in known_artifacts:
        guard.check_write_path(path, "system_script", artifact_type=artifact_type)

    with pytest.raises(PathSafetyError, match="UNKNOWN_ARTIFACT_TYPE"):
        guard.check_write_path("workspace/some_file.txt", "system_script", artifact_type="bogus_type")


def test_intermediate_symlink_rejected_by_guard(project_root: Path):
    """PathSafetyGuard must reject paths with symlinked intermediate directories."""
    import os
    real_dir = project_root / "real_arcs"
    real_dir.mkdir()
    (real_dir / "arc_001").mkdir(parents=True)
    (real_dir / "arc_001" / "drafts").mkdir()

    arcs_link = project_root / "arcs"
    try:
        os.symlink(str(real_dir), str(arcs_link))
    except OSError:
        pytest.skip("Symlink creation not supported (requires admin on Windows)")

    guard = PathSafetyGuard(project_root)
    with pytest.raises(PathSafetyError, match="SYMLINK_ESCAPE_REJECTED"):
        guard.check_write_path("arcs/arc_001/drafts/ch_001.md", "agent")

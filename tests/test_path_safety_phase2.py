"""Milestone 4: PathSafetyGuard Phase 2 extension tests."""
import pytest
from pathlib import Path
from novel_workflow.guards.path_safety import PathSafetyGuard, PathSafetyError


def test_narrative_summary_path_allowed(project_root: Path):
    guard = PathSafetyGuard(project_root)
    (project_root / "workspace" / "summaries").mkdir(parents=True, exist_ok=True)
    resolved = guard.check_write_path(
        "workspace/summaries/ch_001_summary.json", "system_script",
        artifact_type="narrative_summary",
    )
    assert resolved is not None


def test_arc_summary_path_allowed(project_root: Path):
    guard = PathSafetyGuard(project_root)
    (project_root / "workspace" / "summaries").mkdir(parents=True, exist_ok=True)
    resolved = guard.check_write_path(
        "workspace/summaries/arc_001_summary.json", "system_script",
        artifact_type="arc_summary",
    )
    assert resolved is not None


def test_retrieval_trace_path_allowed(project_root: Path):
    guard = PathSafetyGuard(project_root)
    (project_root / "workspace" / "retrieval_traces").mkdir(parents=True, exist_ok=True)
    resolved = guard.check_write_path(
        "workspace/retrieval_traces/ch_001.jsonl", "system_script",
        artifact_type="retrieval_trace",
    )
    assert resolved is not None


def test_phase2_meta_path_allowed(project_root: Path):
    guard = PathSafetyGuard(project_root)
    (project_root / "workspace" / "phase2").mkdir(parents=True, exist_ok=True)
    resolved = guard.check_write_path(
        "workspace/phase2/meta.json", "system_script",
        artifact_type="phase2_meta",
    )
    assert resolved is not None


def test_narrative_summary_wrong_artifact_type(project_root: Path):
    guard = PathSafetyGuard(project_root)
    with pytest.raises(PathSafetyError):
        guard.check_write_path(
            "workspace/summaries/ch_001_summary.json", "system_script",
            artifact_type="progress",
        )


def test_retrieval_trace_path_traversal_rejected(project_root: Path):
    guard = PathSafetyGuard(project_root)
    with pytest.raises(PathSafetyError):
        guard.check_write_path(
            "workspace/retrieval_traces/../../../escape.jsonl", "system_script",
            artifact_type="retrieval_trace",
        )


def test_unknown_phase2_artifact_type_rejected(project_root: Path):
    guard = PathSafetyGuard(project_root)
    with pytest.raises(PathSafetyError, match="UNKNOWN_ARTIFACT_TYPE"):
        guard.check_write_path(
            "workspace/test.json", "system_script",
            artifact_type="truly_unknown_type_xyz",
        )

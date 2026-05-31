"""RebuildOrchestrator tests."""
import json
import pytest
from pathlib import Path
from novel_workflow.system_scripts.rebuild_orchestrator import RebuildOrchestrator, RebuildReport


def _seed_project(root: Path):
    """Create minimal project structure."""
    (root / "arcs" / "arc_001" / "drafts").mkdir(parents=True, exist_ok=True)
    (root / "arcs" / "arc_001" / "drafts" / "ch_001.md").write_text(
        "# Chapter 1\n\nAlice walked in. Bob looked up.", encoding="utf-8"
    )
    (root / "arcs" / "arc_001" / "arc_contract.md").write_text(
        "# Contract\nGoal: journey.", encoding="utf-8"
    )
    (root / "canon").mkdir(exist_ok=True)
    (root / "canon" / "approved_outline.md").write_text("# Outline", encoding="utf-8")
    (root / "ledgers").mkdir(exist_ok=True)
    (root / "ledgers" / "timeline.json").write_text(
        json.dumps({"schema_version": "1.0", "events": []}), encoding="utf-8"
    )
    (root / "ledgers" / "character_knowledge.json").write_text(
        json.dumps({"schema_version": "1.0", "entries": []}), encoding="utf-8"
    )
    (root / "ledgers" / "foreshadowing.json").write_text(
        json.dumps({"schema_version": "1.0", "foreshadowing_entries": []}), encoding="utf-8"
    )


def test_rebuild_summary(tmp_path: Path):
    """Rebuild should generate summary for a chapter."""
    _seed_project(tmp_path)
    orchestrator = RebuildOrchestrator(tmp_path)
    result = orchestrator.rebuild(arc_id="arc_001", chapter_id="ch_001", reason="test")
    assert result.success is True
    assert any("summary" in r.artifact_path for r in result.rebuilt)
    summary_path = tmp_path / "workspace" / "summaries" / "ch_001_summary.json"
    assert summary_path.exists()


def test_rebuild_concurrent_fails(tmp_path: Path):
    """Second concurrent rebuild should fail."""
    _seed_project(tmp_path)
    orchestrator = RebuildOrchestrator(tmp_path)
    orchestrator._lock.acquire("test_process")
    result = orchestrator.rebuild(arc_id="arc_001", chapter_id="ch_001", reason="test")
    assert result.success is False
    assert "lock" in result.reason.lower()
    orchestrator._lock.release()


def test_rebuild_releases_lock(tmp_path: Path):
    """Lock should be released after rebuild."""
    _seed_project(tmp_path)
    orchestrator = RebuildOrchestrator(tmp_path)
    orchestrator.rebuild(arc_id="arc_001", chapter_id="ch_001", reason="test")
    assert orchestrator._lock.is_locked() is False


def test_rebuild_arc_level(tmp_path: Path):
    """Arc-level rebuild (no chapter_id) should not fail."""
    _seed_project(tmp_path)
    orchestrator = RebuildOrchestrator(tmp_path)
    result = orchestrator.rebuild(arc_id="arc_001", chapter_id=None, reason="arc_rebuild")
    assert result.success is True


def test_all_adapters_registered(tmp_path: Path):
    """All 8 required adapters must be registered."""
    from novel_workflow.system_scripts.rebuild_orchestrator import SummaryRebuildAdapter, GraphRebuildAdapter, LifecycleRebuildAdapter, DriftRebuildAdapter, ArcPlanRebuildAdapter, BeatPlanRebuildAdapter, TraceRebuildAdapter, CalibrationRebuildAdapter
    orchestrator = RebuildOrchestrator(tmp_path)
    required = {"summary", "graph", "lifecycle", "drift", "arc_plan", "beat_plan", "trace", "calibration"}
    for step in required:
        assert step in orchestrator._adapters, f"Missing adapter: {step}"
        assert not isinstance(orchestrator._adapters[step], type(None)), f"Null adapter: {step}"

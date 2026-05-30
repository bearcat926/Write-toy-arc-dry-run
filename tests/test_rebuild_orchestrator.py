"""RebuildOrchestrator tests."""
import json
import pytest
from pathlib import Path
from novel_workflow.system_scripts.rebuild_orchestrator import RebuildOrchestrator, RebuildResult


def _seed_project(root: Path):
    """Create minimal project structure."""
    (root / "arcs" / "arc_001" / "drafts").mkdir(parents=True, exist_ok=True)
    (root / "arcs" / "arc_001" / "drafts" / "ch_001.md").write_text(
        "# Chapter 1\n\nAlice walked in. Bob looked up.", encoding="utf-8"
    )


def test_rebuild_summary(tmp_path: Path):
    """Rebuild should generate summary for a chapter."""
    _seed_project(tmp_path)
    orchestrator = RebuildOrchestrator(tmp_path)
    result = orchestrator.rebuild("arc_001", "ch_001", "test")
    assert result.success is True
    assert any("summary" in a for a in result.rebuilt_artifacts)
    # Summary file should exist
    summary_path = tmp_path / "workspace" / "summaries" / "ch_001_summary.json"
    assert summary_path.exists()


def test_rebuild_registers_in_manifest(tmp_path: Path):
    """Rebuild should register artifacts in manifest."""
    _seed_project(tmp_path)
    orchestrator = RebuildOrchestrator(tmp_path)
    orchestrator.rebuild("arc_001", "ch_001", "test")
    # Check manifest has the summary entry
    manifest_path = tmp_path / "workspace" / "phase2" / "manifest.json"
    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text())
    assert len(data["entries"]) >= 1


def test_rebuild_concurrent_fails(tmp_path: Path):
    """Second concurrent rebuild should fail."""
    _seed_project(tmp_path)
    orchestrator = RebuildOrchestrator(tmp_path)
    # Acquire lock manually
    orchestrator._lock.acquire("test_process")
    result = orchestrator.rebuild("arc_001", "ch_001", "test")
    assert result.success is False
    assert "lock" in result.reason.lower()
    orchestrator._lock.release()


def test_rebuild_releases_lock(tmp_path: Path):
    """Lock should be released after rebuild."""
    _seed_project(tmp_path)
    orchestrator = RebuildOrchestrator(tmp_path)
    orchestrator.rebuild("arc_001", "ch_001", "test")
    assert orchestrator._lock.is_locked() is False


def test_rebuild_arc_level(tmp_path: Path):
    """Arc-level rebuild (no chapter_id) should not fail."""
    _seed_project(tmp_path)
    orchestrator = RebuildOrchestrator(tmp_path)
    result = orchestrator.rebuild("arc_001", None, "arc_rebuild")
    assert result.success is True

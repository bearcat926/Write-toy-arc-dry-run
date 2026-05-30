"""ForeshadowLifecycleManager tests."""
import json
import pytest
from pathlib import Path
from novel_workflow.system_scripts.foreshadow_lifecycle_manager import ForeshadowLifecycleManager


def _seed_project(root: Path):
    """Create project with foreshadowing ledger and summaries."""
    (root / "ledgers").mkdir(parents=True, exist_ok=True)
    (root / "ledgers" / "foreshadowing.json").write_text(json.dumps({
        "schema_version": "1.0",
        "foreshadowing_entries": [
            {"foreshadow_id": "fs1", "summary": "Broken sword", "status": "introduced", "priority": "high", "introduced_chapter": "ch_001"},
            {"foreshadow_id": "fs2", "summary": "Dark prophecy", "status": "developed", "priority": "medium", "introduced_chapter": "ch_002"},
            {"foreshadow_id": "fs3", "summary": "Old promise", "status": "paid_off", "priority": "low", "introduced_chapter": "ch_001"},
        ],
    }), encoding="utf-8")
    (root / "workspace" / "summaries").mkdir(parents=True, exist_ok=True)
    (root / "workspace" / "summaries" / "ch_003_summary.json").write_text(json.dumps({
        "chapter_id": "ch_003", "arc_id": "arc_001",
        "source_layer": "draft", "source_artifact": "arcs/arc_001/drafts/ch_003.md",
        "source_artifact_hash": "abc", "derived": True,
        "foreshadow_updates": ["fs1 activated by hero's discovery"],
    }), encoding="utf-8")


def test_build_creates_entries(tmp_path: Path):
    _seed_project(tmp_path)
    manager = ForeshadowLifecycleManager(tmp_path)
    idx = manager.build("arc_001")
    assert idx.derived is True
    assert len(idx.items) == 3


def test_state_mapping_from_ledger(tmp_path: Path):
    """Test initial state mapping without summary updates."""
    # Only create ledger, no summaries
    (tmp_path / "ledgers").mkdir(parents=True, exist_ok=True)
    (tmp_path / "ledgers" / "foreshadowing.json").write_text(json.dumps({
        "schema_version": "1.0",
        "foreshadowing_entries": [
            {"foreshadow_id": "fs1", "summary": "Broken sword", "status": "introduced", "priority": "high", "introduced_chapter": "ch_001"},
            {"foreshadow_id": "fs2", "summary": "Dark prophecy", "status": "developed", "priority": "medium", "introduced_chapter": "ch_002"},
            {"foreshadow_id": "fs3", "summary": "Old promise", "status": "paid_off", "priority": "low", "introduced_chapter": "ch_001"},
        ],
    }), encoding="utf-8")
    manager = ForeshadowLifecycleManager(tmp_path)
    idx = manager.build("arc_001")
    states = {item.foreshadow_id: item.current_state for item in idx.items}
    assert states["fs1"] == "seeded"      # introduced → seeded
    assert states["fs2"] == "activated"   # developed → activated
    assert states["fs3"] == "resolved"    # paid_off → resolved


def test_summary_updates_state(tmp_path: Path):
    _seed_project(tmp_path)
    manager = ForeshadowLifecycleManager(tmp_path)
    idx = manager.build("arc_001")
    # fs1 should have been activated by summary
    fs1 = next(item for item in idx.items if item.foreshadow_id == "fs1")
    assert fs1.current_state == "activated"
    assert fs1.last_touched_chapter == "ch_003"
    assert len(fs1.state_history) >= 2


def test_empty_ledger(tmp_path: Path):
    (tmp_path / "ledgers").mkdir(parents=True, exist_ok=True)
    (tmp_path / "ledgers" / "foreshadowing.json").write_text(
        json.dumps({"schema_version": "1.0", "foreshadowing_entries": []}),
        encoding="utf-8",
    )
    manager = ForeshadowLifecycleManager(tmp_path)
    idx = manager.build("arc_001")
    assert len(idx.items) == 0

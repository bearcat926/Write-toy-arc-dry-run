"""Manifest integration tests — all builders register in manifest."""
import json
import pytest
from pathlib import Path
from novel_workflow.system_scripts.narrative_graph_builder import NarrativeGraphBuilder
from novel_workflow.system_scripts.foreshadow_lifecycle_manager import ForeshadowLifecycleManager
from novel_workflow.system_scripts.character_consistency_engine import CharacterConsistencyEngine
from novel_workflow.system_scripts.arc_planning_engine import ArcPlanningEngine
from novel_workflow.system_scripts.manifest_manager import ManifestManager


def _seed_project(root: Path):
    """Create minimal project for all builders."""
    (root / "ledgers").mkdir(parents=True, exist_ok=True)
    (root / "ledgers" / "timeline.json").write_text(
        json.dumps({"schema_version": "1.0", "events": []}), encoding="utf-8"
    )
    (root / "ledgers" / "character_knowledge.json").write_text(
        json.dumps({"schema_version": "1.0", "entries": []}), encoding="utf-8"
    )
    (root / "ledgers" / "foreshadowing.json").write_text(
        json.dumps({"schema_version": "1.0", "entries": []}), encoding="utf-8"
    )
    (root / "arcs" / "arc_001").mkdir(parents=True, exist_ok=True)
    (root / "arcs" / "arc_001" / "arc_contract.md").write_text(
        "# Contract\nGoal: Test\n", encoding="utf-8"
    )
    (root / "arcs" / "arc_001" / "drafts").mkdir(exist_ok=True)
    (root / "arcs" / "arc_001" / "drafts" / "ch_001.md").write_text(
        "# Ch 1\nAlice walked in.", encoding="utf-8"
    )
    (root / "canon").mkdir(exist_ok=True)
    (root / "canon" / "approved_outline.md").write_text("# Outline\n", encoding="utf-8")


def test_graph_builder_registers_manifest(tmp_path: Path):
    _seed_project(tmp_path)
    builder = NarrativeGraphBuilder(tmp_path)
    builder.build("arc_001")
    manifest = ManifestManager(tmp_path).load()
    graph_entries = [e for e in manifest.entries if e.artifact_type == "narrative_graph_index"]
    assert len(graph_entries) == 1


def test_lifecycle_manager_registers_manifest(tmp_path: Path):
    _seed_project(tmp_path)
    manager = ForeshadowLifecycleManager(tmp_path)
    manager.write_index("arc_001")  # write_index builds + writes + registers
    manifest = ManifestManager(tmp_path).load()
    lc_entries = [e for e in manifest.entries if e.artifact_type == "foreshadow_lifecycle_index"]
    assert len(lc_entries) == 1


def test_consistency_engine_registers_manifest(tmp_path: Path):
    _seed_project(tmp_path)
    from novel_workflow.schemas.character_state import CharacterBaseline
    engine = CharacterConsistencyEngine(tmp_path)
    baseline = CharacterBaseline(character_id="alice", stable_traits=["brave"])
    engine.check_chapter("arc_001", "ch_001", "alice", baseline)
    manifest = ManifestManager(tmp_path).load()
    drift_entries = [e for e in manifest.entries if e.artifact_type == "character_drift_report"]
    assert len(drift_entries) == 1


def test_arc_planner_registers_manifest(tmp_path: Path):
    _seed_project(tmp_path)
    engine = ArcPlanningEngine(tmp_path)
    engine.ensure_arc_artifacts(arc_id="arc_001", chapter_count=3)
    manifest = ManifestManager(tmp_path).load()
    arc_entries = [e for e in manifest.entries if e.artifact_type == "arc_plan"]
    assert len(arc_entries) == 1

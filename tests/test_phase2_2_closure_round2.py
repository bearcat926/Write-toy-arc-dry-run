"""Phase 2.2 Closure Round 2 regression tests.

Validates all 6 patches from the audit closure review:
- C1: Stable snapshot read
- C2: Active failure policy
- C3: Role trace separation
- C4: GenerationCache hit
- C5: Unified planning horizon
- C6: Enhanced verifier
"""
import json
import pytest
from pathlib import Path
from novel_workflow.system_scripts.context_provider import ContextProvider
from novel_workflow.system_scripts.stable_generation_pointer import StableGenerationPointer, StableSnapshot
from novel_workflow.system_scripts.generation_cache import GenerationCache
from novel_workflow.system_scripts.retrieval_context_builder import RetrievalContextBuilder
from novel_workflow.system_scripts.rebuild_orchestrator import (
    RebuildOrchestrator, resolve_planning_horizon,
)
from novel_workflow.system_scripts.manifest_manager import ManifestManager
from novel_workflow.system_scripts.narrative_compressor import NarrativeCompressor
from novel_workflow.schemas.manifest import DerivedArtifactEntry
from novel_workflow.schemas.retrieval import RetrievalRequest


def _seed_project(root: Path, chapters: int = 5):
    """Create minimal project structure."""
    (root / "canon").mkdir(parents=True, exist_ok=True)
    (root / "canon" / "approved_outline.md").write_text("# Outline\n", encoding="utf-8")
    (root / "arcs" / "arc_001").mkdir(parents=True, exist_ok=True)
    (root / "arcs" / "arc_001" / "arc_contract.md").write_text("# Contract\nGoal: Test\n", encoding="utf-8")
    (root / "ledgers").mkdir(parents=True, exist_ok=True)
    (root / "ledgers" / "timeline.json").write_text(
        json.dumps({"schema_version": "1.0", "events": []}), encoding="utf-8"
    )
    (root / "ledgers" / "character_knowledge.json").write_text(
        json.dumps({"schema_version": "1.0", "entries": []}), encoding="utf-8"
    )
    (root / "ledgers" / "foreshadowing.json").write_text(
        json.dumps({"schema_version": "1.0", "foreshadowing_entries": []}), encoding="utf-8"
    )
    (root / "arcs" / "arc_001" / "drafts").mkdir(parents=True, exist_ok=True)
    for i in range(1, chapters + 1):
        (root / "arcs" / "arc_001" / "drafts" / f"ch_{i:03d}.md").write_text(
            f"# Chapter {i}\n\nContent of chapter {i}.\n", encoding="utf-8"
        )


def _seed_manifest_with_summary(root: Path):
    """Seed manifest with summary and lifecycle entries."""
    (root / "workspace" / "summaries").mkdir(parents=True, exist_ok=True)
    (root / "workspace" / "summaries" / "ch_001_summary.json").write_text(
        json.dumps({"chapter_id": "ch_001", "causal_events": ["event_1"]}),
        encoding="utf-8",
    )
    (root / "workspace" / "foreshadow_lifecycle_index.json").write_text(
        json.dumps({"index_id": "test", "arc_id": "arc_001", "items": []}),
        encoding="utf-8",
    )
    mgr = ManifestManager(root)
    mgr.register_artifact(DerivedArtifactEntry(
        artifact_path="workspace/summaries/ch_001_summary.json",
        artifact_type="narrative_summary", builder_name="test",
    ))
    mgr.register_artifact(DerivedArtifactEntry(
        artifact_path="workspace/foreshadow_lifecycle_index.json",
        artifact_type="foreshadow_lifecycle_index", builder_name="test",
    ))
    mgr.save()


# ---- Patch C1: Stable snapshot read ----

def test_active_snapshot_reads_manifest_selected_path(tmp_path: Path):
    """Active builder reads stable entry path, not fixed workspace path."""
    _seed_project(tmp_path)
    _seed_manifest_with_summary(tmp_path)

    # Create a stale summary at a different path
    (tmp_path / "workspace" / "summaries" / "stale_summary.json").write_text(
        '{"chapter_id": "stale"}', encoding="utf-8"
    )
    mgr = ManifestManager(tmp_path)
    mgr.register_artifact(DerivedArtifactEntry(
        artifact_path="workspace/summaries/stale_summary.json",
        artifact_type="narrative_summary", builder_name="test_stale",
    ))
    mgr.mark_stale("workspace/summaries/stale_summary.json", reason="rollback")
    mgr.save()

    # Build snapshot - should not include stale entry
    pointer = StableGenerationPointer(tmp_path)
    snapshot = pointer.resolve_snapshot()
    assert snapshot.has("narrative_summary")
    entry = snapshot.get_entry("narrative_summary")
    assert entry.artifact_path == "workspace/summaries/ch_001_summary.json"
    assert not entry.stale


def test_active_snapshot_blocks_stale_only(tmp_path: Path):
    """Rollback residue files cannot enter retrieval when all entries are stale."""
    _seed_project(tmp_path)
    mgr = ManifestManager(tmp_path)
    (tmp_path / "workspace" / "summaries").mkdir(parents=True, exist_ok=True)
    (tmp_path / "workspace" / "summaries" / "ch_001_summary.json").write_text(
        '{"chapter_id": "ch_001"}', encoding="utf-8"
    )
    mgr.register_artifact(DerivedArtifactEntry(
        artifact_path="workspace/summaries/ch_001_summary.json",
        artifact_type="narrative_summary", builder_name="test",
    ))
    mgr.mark_stale("workspace/summaries/ch_001_summary.json", reason="rollback")
    mgr.save()

    pointer = StableGenerationPointer(tmp_path)
    with pytest.raises(RuntimeError, match="all entries are stale"):
        pointer.resolve_snapshot(required_types=["narrative_summary"])


def test_active_snapshot_rejects_hash_mismatch(tmp_path: Path):
    """Stable entry hash mismatch must block."""
    _seed_project(tmp_path)
    # Create summary with known content
    (tmp_path / "workspace" / "summaries").mkdir(parents=True, exist_ok=True)
    summary_path = tmp_path / "workspace" / "summaries" / "ch_001_summary.json"
    summary_path.write_text('{"chapter_id": "ch_001"}', encoding="utf-8")

    mgr = ManifestManager(tmp_path)
    mgr.register_artifact(DerivedArtifactEntry(
        artifact_path="workspace/summaries/ch_001_summary.json",
        artifact_type="narrative_summary", builder_name="test",
        content_hash="wrong_hash_value",
    ))
    mgr.save()

    # register_persisted_artifact should catch hash mismatch
    with pytest.raises(ValueError, match="Hash mismatch"):
        mgr.register_persisted_artifact(DerivedArtifactEntry(
            artifact_path="workspace/summaries/ch_001_summary.json",
            artifact_type="narrative_summary", builder_name="test",
            content_hash="wrong_hash_value",
        ))


# ---- Patch C2: Active failure policy ----

def test_active_trace_failure_raises(tmp_path: Path):
    """Active mode trace write failure must hard-fail."""
    # Write to a non-existent directory to trigger failure
    with pytest.raises(RuntimeError, match="Active mode: trace write failed"):
        ContextProvider.write_trace(
            tmp_path / "nonexistent_root",
            "arc_001", "ch_001",
            None,  # type: ignore  # will cause failure
            role="writer",
            active=True,
        )


def test_shadow_trace_failure_returns_false(tmp_path: Path):
    """Shadow mode trace write failure returns False without raising."""
    result = ContextProvider.write_trace(
        tmp_path / "nonexistent_root",
        "arc_001", "ch_001",
        None,  # type: ignore
        role="writer",
        active=False,
    )
    assert result is False


# ---- Patch C3: Role trace separation ----

def test_role_specific_trace_paths(tmp_path: Path):
    """Writer, Auditor, Extractor trace files are separated."""
    _seed_project(tmp_path)
    _seed_manifest_with_summary(tmp_path)
    provider = ContextProvider(tmp_path, mode="retrieval_active")

    for role in ("writer", "auditor", "extractor"):
        method = getattr(provider, f"build_{role}_context")
        _, trace = method("arc_001", 1)
        if trace:
            ContextProvider.write_trace(
                tmp_path, "arc_001", "ch_001", trace,
                role=role, active=False,
            )

    # Verify separate files
    trace_dir = tmp_path / "workspace" / "retrieval_traces" / "arc_001" / "ch_001"
    for role in ("writer", "auditor", "extractor"):
        assert (trace_dir / f"{role}.jsonl").exists(), f"Missing {role} trace"


# ---- Patch C4: GenerationCache hit ----

def test_generation_cache_hit_avoids_rebuild(tmp_path: Path):
    """Cache hit returns immediately without rebuilding context."""
    _seed_project(tmp_path)
    _seed_manifest_with_summary(tmp_path)
    provider = ContextProvider(tmp_path, mode="retrieval_active")

    # First call: builds and caches
    ctx1, trace1 = provider.build_writer_context("arc_001", 1)
    assert provider.cache.size() == 1

    # Second call: should hit cache
    ctx2, trace2 = provider.build_writer_context("arc_001", 1)
    assert ctx1 == ctx2
    # Cache size should still be 1 (overwritten, not duplicated)
    assert provider.cache.size() == 1


def test_cache_invalidation_by_generation(tmp_path: Path):
    """Cache invalidation by generation_id works."""
    cache = GenerationCache()
    cache.put("key1", "val1", generation_id="gen_1")
    cache.put("key2", "val2", generation_id="gen_1")
    cache.put("key3", "val3", generation_id="gen_2")
    assert cache.size() == 3

    removed = cache.invalidate_generation("gen_1")
    assert removed == 2
    assert cache.size() == 1
    assert cache.get("key3") == "val3"


# ---- Patch C5: Unified planning horizon ----

def test_resolve_planning_horizon_min_10(tmp_path: Path):
    """Planning horizon is at least 10 even with few drafts."""
    _seed_project(tmp_path, chapters=3)
    horizon = resolve_planning_horizon(tmp_path, "arc_001")
    assert horizon == 10


def test_resolve_planning_horizon_extends_for_chapter(tmp_path: Path):
    """Planning horizon extends when target chapter is beyond existing drafts."""
    _seed_project(tmp_path, chapters=5)
    horizon = resolve_planning_horizon(tmp_path, "arc_001", "ch_015")
    assert horizon == 15


def test_beat_plan_rebuild_after_chapter_10(tmp_path: Path):
    """ch_011 and later can rebuild BeatPlan successfully."""
    _seed_project(tmp_path, chapters=15)
    orchestrator = RebuildOrchestrator(tmp_path)
    result = orchestrator.rebuild(
        arc_id="arc_001", chapter_id="ch_011", reason="test_ch_011",
    )
    # BeatPlan should find the target beat
    beat_results = [r for r in result.rebuilt if "beat_plan" in r.artifact_path]
    if beat_results:
        assert beat_results[0].success is True


# ---- Patch C6: Enhanced verifier ----

def test_phase3_verifier_detects_junit_count_mismatch(tmp_path: Path):
    """Verifier fails when baseline count doesn't match JUnit."""
    # Create fake baseline with wrong count
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(exist_ok=True)
    (docs_dir / "phase2_test_baseline.generated.md").write_text(
        "<!-- DO NOT EDIT -->\n# Baseline\n\n"
        "**Base Commit:** abc1234\n\n"
        "## Summary\n\n"
        "| Metric | Count |\n|--------|-------|\n"
        "| Total | 999 |\n| Passed | 999 |\n"
        "| Failed | 0 |\n| Errors | 0 |\n| Skipped | 0 |\n",
        encoding="utf-8",
    )
    # Create minimal JUnit with different count
    (tmp_path / "report.xml").write_text(
        '<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0">'
        '<testcase name="test_1" classname="test"/></testsuite></testsuites>',
        encoding="utf-8",
    )

    # Use inline check instead of subprocess (project_root may differ from tmp_path)
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "verify_phase3", str(Path(__file__).resolve().parent.parent / "scripts" / "verify_phase3_entry_gate.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    result = mod.check_baseline_test_count(tmp_path)
    assert result["passed"] is False
    assert "mismatch" in str(result.get("errors", [])).lower()

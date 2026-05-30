"""PatchA/B/C closure tests — StablePointer, Cache, Replay, DAG, BatchStop."""
import json
import pytest
from pathlib import Path
from novel_workflow.system_scripts.stable_generation_pointer import StableGenerationPointer
from novel_workflow.system_scripts.generation_cache import GenerationCache
from novel_workflow.system_scripts.replay_contract import ReplayContract
from novel_workflow.system_scripts.rebuild_dag import RebuildDAG
from novel_workflow.system_scripts.batch_stop import BatchStopPropagator, BatchStopSignal
from novel_workflow.system_scripts.manifest_manager import ManifestManager
from novel_workflow.schemas.manifest import DerivedArtifactEntry


def _seed_manifest(root: Path):
    mgr = ManifestManager(root)
    mgr.register_artifact(DerivedArtifactEntry(
        artifact_path="workspace/summaries/ch_001_summary.json",
        artifact_type="narrative_summary",
        builder_name="NarrativeCompressor",
    ))
    mgr.save()


# === StableGenerationPointer ===

def test_stable_pointer_returns_non_stale(tmp_path: Path):
    _seed_manifest(tmp_path)
    ptr = StableGenerationPointer(tmp_path)
    entry = ptr.get_stable("narrative_summary")
    assert entry is not None
    assert entry.artifact_type == "narrative_summary"


def test_stable_pointer_hides_stale(tmp_path: Path):
    _seed_manifest(tmp_path)
    mgr = ManifestManager(tmp_path)
    mgr.mark_stale("workspace/summaries/ch_001_summary.json", "test")
    mgr.save()
    ptr = StableGenerationPointer(tmp_path)
    assert ptr.get_stable("narrative_summary") is None


def test_stable_pointer_rollback(tmp_path: Path):
    _seed_manifest(tmp_path)
    ptr = StableGenerationPointer(tmp_path)
    assert ptr.rollback_to_previous("narrative_summary") is True
    assert ptr.get_stable("narrative_summary") is None


# === GenerationCache ===

def test_cache_put_get():
    cache = GenerationCache()
    cache.put("key1", "value1", "gen_001")
    assert cache.get("key1") == "value1"


def test_cache_invalidate_generation():
    cache = GenerationCache()
    cache.put("k1", "v1", "gen_001")
    cache.put("k2", "v2", "gen_001")
    cache.put("k3", "v3", "gen_002")
    count = cache.invalidate_generation("gen_001")
    assert count == 2
    assert cache.get("k1") is None
    assert cache.get("k3") == "v3"


def test_cache_clear():
    cache = GenerationCache()
    cache.put("k1", "v1")
    cache.clear()
    assert cache.size() == 0


# === ReplayContract ===

def test_replay_contract_capture(tmp_path: Path):
    (tmp_path / "canon").mkdir(parents=True, exist_ok=True)
    (tmp_path / "canon" / "approved_outline.md").write_text("# Outline")
    (tmp_path / "arcs" / "arc_001").mkdir(parents=True, exist_ok=True)
    (tmp_path / "arcs" / "arc_001" / "arc_contract.md").write_text("# Contract")
    (tmp_path / "arcs" / "arc_001" / "drafts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "arcs" / "arc_001" / "drafts" / "ch_001.md").write_text("# Ch 1")

    contract = ReplayContract(tmp_path)
    snapshot = contract.capture_inputs("arc_001", "ch_001", "retrieval_active")
    assert snapshot.fingerprint != ""
    assert len(snapshot.input_files) >= 2


def test_replay_contract_deterministic(tmp_path: Path):
    (tmp_path / "canon").mkdir(parents=True, exist_ok=True)
    (tmp_path / "canon" / "approved_outline.md").write_text("# Outline")
    (tmp_path / "arcs" / "arc_001").mkdir(parents=True, exist_ok=True)
    (tmp_path / "arcs" / "arc_001" / "arc_contract.md").write_text("# Contract")
    (tmp_path / "arcs" / "arc_001" / "drafts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "arcs" / "arc_001" / "drafts" / "ch_001.md").write_text("# Ch 1")

    contract = ReplayContract(tmp_path)
    s1 = contract.capture_inputs("arc_001", "ch_001", "retrieval_active")
    s2 = contract.capture_inputs("arc_001", "ch_001", "retrieval_active")
    assert contract.validate_replay(s1, s2) is True


def test_replay_contract_detects_change(tmp_path: Path):
    (tmp_path / "canon").mkdir(parents=True, exist_ok=True)
    (tmp_path / "canon" / "approved_outline.md").write_text("# Outline v1")
    (tmp_path / "arcs" / "arc_001").mkdir(parents=True, exist_ok=True)
    (tmp_path / "arcs" / "arc_001" / "arc_contract.md").write_text("# Contract")
    (tmp_path / "arcs" / "arc_001" / "drafts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "arcs" / "arc_001" / "drafts" / "ch_001.md").write_text("# Ch 1")

    contract = ReplayContract(tmp_path)
    s1 = contract.capture_inputs("arc_001", "ch_001", "retrieval_active")

    # Change outline
    (tmp_path / "canon" / "approved_outline.md").write_text("# Outline v2")
    s2 = contract.capture_inputs("arc_001", "ch_001", "retrieval_active")
    assert contract.validate_replay(s1, s2) is False


# === RebuildDAG ===

def test_dag_levels():
    assert len(RebuildDAG.get_order("minimal")) == 1
    assert len(RebuildDAG.get_order("recommended")) == 3
    assert len(RebuildDAG.get_order("complete")) == 7


def test_dag_downstream():
    downstream = RebuildDAG.get_downstream("summary")
    assert "graph" in downstream
    assert "drift" in downstream


def test_dag_validate_order():
    assert RebuildDAG.validate_order(["summary", "graph", "lifecycle"]) is True
    assert RebuildDAG.validate_order(["graph", "summary"]) is False  # graph before summary


# === BatchStopPropagator ===

def test_batch_stop_propagation():
    propagator = BatchStopPropagator()
    assert propagator.is_stopped() is False
    propagator.propagate(BatchStopSignal(
        reason="stale summary",
        source_chapter="ch_005",
        error_code="SUMMARY_STALE",
    ))
    assert propagator.is_stopped() is True
    assert "SUMMARY_STALE" in propagator.get_stop_reason()


def test_batch_stop_reset():
    propagator = BatchStopPropagator()
    propagator.propagate(BatchStopSignal(reason="test", source_chapter="ch_001"))
    propagator.reset()
    assert propagator.is_stopped() is False

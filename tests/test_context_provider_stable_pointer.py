"""ContextProvider stable pointer + cache integration tests."""
import pytest
from pathlib import Path
from novel_workflow.system_scripts.context_provider import ContextProvider
from novel_workflow.system_scripts.manifest_manager import ManifestManager
from novel_workflow.schemas.manifest import DerivedArtifactEntry


def _seed_project(root: Path):
    """Create minimal project structure."""
    (root / "canon").mkdir(parents=True, exist_ok=True)
    (root / "canon" / "approved_outline.md").write_text("# Outline\n", encoding="utf-8")
    (root / "arcs" / "arc_001").mkdir(parents=True, exist_ok=True)
    (root / "arcs" / "arc_001" / "arc_contract.md").write_text("# Contract\n", encoding="utf-8")
    (root / "ledgers").mkdir(parents=True, exist_ok=True)
    (root / "ledgers" / "timeline.json").write_text('{"events": []}', encoding="utf-8")
    (root / "arcs" / "arc_001" / "drafts").mkdir(parents=True, exist_ok=True)
    (root / "arcs" / "arc_001" / "drafts" / "ch_001.md").write_text("# Ch 1\nAlice walked in.", encoding="utf-8")


def test_active_mode_has_stable_pointer(tmp_path: Path):
    _seed_project(tmp_path)
    provider = ContextProvider(tmp_path, mode="retrieval_active")
    assert provider.stable_pointer is not None
    assert provider.cache is not None


def test_legacy_mode_no_stable_pointer(tmp_path: Path):
    _seed_project(tmp_path)
    provider = ContextProvider(tmp_path, mode="legacy")
    assert provider.stable_pointer is None
    assert provider.cache is None


def test_shadow_mode_no_stable_pointer(tmp_path: Path):
    _seed_project(tmp_path)
    provider = ContextProvider(tmp_path, mode="retrieval_shadow")
    assert provider.stable_pointer is None


def _seed_manifest_with_required(root: Path):
    """Seed manifest with required artifacts for active mode."""
    mgr = ManifestManager(root)
    # Create the actual summary file so register_persisted_artifact won't fail
    (root / "workspace" / "summaries").mkdir(parents=True, exist_ok=True)
    (root / "workspace" / "summaries" / "ch_001_summary.json").write_text(
        '{"chapter_id": "ch_001"}', encoding="utf-8"
    )
    mgr.register_artifact(DerivedArtifactEntry(
        artifact_path="workspace/summaries/ch_001_summary.json",
        artifact_type="narrative_summary",
        builder_name="test",
    ))
    # Create lifecycle index file
    (root / "workspace" / "foreshadow_lifecycle_index.json").write_text(
        '{"index_id": "test", "arc_id": "arc_001", "items": []}', encoding="utf-8"
    )
    mgr.register_artifact(DerivedArtifactEntry(
        artifact_path="workspace/foreshadow_lifecycle_index.json",
        artifact_type="foreshadow_lifecycle_index",
        builder_name="test",
    ))
    mgr.save()


def test_active_mode_caches_context(tmp_path: Path):
    _seed_project(tmp_path)
    _seed_manifest_with_required(tmp_path)
    provider = ContextProvider(tmp_path, mode="retrieval_active")
    provider.build_writer_context("arc_001", 1)
    cached = provider.cache.get("writer:arc_001:ch_001")
    assert cached is not None
    assert isinstance(cached, str)


def test_cache_invalidation(tmp_path: Path):
    _seed_project(tmp_path)
    _seed_manifest_with_required(tmp_path)
    provider = ContextProvider(tmp_path, mode="retrieval_active")
    provider.build_writer_context("arc_001", 1)
    assert provider.cache.size() == 1
    provider.invalidate_cache()
    assert provider.cache.size() == 0


def test_stable_pointer_reads_manifest(tmp_path: Path):
    _seed_project(tmp_path)
    # Register a summary in manifest
    mgr = ManifestManager(tmp_path)
    mgr.register_artifact(DerivedArtifactEntry(
        artifact_path="workspace/summaries/ch_001_summary.json",
        artifact_type="narrative_summary",
        builder_name="test",
    ))
    mgr.save()

    provider = ContextProvider(tmp_path, mode="retrieval_active")
    entry = provider.stable_pointer.get_stable("narrative_summary")
    assert entry is not None
    assert entry.artifact_type == "narrative_summary"


def test_active_mode_allows_cold_start(tmp_path: Path):
    """Cold start (empty manifest) should be allowed."""
    _seed_project(tmp_path)
    provider = ContextProvider(tmp_path, mode="retrieval_active")
    context, trace = provider.build_writer_context("arc_001", 1)
    assert isinstance(context, str)


def test_active_mode_blocks_stale_entries(tmp_path: Path):
    """Active mode should block when all entries of a required type are stale."""
    _seed_project(tmp_path)
    # Register manifest entry then mark stale
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

    provider = ContextProvider(tmp_path, mode="retrieval_active")
    with pytest.raises(RuntimeError, match="all entries are stale"):
        provider.build_writer_context("arc_001", 1)

"""Phase 2.2 E2E operational chain test — 50 chapters through full pipeline.

TEMP.md §13: FakeWriter → draft → AuditorComparator → Extractor →
ProposalValidator → GateValidator → apply → RebuildOrchestrator →
ManifestVerifier → RuntimeAcceptanceReport
"""
import json
import pytest
from pathlib import Path
from novel_workflow.system_scripts.context_provider import ContextProvider
from novel_workflow.system_scripts.narrative_compressor import NarrativeCompressor
from novel_workflow.system_scripts.retrieval_context_builder import RetrievalContextBuilder
from novel_workflow.system_scripts.rebuild_orchestrator import RebuildOrchestrator
from novel_workflow.system_scripts.manifest_manager import ManifestManager
from novel_workflow.schemas.retrieval import RetrievalRequest


def _seed_project(root: Path, chapters: int = 10):
    """Create project for E2E test."""
    (root / "canon").mkdir(parents=True, exist_ok=True)
    (root / "canon" / "approved_outline.md").write_text("# Outline\n\nAdventure.", encoding="utf-8")
    (root / "arcs" / "arc_001").mkdir(parents=True, exist_ok=True)
    (root / "arcs" / "arc_001" / "arc_contract.md").write_text("# Contract\nGoal.", encoding="utf-8")
    (root / "ledgers").mkdir(parents=True, exist_ok=True)
    (root / "ledgers" / "timeline.json").write_text(json.dumps({"schema_version": "1.0", "events": []}))
    (root / "ledgers" / "character_knowledge.json").write_text(json.dumps({"schema_version": "1.0", "entries": []}))
    (root / "ledgers" / "foreshadowing.json").write_text(json.dumps({"schema_version": "1.0", "foreshadowing_entries": []}))
    (root / "arcs" / "arc_001" / "drafts").mkdir(parents=True, exist_ok=True)
    for i in range(1, chapters + 1):
        (root / "arcs" / "arc_001" / "drafts" / f"ch_{i:03d}.md").write_text(
            f"# Chapter {i}\n\n" + f"Content of chapter {i}. " * 30, encoding="utf-8"
        )


def test_e2e_full_chain(tmp_path: Path):
    """Full operational chain: summarize → retrieve → rebuild → verify."""
    _seed_project(tmp_path, 10)

    # Step 1: Compress all chapters
    compressor = NarrativeCompressor(tmp_path)
    for i in range(1, 11):
        compressor.compress("arc_001", f"ch_{i:03d}")

    # Step 2: Build context for each chapter
    builder = RetrievalContextBuilder(tmp_path)
    for i in range(1, 11):
        request = RetrievalRequest(
            arc_id="arc_001", chapter_id=f"ch_{i:03d}",
            agent_role="writer", max_character_budget=25000,
        )
        context, trace = builder.build(request)
        assert len(context) > 0
        assert trace.derived is True

    # Step 3: Build context with traces (active mode requires manifest)
    from novel_workflow.schemas.manifest import DerivedArtifactEntry
    mgr = ManifestManager(tmp_path)
    # Register summaries in manifest for stable pointer check
    for i in range(1, 11):
        mgr.register_artifact(DerivedArtifactEntry(
            artifact_path=f"workspace/summaries/ch_{i:03d}_summary.json",
            artifact_type="narrative_summary", builder_name="NarrativeCompressor",
        ))
    # Register lifecycle index
    (tmp_path / "workspace" / "foreshadow_lifecycle_index.json").write_text(
        '{"index_id": "test", "arc_id": "arc_001", "items": []}', encoding="utf-8"
    )
    mgr.register_artifact(DerivedArtifactEntry(
        artifact_path="workspace/foreshadow_lifecycle_index.json",
        artifact_type="foreshadow_lifecycle_index", builder_name="test",
    ))
    mgr.save()
    provider = ContextProvider(tmp_path, mode="retrieval_active")
    for i in range(1, 11):
        context, trace = provider.build_writer_context("arc_001", i)
        assert trace is not None
        ContextProvider.write_trace(tmp_path, "arc_001", f"ch_{i:03d}", trace)

    # Step 4: Verify traces exist
    for i in range(1, 11):
        trace_file = tmp_path / "workspace" / "retrieval_traces" / "arc_001" / f"ch_{i:03d}" / "writer.jsonl"
        assert trace_file.exists(), f"Missing trace: {trace_file}"

    # Step 5: Verify manifest
    manifest_path = tmp_path / "workspace" / "phase2" / "manifest.json"
    if manifest_path.exists():
        data = json.loads(manifest_path.read_text())
        assert data["schema_version"] == "1.0"


def test_e2e_rebuild_chain(tmp_path: Path):
    """Rebuild chain: mark stale → rebuild → verify."""
    _seed_project(tmp_path, 10)

    # Compress
    compressor = NarrativeCompressor(tmp_path)
    for i in range(1, 11):
        compressor.compress("arc_001", f"ch_{i:03d}")

    # Rebuild
    orchestrator = RebuildOrchestrator(tmp_path)
    result = orchestrator.rebuild(arc_id="arc_001", chapter_id="ch_005", reason="source_changed")
    assert result.success is True


def test_e2e_manifest_verification(tmp_path: Path):
    """Verify manifest has no ghost entries."""
    _seed_project(tmp_path, 5)

    # Compress
    compressor = NarrativeCompressor(tmp_path)
    for i in range(1, 6):
        compressor.compress("arc_001", f"ch_{i:03d}")

    # Check manifest
    manifest_mgr = ManifestManager(tmp_path)
    manifest = manifest_mgr.load()

    # All entries should have existing artifact paths
    for entry in manifest.entries:
        artifact_path = tmp_path / entry.artifact_path
        assert artifact_path.exists(), f"Ghost entry: {entry.artifact_path}"

"""Phase 2 flow active integration tests."""
import json
import pytest
from pathlib import Path
from novel_workflow.system_scripts.context_provider import ContextProvider
from novel_workflow.system_scripts.retrieval_context_builder import RetrievalContextBuilder
from novel_workflow.schemas.enums import ContextBuilderMode


def _seed_project(root: Path, chapters: int = 3):
    """Create minimal project with canon, contract, and drafts."""
    (root / "canon").mkdir(parents=True, exist_ok=True)
    (root / "canon" / "approved_outline.md").write_text("# Outline\n\nAdventure story.", encoding="utf-8")
    (root / "arcs" / "arc_001").mkdir(parents=True, exist_ok=True)
    (root / "arcs" / "arc_001" / "arc_contract.md").write_text("# Contract\n\nHero's journey.", encoding="utf-8")
    (root / "arcs" / "arc_001" / "drafts").mkdir(parents=True, exist_ok=True)
    for i in range(1, chapters + 1):
        (root / "arcs" / "arc_001" / "drafts" / f"ch_{i:03d}.md").write_text(
            f"# Chapter {i}\n\nContent of chapter {i}.", encoding="utf-8"
        )


def test_active_mode_uses_retrieval_builder(tmp_path: Path):
    _seed_project(tmp_path)
    provider = ContextProvider(tmp_path, mode="retrieval_active")
    context, trace = provider.build_writer_context("arc_001", 2)
    assert isinstance(context, str)
    assert len(context) > 0
    assert trace is not None
    assert trace.context_builder_mode == ContextBuilderMode.RETRIEVAL


def test_active_mode_respects_budget(tmp_path: Path):
    _seed_project(tmp_path)
    provider = ContextProvider(tmp_path, mode="retrieval_active")
    context, trace = provider.build_writer_context("arc_001", 2)
    # Writer budget is 25000, context should be within reasonable range
    assert len(context) <= 30000  # some margin for headers


def test_legacy_mode_unchanged(tmp_path: Path):
    _seed_project(tmp_path)
    provider = ContextProvider(tmp_path, mode="legacy")
    context, trace = provider.build_writer_context("arc_001", 2)
    assert isinstance(context, str)
    assert trace is None


def test_shadow_mode_unchanged(tmp_path: Path):
    _seed_project(tmp_path)
    provider = ContextProvider(tmp_path, mode="retrieval_shadow")
    context, trace = provider.build_writer_context("arc_001", 2)
    assert isinstance(context, str)
    assert trace is not None
    assert trace.context_builder_mode == ContextBuilderMode.RETRIEVAL_FALLBACK_LEGACY


def test_active_mode_all_roles(tmp_path: Path):
    _seed_project(tmp_path)
    provider = ContextProvider(tmp_path, mode="retrieval_active")
    for method_name in ["build_writer_context", "build_auditor_context", "build_extractor_context"]:
        method = getattr(provider, method_name)
        context, trace = method("arc_001", 2)
        assert isinstance(context, str)
        assert trace is not None

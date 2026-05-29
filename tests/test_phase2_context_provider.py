"""Phase 2 ContextProvider tests."""
import pytest
from pathlib import Path
from novel_workflow.system_scripts.context_provider import ContextProvider
from novel_workflow.schemas.enums import ContextBuilderMode


def _seed_project(root: Path):
    """Create minimal project structure for _build_context."""
    (root / "arcs" / "arc_001" / "drafts").mkdir(parents=True, exist_ok=True)
    (root / "arcs" / "arc_001" / "drafts" / "ch_001.md").write_text("# Ch 1")
    (root / "canon").mkdir(exist_ok=True)
    (root / "canon" / "approved_outline.md").write_text("# Outline")
    (root / "ledgers").mkdir(exist_ok=True)
    (root / "ledgers" / "timeline.json").write_text('{"events": []}')


def test_legacy_mode_returns_no_trace(tmp_path: Path):
    _seed_project(tmp_path)
    provider = ContextProvider(tmp_path, mode="legacy")
    context, trace = provider.build_writer_context("arc_001", 2)
    assert isinstance(context, str)
    assert len(context) > 0
    assert trace is None


def test_shadow_mode_returns_trace(tmp_path: Path):
    _seed_project(tmp_path)
    provider = ContextProvider(tmp_path, mode="retrieval_shadow")
    context, trace = provider.build_writer_context("arc_001", 2)
    assert isinstance(context, str)
    assert trace is not None
    assert trace.context_builder_mode == ContextBuilderMode.RETRIEVAL_FALLBACK_LEGACY
    assert trace.derived is True
    assert trace.request.agent_role == "writer"
    assert trace.request.arc_id == "arc_001"


def test_all_roles_return_consistent_format(tmp_path: Path):
    _seed_project(tmp_path)
    provider = ContextProvider(tmp_path, mode="retrieval_shadow")
    for method in [provider.build_writer_context, provider.build_auditor_context, provider.build_extractor_context]:
        context, trace = method("arc_001", 2)
        assert isinstance(context, str)
        assert trace is not None


def test_env_variable_override(monkeypatch, tmp_path: Path):
    _seed_project(tmp_path)
    monkeypatch.setenv("NOVEL_WORKFLOW_CONTEXT_MODE", "retrieval_shadow")
    provider = ContextProvider(tmp_path)
    _, trace = provider.build_writer_context("arc_001", 2)
    assert trace is not None


def test_default_mode_is_legacy(tmp_path: Path):
    _seed_project(tmp_path)
    provider = ContextProvider(tmp_path)
    _, trace = provider.build_writer_context("arc_001", 2)
    assert trace is None

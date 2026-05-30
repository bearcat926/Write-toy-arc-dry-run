"""Phase 2 trace failure policy tests."""
import pytest
from pathlib import Path
from novel_workflow.system_scripts.context_provider import ContextProvider, ACTIVE_MODES
from novel_workflow.schemas.retrieval import RetrievalRequest, RetrievalTrace


def test_write_trace_returns_true_on_success(tmp_path: Path):
    request = RetrievalRequest(arc_id="a1", chapter_id="ch_001", agent_role="writer")
    trace = RetrievalTrace(request=request)
    result = ContextProvider.write_trace(tmp_path, "a1", "ch_001", trace)
    assert result is True


def test_write_trace_returns_false_on_failure(tmp_path: Path):
    request = RetrievalRequest(arc_id="a1", chapter_id="ch_001", agent_role="writer")
    trace = RetrievalTrace(request=request)
    # Block directory creation by placing a file
    blocker = tmp_path / "workspace"
    blocker.write_text("blocking")
    result = ContextProvider.write_trace(tmp_path, "a1", "ch_001", trace)
    assert result is False


def test_shadow_mode_is_not_active():
    provider = ContextProvider(Path("/tmp"), mode="retrieval_shadow")
    assert provider.is_active_mode() is False


def test_legacy_mode_is_not_active():
    provider = ContextProvider(Path("/tmp"), mode="legacy")
    assert provider.is_active_mode() is False


def test_active_modes_defined():
    assert "retrieval_active" in ACTIVE_MODES
    assert "arc_active" in ACTIVE_MODES
    assert "retrieval_shadow" not in ACTIVE_MODES
    assert "legacy" not in ACTIVE_MODES


def test_active_mode_returns_true():
    provider = ContextProvider(Path("/tmp"), mode="retrieval_active")
    assert provider.is_active_mode() is True
    provider2 = ContextProvider(Path("/tmp"), mode="arc_active")
    assert provider2.is_active_mode() is True

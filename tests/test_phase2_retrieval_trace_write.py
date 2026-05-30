"""Phase 2 retrieval trace file writing tests."""
import json
from pathlib import Path
from novel_workflow.system_scripts.context_provider import ContextProvider
from novel_workflow.schemas.retrieval import RetrievalRequest, RetrievalTrace
from novel_workflow.schemas.enums import ContextBuilderMode


def test_write_trace_creates_jsonl(tmp_path: Path):
    request = RetrievalRequest(arc_id="a1", chapter_id="ch_001", agent_role="writer")
    trace = RetrievalTrace(request=request, context_builder_mode=ContextBuilderMode.RETRIEVAL_FALLBACK_LEGACY)
    ContextProvider.write_trace(tmp_path, "a1", "ch_001", trace)
    trace_file = tmp_path / "workspace" / "retrieval_traces" / "ch_001.jsonl"
    assert trace_file.exists()
    data = json.loads(trace_file.read_text())
    assert data["derived"] is True


def test_write_trace_append(tmp_path: Path):
    request = RetrievalRequest(arc_id="a1", chapter_id="ch_001", agent_role="writer")
    trace = RetrievalTrace(request=request)
    ContextProvider.write_trace(tmp_path, "a1", "ch_001", trace)
    ContextProvider.write_trace(tmp_path, "a1", "ch_001", trace)
    trace_file = tmp_path / "workspace" / "retrieval_traces" / "ch_001.jsonl"
    lines = trace_file.read_text().strip().split("\n")
    assert len(lines) == 2


def test_write_trace_non_fatal_on_bad_path(tmp_path: Path, capsys):
    """write_trace should not raise even with invalid path."""
    request = RetrievalRequest(arc_id="a1", chapter_id="ch_001", agent_role="writer")
    trace = RetrievalTrace(request=request)
    # Create a file where the directory should be (will fail to mkdir)
    blocker = tmp_path / "workspace"
    blocker.write_text("blocking")
    ContextProvider.write_trace(tmp_path, "a1", "ch_001", trace)
    captured = capsys.readouterr()
    assert "WARNING" in captured.out

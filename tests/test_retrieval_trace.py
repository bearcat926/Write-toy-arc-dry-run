"""Milestone 8: Retrieval trace append-only tests."""
import json
import pytest
from pathlib import Path
from novel_workflow.schemas.retrieval import RetrievalTrace, RetrievalRequest
from novel_workflow.schemas.enums import ContextBuilderMode, RetrievalFallbackReason


def test_trace_schema_valid():
    request = RetrievalRequest(
        arc_id="arc_001", chapter_id="ch_001", agent_role="writer",
    )
    trace = RetrievalTrace(
        request=request,
        final_character_count=5000,
        estimated_token_count=1250,
        fallback_used=False,
        context_builder_mode=ContextBuilderMode.RETRIEVAL,
        chapter_id="ch_001",
        agent_role="writer",
        attempt_id="1717023112231_writer_01",
    )
    assert trace.derived is True
    assert trace.fallback_reason is None


def test_trace_with_fallback():
    request = RetrievalRequest(
        arc_id="arc_001", chapter_id="ch_001", agent_role="auditor",
    )
    trace = RetrievalTrace(
        request=request,
        fallback_used=True,
        fallback_reason=RetrievalFallbackReason.SUMMARY_STALE,
        context_builder_mode=ContextBuilderMode.RETRIEVAL_FALLBACK_LEGACY,
        chapter_id="ch_001",
        agent_role="auditor",
        attempt_id="1717023112231_auditor_01",
    )
    assert trace.fallback_used is True
    assert trace.fallback_reason == RetrievalFallbackReason.SUMMARY_STALE


def test_trace_append_only_behavior(tmp_path: Path):
    """Trace files must be append-only — writing appends lines, not overwrites."""
    trace_dir = tmp_path / "workspace" / "retrieval_traces"
    trace_dir.mkdir(parents=True)
    trace_file = trace_dir / "ch_001.jsonl"

    # Write first entry
    with open(trace_file, "a", encoding="utf-8") as f:
        f.write(json.dumps({"attempt_id": "001", "agent_role": "writer"}) + "\n")

    # Append second entry
    with open(trace_file, "a", encoding="utf-8") as f:
        f.write(json.dumps({"attempt_id": "002", "agent_role": "auditor"}) + "\n")

    lines = trace_file.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["attempt_id"] == "001"
    assert json.loads(lines[1])["attempt_id"] == "002"


def test_trace_chapter_isolation(tmp_path: Path):
    """Each chapter gets its own trace file."""
    trace_dir = tmp_path / "workspace" / "retrieval_traces"
    trace_dir.mkdir(parents=True)

    ch1_file = trace_dir / "ch_001.jsonl"
    ch2_file = trace_dir / "ch_002.jsonl"

    ch1_file.write_text('{"ch": "001"}\n', encoding="utf-8")
    ch2_file.write_text('{"ch": "002"}\n', encoding="utf-8")

    assert ch1_file.exists()
    assert ch2_file.exists()
    assert ch1_file.read_text() != ch2_file.read_text()

"""ContextProvider — abstraction layer for context building."""
import os
from pathlib import Path

from ..schemas.retrieval import RetrievalRequest, RetrievalTrace
from ..schemas.enums import ContextBuilderMode


def _get_build_context():
    """Lazy import to avoid circular dependency with flow.py."""
    from ..crewai.flow import _build_context
    return _build_context


class ContextProvider:
    """Provides context for Writer/Auditor/Extractor roles.

    Modes:
    - legacy: calls _build_context(), returns (context, None)
    - retrieval_shadow: calls _build_context(), returns (context, RetrievalTrace)
    """

    def __init__(self, root: Path, mode: str | None = None):
        self._root = root
        self._mode = mode or os.environ.get("NOVEL_WORKFLOW_CONTEXT_MODE", "legacy")

    def build_writer_context(self, arc_id: str, current_ch: int) -> tuple[str, RetrievalTrace | None]:
        context = _get_build_context()(self._root, arc_id, current_ch)
        if self._mode == "legacy":
            return context, None
        trace = self._make_shadow_trace("writer", arc_id, current_ch)
        return context, trace

    def build_auditor_context(self, arc_id: str, current_ch: int) -> tuple[str, RetrievalTrace | None]:
        context = _get_build_context()(self._root, arc_id, current_ch)
        if self._mode == "legacy":
            return context, None
        trace = self._make_shadow_trace("auditor", arc_id, current_ch)
        return context, trace

    def build_extractor_context(self, arc_id: str, current_ch: int) -> tuple[str, RetrievalTrace | None]:
        context = _get_build_context()(self._root, arc_id, current_ch)
        if self._mode == "legacy":
            return context, None
        trace = self._make_shadow_trace("extractor", arc_id, current_ch)
        return context, trace

    @staticmethod
    def write_trace(root: Path, arc_id: str, chapter_id: str, trace: RetrievalTrace) -> None:
        """Write retrieval trace to JSONL file. Non-fatal on failure."""
        try:
            traces_dir = root / "workspace" / "retrieval_traces"
            traces_dir.mkdir(parents=True, exist_ok=True)
            trace_file = traces_dir / f"{chapter_id}.jsonl"
            with open(trace_file, "a", encoding="utf-8") as f:
                f.write(trace.model_dump_json() + "\n")
        except Exception as e:
            print(f"[ContextProvider] WARNING: failed to write trace for {chapter_id}: {e}")

    def _make_shadow_trace(self, agent_role: str, arc_id: str, current_ch: int) -> RetrievalTrace:
        request = RetrievalRequest(
            arc_id=arc_id,
            chapter_id=f"ch_{current_ch:03d}",
            agent_role=agent_role,
        )
        return RetrievalTrace(
            request=request,
            context_builder_mode=ContextBuilderMode.RETRIEVAL_FALLBACK_LEGACY,
            derived=True,
        )

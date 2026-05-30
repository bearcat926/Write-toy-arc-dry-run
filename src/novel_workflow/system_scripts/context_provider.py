"""ContextProvider — abstraction layer for context building."""
import os
from pathlib import Path

from ..schemas.retrieval import RetrievalRequest, RetrievalTrace
from ..schemas.enums import ContextBuilderMode

ACTIVE_MODES = {"retrieval_active", "arc_active"}

# Budget per role for active mode
_ROLE_BUDGETS = {
    "writer": 25000,
    "auditor": 30000,
    "extractor": 12000,
}


def _get_build_context():
    """Lazy import to avoid circular dependency with flow.py."""
    from ..crewai.flow import _build_context
    return _build_context


class ContextProvider:
    """Provides context for Writer/Auditor/Extractor roles.

    Modes:
    - legacy: calls _build_context(), returns (context, None)
    - retrieval_shadow: calls _build_context(), returns (context, RetrievalTrace)
    - retrieval_active: uses RetrievalContextBuilder with budget control,
        StablePointer for stable reads, GenerationCache for caching
    """

    def __init__(self, root: Path, mode: str | None = None):
        self._root = root
        self._mode = mode or os.environ.get("NOVEL_WORKFLOW_CONTEXT_MODE", "legacy")
        # Stable pointer and cache for active modes
        self._stable_pointer = None
        self._cache = None
        if self.is_active_mode():
            from .stable_generation_pointer import StableGenerationPointer
            from .generation_cache import GenerationCache
            self._stable_pointer = StableGenerationPointer(root)
            self._cache = GenerationCache()

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def stable_pointer(self):
        """Access the StableGenerationPointer (active modes only)."""
        return self._stable_pointer

    @property
    def cache(self):
        """Access the GenerationCache (active modes only)."""
        return self._cache

    def is_active_mode(self) -> bool:
        """Return True if current mode requires hard fail on trace errors."""
        return self._mode in ACTIVE_MODES

    def get_failure_isolation(self) -> str:
        """Return the failure isolation policy for the current mode."""
        from ..config import FAILURE_ISOLATION_DEFAULTS, ACTIVE_FAILURE_MODES
        env_val = os.environ.get("NOVEL_WORKFLOW_FAILURE_ISOLATION")
        if env_val:
            if env_val not in ("strict", "chapter", "best_effort"):
                raise ValueError(f"Invalid NOVEL_WORKFLOW_FAILURE_ISOLATION: {env_val}")
            if self.is_active_mode() and env_val not in ACTIVE_FAILURE_MODES:
                raise ValueError(
                    f"Active mode '{self._mode}' cannot use failure_isolation='{env_val}'"
                )
            return env_val
        return FAILURE_ISOLATION_DEFAULTS.get(self._mode, "best_effort")

    def build_writer_context(self, arc_id: str, current_ch: int) -> tuple[str, RetrievalTrace | None]:
        if self._mode == "retrieval_active":
            return self._build_active_context("writer", arc_id, current_ch)
        context = _get_build_context()(self._root, arc_id, current_ch)
        if self._mode == "legacy":
            return context, None
        # retrieval_shadow
        trace = self._make_shadow_trace("writer", arc_id, current_ch)
        return context, trace

    def build_auditor_context(self, arc_id: str, current_ch: int) -> tuple[str, RetrievalTrace | None]:
        if self._mode == "retrieval_active":
            return self._build_active_context("auditor", arc_id, current_ch)
        context = _get_build_context()(self._root, arc_id, current_ch)
        if self._mode == "legacy":
            return context, None
        trace = self._make_shadow_trace("auditor", arc_id, current_ch)
        return context, trace

    def build_extractor_context(self, arc_id: str, current_ch: int) -> tuple[str, RetrievalTrace | None]:
        if self._mode == "retrieval_active":
            return self._build_active_context("extractor", arc_id, current_ch)
        context = _get_build_context()(self._root, arc_id, current_ch)
        if self._mode == "legacy":
            return context, None
        trace = self._make_shadow_trace("extractor", arc_id, current_ch)
        return context, trace

    def _build_active_context(self, agent_role: str, arc_id: str, current_ch: int) -> tuple[str, RetrievalTrace]:
        """Build context using RetrievalContextBuilder for active mode."""
        from .retrieval_context_builder import RetrievalContextBuilder
        builder = RetrievalContextBuilder(self._root)
        budget = _ROLE_BUDGETS.get(agent_role, 12000)
        request = RetrievalRequest(
            arc_id=arc_id,
            chapter_id=f"ch_{current_ch:03d}",
            agent_role=agent_role,
            max_character_budget=budget,
        )
        context, trace = builder.build(request)

        # Cache the context for this chapter
        if self._cache:
            cache_key = f"{agent_role}:{arc_id}:ch_{current_ch:03d}"
            self._cache.put(cache_key, context)

        return context, trace

    def invalidate_cache(self, generation_id: str = "") -> int:
        """Invalidate cached context entries. If generation_id given, invalidate only that generation."""
        if not self._cache:
            return 0
        if generation_id:
            return self._cache.invalidate_generation(generation_id)
        self._cache.clear()
        return 0

    @staticmethod
    def write_trace(root: Path, arc_id: str, chapter_id: str, trace: RetrievalTrace) -> bool:
        """Write retrieval trace to JSONL file. Returns True on success."""
        try:
            traces_dir = root / "workspace" / "retrieval_traces"
            traces_dir.mkdir(parents=True, exist_ok=True)
            trace_file = traces_dir / f"{chapter_id}.jsonl"
            with open(trace_file, "a", encoding="utf-8") as f:
                f.write(trace.model_dump_json() + "\n")
            return True
        except Exception as e:
            print(f"[ContextProvider] WARNING: failed to write trace for {chapter_id}: {e}")
            return False

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

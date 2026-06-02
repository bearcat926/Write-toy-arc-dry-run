"""Hybrid Narrative Retriever — Phase 3 D-05, D-06, D-10.

Combines BM25, Vector, and Graph expansion results using Reciprocal Rank
Fusion (RRF), with optional reranker, role profile filtering,
budget trimming, and RetrievalTrace output (D-10).

This is the unified retrieval entry point for Phase 3.
"""

import math
import time as _time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .bm25_retriever import BM25Retriever, BM25Result
    from .vector_adapter import VectorAdapter, VectorResult
    from ..schemas.retrieval import RetrievalRequest, RetrievalTrace, RetrievedContextItem
    from ..schemas.enums import RetrievalFallbackReason, ContextBuilderMode


@dataclass
class FusedResult:
    """A single fused retrieval result with RRF score."""
    item_id: str
    item_type: str = ""
    content: str = ""
    source_layer: str = ""
    chapter_id: str = ""
    arc_id: str = ""
    trust_level: str = ""
    bm25_score: float = 0.0
    vector_score: float = 0.0
    graph_score: float = 0.0
    rrf_score: float = 0.0
    source: str = ""  # "bm25" | "vector" | "graph" | "fusion"

    def to_context_item(self) -> dict:
        return {
            "item_id": self.item_id,
            "item_type": self.item_type,
            "content": self.content,
            "source_layer": self.source_layer,
            "source": self.source,
        }


@dataclass
class RetrievalPlan:
    """Retrieval configuration for a single query."""
    profile: str = "writer"  # "writer" | "auditor" | "extractor"
    enable_bm25: bool = True
    enable_vector: bool = True
    enable_graph: bool = False
    top_k_per_source: int = 20
    fusion_k: int = 60  # RRF k parameter
    max_results: int = 30
    char_budget: int = 8000
    sort_by: str = "rrf"  # "rrf" | "bm25" | "source"


# Profile-specific weights and filters
PROFILE_CONFIG = {
    "writer": {
        "preferred_types": ["chapter", "character", "foreshadow", "summary"],
        "vector_weight": 0.4,
        "bm25_weight": 0.6,
        "graph_weight": 0.3,
        "min_trust": "derived_summary",
    },
    "auditor": {
        "preferred_types": ["chapter", "timeline", "character"],
        "vector_weight": 0.3,
        "bm25_weight": 0.7,
        "graph_weight": 0.0,
        "min_trust": "canonical",
    },
    "extractor": {
        "preferred_types": ["chapter", "timeline"],
        "vector_weight": 0.3,
        "bm25_weight": 0.7,
        "graph_weight": 0.0,
        "min_trust": "canonical",
    },
}

TRUST_LEVEL_RANK = {
    "canonical": 100,
    "ledger_fact": 90,
    "working_state": 80,
    "derived_summary": 55,
    "derived_graph": 50,
    "derived_lifecycle": 45,
    "derived_drift": 35,
    "derived_arc_plan": 30,
    "runtime_context": 10,
}


class HybridRetriever:
    """Unified retrieval that fuses BM25, Vector, and Graph results.

    Usage:
        hr = HybridRetriever(bm25_retriever, vector_adapter, graph_builder)
        results = hr.retrieve("character conflict foreshadow", plan=RetrievalPlan())
    """

    def __init__(
        self,
        bm25: "BM25Retriever",
        vector_adapter: "VectorAdapter | None" = None,
        graph_expander: "GraphExpander | None" = None,
    ):
        self._bm25 = bm25
        self._vector = vector_adapter
        self._graph = graph_expander
        # Trace state (populated by last retrieve call)
        self._last_query = ""
        self._last_plan: RetrievalPlan | None = None
        self._last_all_items: list[FusedResult] = []
        self._last_selected: list[FusedResult] = []
        self._last_dropped: list[FusedResult] = []
        self._last_fallback: tuple[bool, list[str]] = (False, [])

    def retrieve(
        self,
        query: str,
        plan: RetrievalPlan | None = None,
    ) -> list[FusedResult]:
        """Execute retrieval with all enabled sources."""
        if plan is None:
            plan = RetrievalPlan()

        profile_cfg = PROFILE_CONFIG.get(plan.profile, PROFILE_CONFIG["writer"])
        all_results: dict[str, FusedResult] = {}
        fallback_used = False
        fallback_reasons: list[str] = []

        # --- BM25 ---
        if plan.enable_bm25:
            bm25_results = self._bm25.search(
                query,
                top_k=plan.top_k_per_source,
                item_types=profile_cfg.get("preferred_types"),
            )
            for r in bm25_results:
                fr = self._make_fused(r, "bm25")
                if fr.item_id in all_results:
                    all_results[fr.item_id].bm25_score = fr.bm25_score
                else:
                    all_results[fr.item_id] = fr

        # --- Vector ---
        if plan.enable_vector and self._vector:
            if self._vector.is_available():
                vec_results = self._vector.search(query, top_k=plan.top_k_per_source)
                for r in vec_results:
                    if r.item_id in all_results:
                        all_results[r.item_id].vector_score = r.score
                    else:
                        fr = FusedResult(
                            item_id=r.item_id,
                            content=r.content_snippet,
                            vector_score=r.score,
                            source="vector",
                        )
                        all_results[r.item_id] = fr
            else:
                fallback_used = True
                fallback_reasons.append("vector_unavailable")

        # --- Graph Expansion ---
        if plan.enable_graph and self._graph:
            graph_results = self._graph.expand(
                query,
                top_k=min(plan.top_k_per_source, 10),
            )
            for r in graph_results:
                if r.item_id in all_results:
                    all_results[r.item_id].graph_score = r.score
                else:
                    fr = FusedResult(
                        item_id=r.item_id,
                        content=r.content,
                        graph_score=r.score,
                        source="graph",
                    )
                    all_results[r.item_id] = fr

        # --- RRF Fusion (D-06) ---
        all_items = list(all_results.values())
        self._compute_rrf(all_items, k=plan.fusion_k)

        # Store trace data before trimming
        self._last_query = query
        self._last_plan = plan
        self._last_all_items = list(all_items)  # Copy before trimming
        self._last_fallback = (fallback_used, fallback_reasons)

        # Sort
        if plan.sort_by == "rrf":
            all_items.sort(key=lambda x: x.rrf_score, reverse=True)

        # --- Budget trimming ---
        selected = self._trim_budget(all_items, plan.char_budget, plan.max_results)

        # Store trace metadata
        selected_ids = {s.item_id for s in selected}
        self._last_selected = selected
        self._last_dropped = [r for r in all_items if r.item_id not in selected_ids]

        return selected

    def get_last_trace(self) -> dict:
        """Get trace data from the last retrieve() call (D-10).

        Returns a dict with selected_items, dropped_items, scores, reasons, and fallback info.
        Compatible with RetrievalTrace schema.
        """
        selected = []
        for r in self._last_selected:
            selected.append({
                "item_id": r.item_id,
                "item_type": r.item_type,
                "content_snippet": r.content[:200] if r.content else "",
                "source": r.source,
                "bm25_score": r.bm25_score,
                "vector_score": r.vector_score,
                "graph_score": r.graph_score,
                "rrf_score": r.rrf_score,
                "trust_level": r.trust_level,
                "source_layer": r.source_layer,
                "chapter_id": r.chapter_id,
            })

        dropped = []
        for r in self._last_dropped:
            dropped.append({
                "item_id": r.item_id,
                "item_type": r.item_type,
                "reason": "budget_trimmed",
                "score": r.rrf_score,
                "source": r.source,
            })

        fallback_used, fallback_reasons = self._last_fallback

        return {
            "query": self._last_query,
            "profile": self._last_plan.profile if self._last_plan else "writer",
            "selected_items": selected,
            "dropped_items": dropped,
            "selected_count": len(selected),
            "dropped_count": len(dropped),
            "total_candidates": len(self._last_all_items),
            "final_char_count": sum(len(r.content) for r in self._last_selected),
            "fallback_used": fallback_used,
            "fallback_reasons": fallback_reasons,
            "sources_used": list(set(r.source for r in self._last_all_items)),
        }

    # ================================================================
    # RRF Fusion
    # ================================================================

    @staticmethod
    def _compute_rrf(
        items: list[FusedResult],
        k: int = 60,
    ) -> None:
        """Compute RRF scores for a list of FusedResult (mutates in-place).

        Reciprocal Rank Fusion: merge ranked lists from multiple sources.
        RRF score for item i from source s at rank r:
            score(i, s) = 1 / (k + r_s(i))
        k = 60 is the standard value.
        """
        # Rank BM25 results (lower score = better match for BM25)
        bm25_sorted = sorted(
            [r for r in items if r.bm25_score > 0],
            key=lambda x: x.bm25_score,
        )
        # Rank vector results (higher score = better)
        vec_sorted = sorted(
            [r for r in items if r.vector_score > 0],
            key=lambda x: x.vector_score,
            reverse=True,
        )
        # Rank graph results
        graph_sorted = sorted(
            [r for r in items if r.graph_score > 0],
            key=lambda x: x.graph_score,
            reverse=True,
        )

        for rank, r in enumerate(bm25_sorted):
            r.rrf_score += 1.0 / (k + rank + 1)
        for rank, r in enumerate(vec_sorted):
            r.rrf_score += 1.0 / (k + rank + 1)
        for rank, r in enumerate(graph_sorted):
            r.rrf_score += 1.0 / (k + rank + 1)

    # ================================================================
    # Budget trimming
    # ================================================================

    @staticmethod
    def _trim_budget(
        results: list[FusedResult],
        char_budget: int,
        max_results: int,
    ) -> list[FusedResult]:
        """Trim results to fit within character budget and max count."""
        trimmed = []
        total_chars = 0

        for r in results:
            if len(trimmed) >= max_results:
                break
            content_len = len(r.content)
            if total_chars + content_len > char_budget and trimmed:
                # Skip if would exceed budget (but always include at least 1)
                continue
            trimmed.append(r)
            total_chars += content_len

        return trimmed

    # ================================================================
    # Helpers
    # ================================================================

    @staticmethod
    def _make_fused(bm25_result, source: str) -> FusedResult:
        """Convert BM25Result to FusedResult."""
        return FusedResult(
            item_id=bm25_result.item_id,
            item_type=bm25_result.item_type,
            content=bm25_result.content,
            source_layer=bm25_result.source_layer,
            chapter_id=bm25_result.chapter_id,
            arc_id=bm25_result.arc_id,
            trust_level=bm25_result.trust_level,
            bm25_score=bm25_result.score,
            source=source,
        )


class GraphExpander:
    """Graph-based expansion for retrieval (D-05).

    Uses the existing NarrativeGraphIndex to find related nodes
    by character, location, foreshadow, and arc relationships.

    Currently a stub that provides keyword-based expansion.
    Full implementation requires NarrativeGraphBuilder integration.
    """

    def __init__(self, root: Path):
        self._root = root
        self._graph_index = self._load_graph()

    def _load_graph(self) -> dict:
        """Load narrative graph index if available."""
        graph_path = self._root / "workspace" / "narrative_graph_index.json"
        if graph_path.exists():
            import json
            try:
                return json.loads(graph_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"nodes": {}, "edges": []}

    def expand(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[FusedResult]:
        """Expand query results using graph relationships.

        For now, this is a keyword-based expansion that searches
        graph node names for query terms and returns neighbor nodes.
        """
        results: list[FusedResult] = []
        query_lower = query.lower()

        nodes = self._graph_index.get("nodes", {})
        edges = self._graph_index.get("edges", [])

        # Find matching nodes by name
        matched_ids: set[str] = set()
        for node_id, node_data in nodes.items():
            name = node_data.get("name", "")
            node_type = node_data.get("type", "")
            if any(term in name.lower() for term in query_lower.split()):
                matched_ids.add(node_id)

        # Expand to neighbors (1-hop)
        for edge in edges:
            source = edge.get("source", "")
            target = edge.get("target", "")
            edge_type = edge.get("type", "")

            if source in matched_ids and target in nodes:
                target_data = nodes[target]
                results.append(FusedResult(
                    item_id=f"graph:{target}",
                    item_type="graph",
                    content=f"[{edge_type}] {target_data.get('name', target)}: "
                            f"{target_data.get('description', '')}",
                    graph_score=0.5,
                    source="graph",
                ))
            elif target in matched_ids and source in nodes:
                source_data = nodes[source]
                results.append(FusedResult(
                    item_id=f"graph:{source}",
                    item_type="graph",
                    content=f"[{edge_type}] {source_data.get('name', source)}: "
                            f"{source_data.get('description', '')}",
                    graph_score=0.5,
                    source="graph",
                ))

        return results[:top_k]

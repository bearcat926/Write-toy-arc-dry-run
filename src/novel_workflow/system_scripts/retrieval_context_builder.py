"""RetrievalContextBuilder — selects context items with budget control.

Replaces naive _build_context() with traceable, budgeted context selection.
"""
import json
from pathlib import Path, PurePosixPath

from ..schemas.retrieval import (
    RetrievalRequest,
    RetrievedContextItem,
    RetrievalTrace,
    retrieval_sort_key,
)
from ..schemas.enums import (
    RetrievalTrustLevel,
    SourceLayer,
    ContextBuilderMode,
)
from ..schemas.hash_utils import canonical_sha256_file


class RetrievalContextBuilder:
    """Selects relevant context items for Writer/Auditor/Extractor roles."""

    def __init__(self, root: Path):
        self._root = root

    def build(self, request: RetrievalRequest) -> tuple[str, RetrievalTrace]:
        """Build context string and retrieval trace.

        Args:
            request: Retrieval request with arc_id, chapter_id, agent_role, budget

        Returns:
            (context_string, retrieval_trace)
        """
        items = self._collect_items(request)
        selected, dropped = self._select_and_budget(items, request.max_character_budget)
        context = self._render_context(selected)
        trace = self._make_trace(request, selected, dropped)
        return context, trace

    def _collect_items(self, request: RetrievalRequest) -> list[RetrievedContextItem]:
        """Collect available context items from canon, contracts, and summaries."""
        items = []

        # 1. Canon outline
        outline_path = self._root / "canon" / "approved_outline.md"
        if outline_path.exists():
            content = outline_path.read_text(encoding="utf-8", errors="replace")
            items.append(RetrievedContextItem(
                item_id="canon_outline",
                item_type="outline",
                content=content,
                source_layer=SourceLayer.CANON,
                source_artifact="canon/approved_outline.md",
                source_artifact_hash=canonical_sha256_file(outline_path),
                trust_level=RetrievalTrustLevel.CANONICAL,
                relevance_reason="Story outline and structure",
                priority=100,
                selection_reason="score_canonical",
            ))

        # 2. Arc contract
        contract_path = self._root / "arcs" / request.arc_id / "arc_contract.md"
        if contract_path.exists():
            content = contract_path.read_text(encoding="utf-8", errors="replace")
            items.append(RetrievedContextItem(
                item_id=f"arc_contract_{request.arc_id}",
                item_type="arc_contract",
                content=content,
                source_layer=SourceLayer.CANON,
                source_artifact=f"arcs/{request.arc_id}/arc_contract.md",
                source_artifact_hash=canonical_sha256_file(contract_path),
                trust_level=RetrievalTrustLevel.CANONICAL,
                relevance_reason="Arc contract and goals",
                priority=90,
                selection_reason="score_canonical",
            ))

        # 3. Chapter summaries (from NarrativeCompressor output)
        summaries_dir = self._root / "workspace" / "summaries"
        if summaries_dir.exists():
            for summary_file in sorted(summaries_dir.glob("ch_*_summary.json")):
                try:
                    data = json.loads(summary_file.read_text(encoding="utf-8"))
                    ch_id = data.get("chapter_id", summary_file.stem)
                    # Skip current chapter's summary (if it exists)
                    if ch_id == request.chapter_id:
                        continue
                    content_parts = []
                    for field in ("causal_events", "character_state_changes",
                                  "emotional_residue", "unresolved_tensions",
                                  "promises_created", "foreshadow_updates"):
                        values = data.get(field, [])
                        if values:
                            content_parts.append(f"{field}: {json.dumps(values, ensure_ascii=False)}")
                    if not content_parts:
                        content_parts = [f"Summary for {ch_id}"]
                    items.append(RetrievedContextItem(
                        item_id=f"summary_{ch_id}",
                        item_type="narrative_summary",
                        content="\n".join(content_parts),
                        source_layer=SourceLayer.DRAFT,
                        source_artifact=f"workspace/summaries/{summary_file.name}",
                        source_artifact_hash=data.get("source_artifact_hash", ""),
                        is_derived=True,
                        trust_level=RetrievalTrustLevel.DERIVED_SUMMARY,
                        relevance_reason=f"Chapter {ch_id} summary",
                        priority=50,
                        selection_reason="score_derived_summary",
                    ))
                except (json.JSONDecodeError, KeyError):
                    continue

        # 4. Narrative graph index (if available)
        graph_path = self._root / "workspace" / "narrative_graph_index.json"
        if graph_path.exists():
            try:
                data = json.loads(graph_path.read_text(encoding="utf-8"))
                nodes = data.get("nodes", [])
                edges = data.get("edges", [])
                # Include actual node/edge data for retrieval
                content_parts = [f"Narrative graph: {len(nodes)} nodes, {len(edges)} edges"]
                # Add character nodes
                char_nodes = [n for n in nodes if n.get("node_type") == "character"]
                if char_nodes:
                    content_parts.append("Characters: " + ", ".join(
                        n.get("label", n.get("node_id", "?")) for n in char_nodes[:20]
                    ))
                # Add active foreshadow edges
                fs_edges = [e for e in edges if e.get("edge_type") == "foreshadow"]
                if fs_edges:
                    content_parts.append("Foreshadow links: " + "; ".join(
                        f"{e.get('source_id', '?')} → {e.get('target_id', '?')}"
                        for e in fs_edges[:15]
                    ))
                # Add relationship edges
                rel_edges = [e for e in edges if e.get("edge_type") == "relationship"]
                if rel_edges:
                    content_parts.append("Relationships: " + "; ".join(
                        f"{e.get('source_id', '?')} → {e.get('target_id', '?')}"
                        for e in rel_edges[:15]
                    ))
                items.append(RetrievedContextItem(
                    item_id="narrative_graph_index",
                    item_type="narrative_graph_index",
                    content="\n".join(content_parts),
                    is_derived=True,
                    trust_level=RetrievalTrustLevel.DERIVED_GRAPH,
                    relevance_reason="Narrative structure graph",
                    priority=40,
                    selection_reason="score_derived_graph",
                ))
            except (json.JSONDecodeError, KeyError):
                pass

        # 5. Foreshadow lifecycle index (if available)
        lifecycle_path = self._root / "workspace" / "foreshadow_lifecycle_index.json"
        if lifecycle_path.exists():
            try:
                data = json.loads(lifecycle_path.read_text(encoding="utf-8"))
                items_data = data.get("items", [])
                active_items = [it for it in items_data
                                if it.get("current_state") in ("activated", "escalated")]
                content_parts = [
                    f"Foreshadow lifecycle: {len(items_data)} items, {len(active_items)} active",
                ]
                # Include active foreshadow details
                for it in active_items[:20]:
                    label = it.get("label", it.get("foreshadow_id", "?"))
                    state = it.get("current_state", "?")
                    priority = it.get("priority", "?")
                    introduced = it.get("introduced_chapter", "?")
                    content_parts.append(
                        f"  [{state}] {label} (priority={priority}, since {introduced})"
                    )
                items.append(RetrievedContextItem(
                    item_id="foreshadow_lifecycle_index",
                    item_type="foreshadow_lifecycle_index",
                    content="\n".join(content_parts),
                    is_derived=True,
                    trust_level=RetrievalTrustLevel.DERIVED_LIFECYCLE,
                    relevance_reason="Foreshadow lifecycle state",
                    priority=35,
                    selection_reason="score_derived_lifecycle",
                ))
            except (json.JSONDecodeError, KeyError):
                pass

        return items

    def _select_and_budget(
        self, items: list[RetrievedContextItem], budget: int
    ) -> tuple[list[RetrievedContextItem], list[dict]]:
        """Select items within budget, record dropped items."""
        sorted_items = sorted(items, key=retrieval_sort_key)
        selected = []
        dropped = []
        used = 0

        for item in sorted_items:
            item_len = len(item.content)
            if used + item_len <= budget:
                selected.append(item)
                used += item_len
            else:
                dropped.append({
                    "item_id": item.item_id,
                    "drop_reason": "budget_exceeded",
                    "content_length": item_len,
                    "budget_remaining": budget - used,
                })

        return selected, dropped

    def _render_context(self, selected: list[RetrievedContextItem]) -> str:
        """Render selected items into a context string."""
        parts = []
        for item in selected:
            parts.append(f"## {item.relevance_reason}\n{item.content}")
        return "\n\n".join(parts) if parts else "(no context available)"

    def _make_trace(
        self,
        request: RetrievalRequest,
        selected: list[RetrievedContextItem],
        dropped: list[dict],
    ) -> RetrievalTrace:
        """Generate retrieval trace."""
        total_chars = sum(len(item.content) for item in selected)
        return RetrievalTrace(
            request=request,
            selected_items=selected,
            dropped_items=dropped,
            final_character_count=total_chars,
            context_builder_mode=ContextBuilderMode.RETRIEVAL,
            derived=True,
            chapter_id=request.chapter_id,
            agent_role=request.agent_role,
        )

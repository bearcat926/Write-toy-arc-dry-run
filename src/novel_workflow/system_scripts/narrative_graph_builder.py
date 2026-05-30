"""NarrativeGraphBuilder — deterministic projection from ledgers + summaries.

Projects timeline events, character knowledge, foreshadowing entries,
and chapter summaries into a NarrativeGraphIndex.
"""
import json
from pathlib import Path

from ..schemas.narrative_graph import NarrativeNode, NarrativeEdge, NarrativeGraphIndex


class NarrativeGraphBuilder:
    """Builds NarrativeGraphIndex from ledgers and summaries."""

    def __init__(self, root: Path):
        self._root = root

    def build(self, arc_id: str | None = None) -> NarrativeGraphIndex:
        """Build narrative graph from all available sources."""
        nodes: list[NarrativeNode] = []
        edges: list[NarrativeEdge] = []
        generated_from: list[str] = []
        node_counter = 0
        edge_counter = 0

        # 1. Timeline events → event nodes
        timeline_path = self._root / "ledgers" / "timeline.json"
        if timeline_path.exists():
            timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
            generated_from.append("ledgers/timeline.json")
            for evt in timeline.get("events", []):
                node_counter += 1
                nodes.append(NarrativeNode(
                    node_id=f"event_{node_counter:03d}",
                    node_type="event",
                    label=evt.get("event_id", f"evt_{node_counter}"),
                    summary=evt.get("summary", ""),
                    source_artifacts=["ledgers/timeline.json"],
                ))
                # Participants → character-event edges
                for participant in evt.get("participants", []):
                    char_node_id = f"char_{participant}"
                    # Find or note character node
                    edge_counter += 1
                    edges.append(NarrativeEdge(
                        edge_id=f"edge_{edge_counter:03d}",
                        from_node=char_node_id,
                        to_node=f"event_{node_counter:03d}",
                        relation_type="changes",
                        evidence=f"Participated in {evt.get('event_id', '')}",
                        source_artifacts=["ledgers/timeline.json"],
                    ))

        # 2. Character knowledge → character nodes
        ck_path = self._root / "ledgers" / "character_knowledge.json"
        if ck_path.exists():
            ck = json.loads(ck_path.read_text(encoding="utf-8"))
            generated_from.append("ledgers/character_knowledge.json")
            seen_chars: set[str] = set()
            for entry in ck.get("character_knowledge_entries", []):
                char_id = entry.get("character_id", "")
                if char_id and char_id not in seen_chars:
                    seen_chars.add(char_id)
                    node_counter += 1
                    nodes.append(NarrativeNode(
                        node_id=f"char_{char_id}",
                        node_type="character",
                        label=char_id,
                        summary=f"Character: {char_id}",
                        source_artifacts=["ledgers/character_knowledge.json"],
                    ))

        # 3. Foreshadowing → foreshadow nodes
        fs_path = self._root / "ledgers" / "foreshadowing.json"
        if fs_path.exists():
            fs = json.loads(fs_path.read_text(encoding="utf-8"))
            generated_from.append("ledgers/foreshadowing.json")
            for entry in fs.get("foreshadowing_entries", []):
                node_counter += 1
                fs_node_id = f"fs_{node_counter:03d}"
                nodes.append(NarrativeNode(
                    node_id=fs_node_id,
                    node_type="foreshadow",
                    label=entry.get("foreshadow_id", f"fs_{node_counter}"),
                    summary=entry.get("summary", ""),
                    source_artifacts=["ledgers/foreshadowing.json"],
                ))

        # 4. Chapter summaries → summary nodes + emotional_residue
        summaries_dir = self._root / "workspace" / "summaries"
        if summaries_dir.exists():
            for summary_file in sorted(summaries_dir.glob("ch_*_summary.json")):
                try:
                    data = json.loads(summary_file.read_text(encoding="utf-8"))
                    generated_from.append(f"workspace/summaries/{summary_file.name}")
                    ch_id = data.get("chapter_id", summary_file.stem)

                    # Causal events → event nodes
                    for evt in data.get("causal_events", []):
                        node_counter += 1
                        nodes.append(NarrativeNode(
                            node_id=f"ch_{ch_id}_evt_{node_counter:03d}",
                            node_type="event",
                            label=f"{ch_id} event",
                            summary=evt if isinstance(evt, str) else json.dumps(evt),
                            source_artifacts=[f"workspace/summaries/{summary_file.name}"],
                        ))

                    # Emotional residue → emotional_residue nodes
                    for residue in data.get("emotional_residue", []):
                        node_counter += 1
                        nodes.append(NarrativeNode(
                            node_id=f"ch_{ch_id}_er_{node_counter:03d}",
                            node_type="emotional_residue",
                            label=f"{ch_id} emotion",
                            summary=residue if isinstance(residue, str) else json.dumps(residue),
                            source_artifacts=[f"workspace/summaries/{summary_file.name}"],
                        ))

                    # Foreshadow updates → edges
                    for fs_update in data.get("foreshadow_updates", []):
                        edge_counter += 1
                        edges.append(NarrativeEdge(
                            edge_id=f"edge_{edge_counter:03d}",
                            from_node=ch_id,
                            to_node="foreshadow",
                            relation_type="foreshadows",
                            evidence=fs_update if isinstance(fs_update, str) else json.dumps(fs_update),
                            source_artifacts=[f"workspace/summaries/{summary_file.name}"],
                        ))
                except (json.JSONDecodeError, KeyError):
                    continue

        return NarrativeGraphIndex(
            graph_id=f"graph_{arc_id or 'global'}",
            arc_id=arc_id,
            generated_from=generated_from,
            nodes=nodes,
            edges=edges,
        )

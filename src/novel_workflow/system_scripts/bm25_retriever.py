"""BM25/FTS5 Narrative Retriever — Phase 3 D-01, D-02.

Local-first, dependency-free text retrieval using SQLite FTS5 with BM25 ranking.
Provides baseline retrieval for chapters, characters, foreshadows, and summaries.

Architecture:
    Build: scan canon/ & ledgers/ → SQLite FTS5 index
    Search: query → FTS5 bm25() → ranked results → RetrievedContextItem list
    Fallback: if index missing, fall back to file-read mode (existing behavior)
"""

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from ..schemas.enums import RetrievalTrustLevel, SourceLayer

if TYPE_CHECKING:
    from ..schemas.retrieval import RetrievedContextItem


# --- Index schema ---
CREATE_FTS5_TABLE = """
CREATE VIRTUAL TABLE IF NOT EXISTS narrative_fts USING fts5(
    item_id,
    item_type,
    content,
    source_layer,
    source_artifact,
    chapter_id,
    arc_id,
    trust_level,
    tokenize='porter unicode61'
);
"""

# --- Materialized table for metadata (non-FTS fields) ---
CREATE_META_TABLE = """
CREATE TABLE IF NOT EXISTS narrative_meta (
    item_id TEXT PRIMARY KEY,
    item_type TEXT NOT NULL,
    source_layer TEXT,
    source_artifact TEXT,
    chapter_id TEXT,
    arc_id TEXT,
    trust_level TEXT NOT NULL,
    char_count INTEGER DEFAULT 0,
    indexed_at TEXT NOT NULL,
    content_hash TEXT DEFAULT ''
);
"""

INDEX_PATH = "workspace/fts5_index/narrative.db"


@dataclass
class BM25Result:
    """A single BM25 search result."""
    item_id: str
    item_type: str
    content: str
    source_layer: str
    source_artifact: str
    chapter_id: str
    arc_id: str
    trust_level: str
    score: float


class BM25Retriever:
    """SQLite FTS5 retriever with BM25 ranking for narrative content.

    Usage:
        retriever = BM25Retriever(project_root)
        retriever.build()           # Build or rebuild index
        results = retriever.search("character conflict foreshadow")  # Query
    """

    def __init__(self, root: Path):
        self._root = root
        self._db_path = root / INDEX_PATH

    # ================================================================
    # Public API
    # ================================================================

    def build(self, force: bool = False) -> dict:
        """Build (or rebuild) the FTS5 index from canon and ledger files.

        Args:
            force: If True, drop and rebuild even if index exists.

        Returns:
            dict with stats: {"chapters": N, "characters": N, "foreshadows": N, "timeline": N, "total": N}
        """
        if force and self._db_path.exists():
            self._db_path.unlink()

        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(self._db_path))
        try:
            conn.execute(CREATE_FTS5_TABLE)
            conn.execute(CREATE_META_TABLE)

            stats = {"chapters": 0, "characters": 0, "foreshadows": 0, "timeline": 0, "summaries": 0}

            stats["chapters"] = self._index_chapters(conn)
            stats["characters"] = self._index_character_knowledge(conn)
            stats["foreshadows"] = self._index_foreshadows(conn)
            stats["timeline"] = self._index_timeline(conn)
            stats["summaries"] = self._index_summaries(conn)

            stats["total"] = sum(stats.values())
            conn.commit()
        finally:
            conn.close()

        return stats

    def search(
        self,
        query: str,
        top_k: int = 20,
        item_types: list[str] | None = None,
    ) -> list[BM25Result]:
        """Search the FTS5 index with BM25 ranking.

        Args:
            query: Natural language query string
            top_k: Max results to return
            item_types: Optional filter by item_type (e.g., ["chapter", "character"])

        Returns:
            List of BM25Result sorted by BM25 score (descending)
        """
        if not self._db_path.exists():
            return []

        conn = sqlite3.connect(str(self._db_path))
        try:
            # Build type filter
            type_clause = ""
            params: list = []

            if item_types:
                placeholders = ",".join("?" for _ in item_types)
                type_clause = f"AND m.item_type IN ({placeholders})"
                params = list(item_types)

            # BM25 ranking via fts5 bm25() function
            sql = f"""
                SELECT
                    f.item_id, f.item_type, f.content,
                    m.source_layer, m.source_artifact,
                    m.chapter_id, m.arc_id, m.trust_level,
                    bm25(narrative_fts, 0.0, 1.0, 0.75, 0.0) AS score
                FROM narrative_fts f
                JOIN narrative_meta m ON f.item_id = m.item_id
                WHERE narrative_fts MATCH ?
                {type_clause}
                ORDER BY score
                LIMIT ?
            """
            params = [query] + params + [top_k]

            cursor = conn.execute(sql, params)
            results = []
            for row in cursor.fetchall():
                results.append(BM25Result(
                    item_id=row[0],
                    item_type=row[1],
                    content=row[2],
                    source_layer=row[3] or "",
                    source_artifact=row[4] or "",
                    chapter_id=row[5] or "",
                    arc_id=row[6] or "",
                    trust_level=row[7] or "",
                    score=float(row[8]) if row[8] is not None else 0.0,
                ))
            return results
        finally:
            conn.close()

    def get_index_stats(self) -> dict:
        """Get index statistics."""
        if not self._db_path.exists():
            return {"exists": False, "total_docs": 0}

        conn = sqlite3.connect(str(self._db_path))
        try:
            count = conn.execute("SELECT COUNT(*) FROM narrative_meta").fetchone()[0]
            by_type = conn.execute(
                "SELECT item_type, COUNT(*) FROM narrative_meta GROUP BY item_type"
            ).fetchall()
            return {
                "exists": True,
                "total_docs": count,
                "by_type": dict(by_type),
                "db_path": str(self._db_path),
            }
        finally:
            conn.close()

    def exists(self) -> bool:
        """Check if the index exists."""
        return self._db_path.exists()

    # ================================================================
    # Internal: Index builders
    # ================================================================

    def _index_chapters(self, conn: sqlite3.Connection) -> int:
        """Index chapters from canon/manuscript/."""
        count = 0
        manuscript_dir = self._root / "canon" / "manuscript"
        if not manuscript_dir.exists():
            return 0

        for md_file in sorted(manuscript_dir.glob("ch_*.md")):
            try:
                content = md_file.read_text(encoding="utf-8")
                chapter_id = md_file.stem  # e.g., "ch_003"
                item_id = f"chapter:{chapter_id}"

                self._insert_doc(
                    conn,
                    item_id=item_id,
                    item_type="chapter",
                    content=self._truncate(content, 8000),
                    source_layer=SourceLayer.CANON.value,
                    source_artifact=f"canon/manuscript/{md_file.name}",
                    chapter_id=chapter_id,
                    arc_id="",
                    trust_level=RetrievalTrustLevel.CANONICAL.value,
                    content_hash=self._hash_content(content),
                )
                count += 1
            except Exception:
                continue

        return count

    def _index_character_knowledge(self, conn: sqlite3.Connection) -> int:
        """Index character knowledge entries from ledgers."""
        count = 0
        ck_path = self._root / "ledgers" / "character_knowledge.json"
        if not ck_path.exists():
            return 0

        try:
            data = json.loads(ck_path.read_text(encoding="utf-8"))
            entries = data.get("character_knowledge_entries", [])
            for entry in entries:
                char_name = entry.get("character_name", entry.get("character_id", "unknown"))
                knowledge = entry.get("knowledge", entry.get("description", ""))
                if not knowledge:
                    continue

                item_id = f"character:{char_name}:{self._hash_content(knowledge)[:8]}"
                self._insert_doc(
                    conn,
                    item_id=item_id,
                    item_type="character",
                    content=f"{char_name}: {knowledge}",
                    source_layer=SourceLayer.CANON.value,
                    source_artifact="ledgers/character_knowledge.json",
                    chapter_id="",
                    arc_id="",
                    trust_level=RetrievalTrustLevel.LEDGER_FACT.value,
                    content_hash=self._hash_content(knowledge),
                )
                count += 1
        except Exception:
            pass

        return count

    def _index_foreshadows(self, conn: sqlite3.Connection) -> int:
        """Index foreshadow entries from ledgers."""
        count = 0
        fs_path = self._root / "ledgers" / "foreshadowing.json"
        if not fs_path.exists():
            return 0

        try:
            data = json.loads(fs_path.read_text(encoding="utf-8"))
            entries = data.get("foreshadowing_entries", [])
            for entry in entries:
                fs_id = entry.get("foreshadow_id", entry.get("id", "unknown"))
                description = entry.get("description", entry.get("detail", ""))
                status = entry.get("status", "")
                if not description:
                    continue

                item_id = f"foreshadow:{fs_id}"
                self._insert_doc(
                    conn,
                    item_id=item_id,
                    item_type="foreshadow",
                    content=f"[{status}] {description}",
                    source_layer=SourceLayer.CANON.value,
                    source_artifact="ledgers/foreshadowing.json",
                    chapter_id="",
                    arc_id="",
                    trust_level=RetrievalTrustLevel.LEDGER_FACT.value,
                    content_hash=self._hash_content(description),
                )
                count += 1
        except Exception:
            pass

        return count

    def _index_timeline(self, conn: sqlite3.Connection) -> int:
        """Index timeline events from ledgers."""
        count = 0
        tl_path = self._root / "ledgers" / "timeline.json"
        if not tl_path.exists():
            return 0

        try:
            data = json.loads(tl_path.read_text(encoding="utf-8"))
            events = data.get("events", [])
            for event in events:
                event_id = event.get("event_id", "unknown")
                description = event.get("description", "")
                event_type = event.get("event_type", "")
                chapter = event.get("chapter", "")
                if not description:
                    continue

                item_id = f"timeline:{event_id}"
                chapter_tag = f"[ch:{chapter}] " if chapter else ""
                self._insert_doc(
                    conn,
                    item_id=item_id,
                    item_type="timeline",
                    content=f"{chapter_tag}[{event_type}] {description}",
                    source_layer=SourceLayer.CANON.value,
                    source_artifact="ledgers/timeline.json",
                    chapter_id=chapter,
                    arc_id="",
                    trust_level=RetrievalTrustLevel.LEDGER_FACT.value,
                    content_hash=self._hash_content(description),
                )
                count += 1
        except Exception:
            pass

        return count

    def _index_summaries(self, conn: sqlite3.Connection) -> int:
        """Index chapter summaries from workspace/summaries/."""
        count = 0
        summaries_dir = self._root / "workspace" / "summaries"
        if not summaries_dir.exists():
            return 0

        for summary_file in sorted(summaries_dir.glob("ch_*_summary.json")):
            try:
                data = json.loads(summary_file.read_text(encoding="utf-8"))
                summary_text = data.get("summary", data.get("narrative_summary", ""))
                if not summary_text:
                    continue

                # Extract chapter_id from filename: ch_003_summary.json -> ch_003
                stem = summary_file.stem  # ch_003_summary
                chapter_id = stem.replace("_summary", "")

                item_id = f"summary:{chapter_id}"
                self._insert_doc(
                    conn,
                    item_id=item_id,
                    item_type="summary",
                    content=summary_text,
                    source_layer=SourceLayer.DRAFT.value,
                    source_artifact=f"workspace/summaries/{summary_file.name}",
                    chapter_id=chapter_id,
                    arc_id="",
                    trust_level=RetrievalTrustLevel.DERIVED_SUMMARY.value,
                    content_hash=self._hash_content(summary_text),
                )
                count += 1
            except Exception:
                continue

        return count

    # ================================================================
    # Internal helpers
    # ================================================================

    def _insert_doc(
        self,
        conn: sqlite3.Connection,
        item_id: str,
        item_type: str,
        content: str,
        source_layer: str,
        source_artifact: str,
        chapter_id: str,
        arc_id: str,
        trust_level: str,
        content_hash: str = "",
    ) -> None:
        """Upsert a document into both FTS and meta tables."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        char_count = len(content)

        # Upsert FTS
        conn.execute(
            """
            INSERT INTO narrative_fts(item_id, item_type, content, source_layer,
                                       source_artifact, chapter_id, arc_id, trust_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (item_id, item_type, content, source_layer, source_artifact,
             chapter_id, arc_id, trust_level),
        )

        # Upsert meta
        conn.execute(
            """
            INSERT OR REPLACE INTO narrative_meta(item_id, item_type, source_layer,
                                                   source_artifact, chapter_id, arc_id,
                                                   trust_level, char_count, indexed_at, content_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (item_id, item_type, source_layer, source_artifact,
             chapter_id, arc_id, trust_level, char_count, now, content_hash),
        )

    @staticmethod
    def _hash_content(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _truncate(content: str, max_chars: int = 8000) -> str:
        if len(content) <= max_chars:
            return content
        return content[:max_chars] + "\n\n[... content truncated for indexing ...]"

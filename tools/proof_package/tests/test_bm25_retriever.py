"""Tests for BM25/FTS5 Narrative Retriever (Phase 3 D-01, D-02)."""

import json
import tempfile
from pathlib import Path

import pytest

from novel_workflow.system_scripts.bm25_retriever import BM25Retriever, BM25Result


def setup_test_project(root: Path) -> Path:
    """Set up a minimal project with canon, ledgers, and summaries."""
    (root / "canon" / "manuscript").mkdir(parents=True)
    (root / "ledgers").mkdir(parents=True)
    (root / "workspace" / "summaries").mkdir(parents=True)

    # Chapters
    (root / "canon" / "manuscript" / "ch_001.md").write_text(
        "# Chapter 1: The Beginning\n\nKael stepped into the ancient temple. "
        "The walls were covered with mysterious runes that glowed faintly in the darkness. "
        "He felt a strange power emanating from the central altar.",
        encoding="utf-8",
    )
    (root / "canon" / "manuscript" / "ch_002.md").write_text(
        "# Chapter 2: The Discovery\n\nLira examined the artifact carefully. "
        "It was clearly of Elven origin, yet the markings suggested something far older. "
        "She turned to Kael with a worried expression.",
        encoding="utf-8",
    )
    (root / "canon" / "manuscript" / "ch_003.md").write_text(
        "# Chapter 3: The Betrayal\n\nMarcus revealed his true intentions at the council meeting. "
        "The alliance between the three kingdoms was shattered in a single moment. "
        "Kael realized they had been manipulated from the very beginning.",
        encoding="utf-8",
    )

    # Ledgers - characters
    (root / "ledgers" / "character_knowledge.json").write_text(
        json.dumps({
            "schema_version": "1.0",
            "character_knowledge_entries": [
                {
                    "character_name": "Kael",
                    "character_id": "kael_sunstrider",
                    "knowledge": "Kael is a warrior from the Sunstrider clan. "
                                 "He wields the legendary blade Dawnbreaker and "
                                 "has a deep connection to the ancient runes.",
                },
                {
                    "character_name": "Lira",
                    "character_id": "lira_moonwhisper",
                    "knowledge": "Lira is an Elven scholar specializing in "
                                 "precursor artifacts. She is cautious and analytical, "
                                 "often serving as the voice of reason.",
                },
                {
                    "character_name": "Marcus",
                    "character_id": "marcus_ironhand",
                    "knowledge": "Marcus is a military commander who secretly "
                                 "serves the Shadow Council. His betrayal is the "
                                 "central conflict of the second arc.",
                },
            ],
        }, indent=2),
        encoding="utf-8",
    )

    # Ledgers - foreshadows
    (root / "ledgers" / "foreshadowing.json").write_text(
        json.dumps({
            "schema_version": "1.0",
            "foreshadowing_entries": [
                {
                    "foreshadow_id": "fs_001",
                    "description": "The ancient runes on the temple walls react to Kael's "
                                   "presence, hinting at his hidden lineage.",
                    "status": "active",
                    "introduced_in": "ch_001",
                    "due_by": "ch_010",
                },
                {
                    "foreshadow_id": "fs_002",
                    "description": "Marcus is seen meeting with a hooded figure after dark, "
                                   "foreshadowing his eventual betrayal.",
                    "status": "paid_off",
                    "introduced_in": "ch_001",
                    "resolved_in": "ch_003",
                },
            ],
        }, indent=2),
        encoding="utf-8",
    )

    # Ledgers - timeline
    (root / "ledgers" / "timeline.json").write_text(
        json.dumps({
            "schema_version": "1.0",
            "events": [
                {
                    "event_id": "evt_001",
                    "event_type": "chapter_written",
                    "chapter": "ch_001",
                    "description": "Kael discovers ancient temple with mysterious runes",
                },
                {
                    "event_id": "evt_002",
                    "event_type": "chapter_written",
                    "chapter": "ch_002",
                    "description": "Lira analyzes Elven artifact of unknown origin",
                },
                {
                    "event_id": "evt_003",
                    "event_type": "chapter_written",
                    "chapter": "ch_003",
                    "description": "Marcus betrays the alliance at the council meeting",
                },
            ],
        }, indent=2),
        encoding="utf-8",
    )

    # Summaries
    (root / "workspace" / "summaries" / "ch_001_summary.json").write_text(
        json.dumps({
            "summary": "Kael enters an ancient temple and discovers glowing runes. "
                       "A mysterious power emanates from the central altar.",
        }, indent=2),
        encoding="utf-8",
    )

    return root


class TestBM25Build:
    """Test BM25 index building (D-01)."""

    @pytest.fixture
    def project(self):
        with tempfile.TemporaryDirectory() as d:
            yield setup_test_project(Path(d))

    def test_build_creates_database(self, project):
        """D-01: build() creates the SQLite FTS5 database."""
        retriever = BM25Retriever(project)
        assert not retriever.exists()

        stats = retriever.build()
        assert retriever.exists()
        assert stats["total"] > 0

    def test_build_stats(self, project):
        """D-01: build() returns correct document counts."""
        retriever = BM25Retriever(project)
        stats = retriever.build()

        assert stats["chapters"] == 3
        assert stats["characters"] == 3
        assert stats["foreshadows"] == 2
        assert stats["timeline"] == 3
        assert stats["summaries"] == 1
        assert stats["total"] == 12

    def test_build_force_rebuild(self, project):
        """D-01: force=True rebuilds the index from scratch."""
        retriever = BM25Retriever(project)
        retriever.build()

        # Delete a chapter to prove rebuild actually re-scans
        (project / "canon" / "manuscript" / "ch_003.md").unlink()
        retriever.build(force=True)

        stats = retriever.get_index_stats()
        assert stats["by_type"]["chapter"] == 2

    def test_index_stats(self, project):
        """D-01: get_index_stats() returns correct information."""
        retriever = BM25Retriever(project)
        retriever.build()

        stats = retriever.get_index_stats()
        assert stats["exists"] is True
        assert stats["total_docs"] == 12
        assert stats["by_type"]["chapter"] == 3
        assert stats["by_type"]["character"] == 3


class TestBM25Search:
    """Test BM25 search functionality (D-02)."""

    @pytest.fixture
    def retriever(self):
        with tempfile.TemporaryDirectory() as d:
            root = setup_test_project(Path(d))
            r = BM25Retriever(root)
            r.build()
            yield r

    def test_search_returns_results(self, retriever):
        """D-02: search() returns results for a keyword query."""
        results = retriever.search("temple runes", top_k=5)
        assert len(results) > 0
        assert all(isinstance(r, BM25Result) for r in results)

    def test_search_ranks_by_relevance(self, retriever):
        """D-02: Results are ranked by BM25 score (most relevant first)."""
        results = retriever.search("ancient runes temple", top_k=10)
        assert len(results) >= 2

        # First result should be most relevant (contains all query terms)
        scores = [r.score for r in results]
        assert scores == sorted(scores)  # BM25: lower = better match

    def test_search_chapter_content(self, retriever):
        """D-02: Chapter content is searchable."""
        results = retriever.search("Elven artifact", top_k=5)
        chapter_results = [r for r in results if r.item_type == "chapter"]

        assert len(chapter_results) >= 1
        content_text = " ".join(r.content for r in chapter_results).lower()
        assert "elven" in content_text

    def test_search_character_knowledge(self, retriever):
        """D-02: Character knowledge is searchable."""
        results = retriever.search("warrior blade Dawnbreaker", top_k=5)
        char_results = [r for r in results if r.item_type == "character"]

        assert len(char_results) >= 1
        assert any("kael" in r.content.lower() for r in char_results)

    def test_search_foreshadows(self, retriever):
        """D-02: Foreshadow entries are searchable."""
        results = retriever.search("betrayal marcus hooded figure", top_k=5)
        fs_results = [r for r in results if r.item_type == "foreshadow"]

        assert len(fs_results) >= 1
        assert any("marcus" in r.content.lower() for r in fs_results)

    def test_search_timeline(self, retriever):
        """D-02: Timeline events are searchable."""
        results = retriever.search("betray council meeting", top_k=5)
        tl_results = [r for r in results if r.item_type == "timeline"]

        assert len(tl_results) >= 1

    def test_search_summaries(self, retriever):
        """D-02: Summaries are searchable."""
        results = retriever.search("ancient temple mysterious", top_k=5)
        summary_results = [r for r in results if r.item_type == "summary"]

        assert len(summary_results) >= 1

    def test_search_filter_by_type(self, retriever):
        """D-02: Filter results by item_type."""
        results = retriever.search("kael", top_k=10, item_types=["character"])
        assert all(r.item_type == "character" for r in results)
        assert len(results) >= 1

    def test_search_top_k_limit(self, retriever):
        """D-02: top_k parameter limits results."""
        results_all = retriever.search("the", top_k=3)
        assert len(results_all) <= 3

    def test_search_no_results(self, retriever):
        """D-02: Query with no matches returns empty list."""
        results = retriever.search("xyzzy_nonexistent_term_12345", top_k=5)
        assert results == []

    def test_search_without_index(self, tmp_path):
        """D-02: search() returns empty when no index exists."""
        retriever = BM25Retriever(tmp_path)
        results = retriever.search("anything", top_k=5)
        assert results == []

    def test_results_have_all_fields(self, retriever):
        """D-02: Results contain all expected metadata fields."""
        results = retriever.search("Kael", top_k=3)
        for r in results:
            assert r.item_id
            assert r.item_type
            assert r.content
            assert r.trust_level
            assert r.score is not None

    def test_trust_levels_preserved(self, retriever):
        """D-02: Trust levels from source data are preserved."""
        results = retriever.search("Kael", top_k=10)

        trust_levels = {r.trust_level for r in results}
        # Chapters should have canonical trust level
        assert "canonical" in trust_levels or "ledger_fact" in trust_levels

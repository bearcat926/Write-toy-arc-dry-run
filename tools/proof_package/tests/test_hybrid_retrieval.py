"""Tests for VectorAdapter and HybridRetriever (Phase 3 D-03 through D-06)."""

import tempfile
from pathlib import Path

import pytest

from novel_workflow.system_scripts.vector_adapter import (
    TfidfVectorAdapter,
    NullVectorAdapter,
    create_vector_adapter,
    VectorResult,
)
from novel_workflow.system_scripts.hybrid_retriever import (
    HybridRetriever,
    GraphExpander,
    RetrievalPlan,
    FusedResult,
    PROFILE_CONFIG,
)
from novel_workflow.system_scripts.bm25_retriever import BM25Retriever


# ================================================================
# D-03: VectorAdapter interface
# ================================================================

class TestNullAdapter:
    def test_is_not_available(self):
        adapter = NullVectorAdapter()
        assert not adapter.is_available()

    def test_search_returns_empty(self):
        adapter = NullVectorAdapter()
        results = adapter.search("anything")
        assert results == []

    def test_index_is_noop(self):
        adapter = NullVectorAdapter()
        adapter.index([{"item_id": "1", "content": "hello"}])


class TestTfidfAdapter:
    @pytest.fixture
    def docs(self):
        return [
            {"item_id": "ch_001", "content": "Kael discovers ancient temple runes mysterious power"},
            {"item_id": "ch_002", "content": "Lira analyzes Elven artifact precursor origin"},
            {"item_id": "ch_003", "content": "Marcus betrays alliance council meeting kingdoms shattered"},
            {"item_id": "char_kael", "content": "Warrior Sunstrider clan legendary blade Dawnbreaker"},
            {"item_id": "char_lira", "content": "Elven scholar precursor artifacts cautious analytical"},
        ]

    def test_availability(self):
        adapter = TfidfVectorAdapter()
        # May be available or not depending on sklearn
        assert adapter.name == "tfidf-local"

    def test_index_and_search(self, docs):
        adapter = TfidfVectorAdapter()
        if not adapter.is_available():
            pytest.skip("scikit-learn not available")

        adapter.index(docs)
        results = adapter.search("ancient temple runes")

        assert len(results) > 0
        assert any("ch_001" in r.item_id for r in results)

    def test_search_character(self, docs):
        adapter = TfidfVectorAdapter()
        if not adapter.is_available():
            pytest.skip("scikit-learn not available")

        adapter.index(docs)
        results = adapter.search("warrior blade")

        assert len(results) > 0
        assert any("kael" in r.item_id for r in results)

    def test_search_empty_query(self, docs):
        adapter = TfidfVectorAdapter()
        if not adapter.is_available():
            pytest.skip("scikit-learn not available")

        adapter.index(docs)
        results = adapter.search("")
        assert results == []


class TestFactory:
    def test_create_null(self):
        adapter = create_vector_adapter("null")
        assert isinstance(adapter, NullVectorAdapter)

    def test_create_auto(self):
        adapter = create_vector_adapter("auto")
        assert adapter.name in ("tfidf-local", "null")

    def test_create_invalid(self):
        with pytest.raises(ValueError, match="Unknown vector adapter"):
            create_vector_adapter("invalid_name")


# ================================================================
# D-05: Graph Expansion
# ================================================================

class TestGraphExpander:
    @pytest.fixture
    def expander(self):
        with tempfile.TemporaryDirectory() as d:
            yield GraphExpander(Path(d))

    def test_empty_graph(self, expander):
        results = expander.expand("anything")
        assert results == []

    def test_with_graph_data(self):
        import json

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "workspace").mkdir(parents=True)
            graph = {
                "nodes": {
                    "n_kael": {"name": "Kael", "type": "character", "description": "Warrior"},
                    "n_temple": {"name": "Ancient Temple", "type": "location", "description": "Mysterious"},
                    "n_lira": {"name": "Lira", "type": "character", "description": "Scholar"},
                },
                "edges": [
                    {"source": "n_kael", "target": "n_temple", "type": "visited"},
                    {"source": "n_kael", "target": "n_lira", "type": "ally"},
                ],
            }
            (root / "workspace" / "narrative_graph_index.json").write_text(
                json.dumps(graph)
            )

            expander = GraphExpander(root)
            results = expander.expand("Kael")

            assert len(results) > 0
            assert any("temple" in r.item_id for r in results)


# ================================================================
# D-06: HybridRetriever + RRF Fusion
# ================================================================

class TestHybridRetriever:
    @pytest.fixture
    def retriever(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            # Set up minimal project
            (root / "canon" / "manuscript").mkdir(parents=True)
            (root / "ledgers").mkdir(parents=True)
            (root / "workspace" / "summaries").mkdir(parents=True)

            import json
            (root / "canon" / "manuscript" / "ch_001.md").write_text(
                "# Chapter 1\n\nKael entered the ancient temple with glowing runes.",
                encoding="utf-8",
            )
            (root / "ledgers" / "timeline.json").write_text(
                json.dumps({"schema_version": "1.0", "events": [
                    {"event_id": "e1", "event_type": "discovery", "chapter": "ch_001",
                     "description": "Kael discovers ancient temple"}
                ]})
            )
            (root / "ledgers" / "character_knowledge.json").write_text(
                json.dumps({"schema_version": "1.0", "character_knowledge_entries": []})
            )
            (root / "ledgers" / "foreshadowing.json").write_text(
                json.dumps({"schema_version": "1.0", "foreshadowing_entries": []})
            )

            bm25 = BM25Retriever(root)
            bm25.build()

            yield HybridRetriever(bm25, None, None)

    def test_bm25_only_retrieval(self, retriever):
        results = retriever.retrieve("temple", RetrievalPlan(enable_vector=False))
        assert len(results) > 0

    def test_writer_profile(self, retriever):
        results = retriever.retrieve("Kael", RetrievalPlan(profile="writer"))
        assert len(results) > 0

    def test_auditor_profile(self, retriever):
        results = retriever.retrieve("temple", RetrievalPlan(profile="auditor"))
        assert len(results) > 0

    def test_budget_trimming(self, retriever):
        results = retriever.retrieve(
            "temple", RetrievalPlan(char_budget=100, max_results=2)
        )
        assert len(results) <= 2

    def test_rrf_scoring(self, retriever):
        """RRF scores are computed when multiple sources contribute."""
        results = retriever.retrieve(
            "Kael temple",
            RetrievalPlan(enable_bm25=True, enable_vector=False, enable_graph=False),
        )
        for r in results:
            assert r.rrf_score > 0 if r.bm25_score > 0 else r.rrf_score == 0


class TestRetrievalPlan:
    def test_defaults(self):
        plan = RetrievalPlan()
        assert plan.profile == "writer"
        assert plan.enable_bm25 is True
        assert plan.enable_vector is True

    def test_custom(self):
        plan = RetrievalPlan(
            profile="auditor",
            enable_vector=False,
            top_k_per_source=10,
            max_results=5,
        )
        assert plan.profile == "auditor"
        assert not plan.enable_vector


class TestProfileConfig:
    def test_all_profiles_exist(self):
        assert "writer" in PROFILE_CONFIG
        assert "auditor" in PROFILE_CONFIG
        assert "extractor" in PROFILE_CONFIG

    def test_writer_includes_summaries(self):
        cfg = PROFILE_CONFIG["writer"]
        assert "summary" in cfg["preferred_types"]
        assert "foreshadow" in cfg["preferred_types"]

    def test_auditor_prefers_canonical(self):
        cfg = PROFILE_CONFIG["auditor"]
        assert cfg["min_trust"] == "canonical"

    def test_extractor_prefers_chapters(self):
        cfg = PROFILE_CONFIG["extractor"]
        assert "chapter" in cfg["preferred_types"]


class TestFusedResult:
    def test_to_context_item(self):
        fr = FusedResult(
            item_id="test_1",
            item_type="character",
            content="Kael the warrior",
            source="bm25",
        )
        ctx = fr.to_context_item()
        assert ctx["item_id"] == "test_1"
        assert ctx["item_type"] == "character"
        assert ctx["source"] == "bm25"

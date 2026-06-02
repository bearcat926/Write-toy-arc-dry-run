"""Tests for ChapterCommit event system (Phase 3 C-01 through C-03)."""

import json
import tempfile
from pathlib import Path

import pytest

from novel_workflow.schemas.chapter_commit import (
    ChapterCommitEvent,
    ChapterCommitLog,
    ChapterCommitStore,
)
from novel_workflow.system_scripts.projection_registry import (
    ProjectionRegistry,
    ProjectionStatus,
)


# ============================================================
# C-01: ChapterCommit Schema Tests
# ============================================================

class TestChapterCommitEvent:
    """Test ChapterCommitEvent creation and serialization."""

    def test_create_event(self):
        """C-01: Event creation with factory method."""
        event = ChapterCommitEvent.create(
            chapter_id="ch_001",
            arc_id="arc_dragon",
            ledger_diff_hash="abc123def456",
            trace_id="trc_test_001",
        )

        assert event.event_type == "chapter.commit"
        assert event.event_version == "1.0"
        assert event.chapter_id == "ch_001"
        assert event.arc_id == "arc_dragon"
        assert event.ledger_diff_hash == "abc123def456"
        assert event.trace_id == "trc_test_001"
        assert event.commit_id.startswith("cmt_")
        assert event.applied_at != ""

    def test_create_event_deterministic_commit_id(self):
        """C-01: Same inputs produce same commit_id."""
        e1 = ChapterCommitEvent.create("ch_001", "arc_a", "hash_a", trace_id="trc_a")
        e2 = ChapterCommitEvent.create("ch_001", "arc_a", "hash_a", trace_id="trc_a")
        assert e1.commit_id == e2.commit_id

    def test_create_event_different_commit_id(self):
        """C-01: Different inputs produce different commit_id."""
        e1 = ChapterCommitEvent.create("ch_001", "arc_a", "hash_a")
        e2 = ChapterCommitEvent.create("ch_002", "arc_a", "hash_a")
        assert e1.commit_id != e2.commit_id

    def test_event_serialization(self):
        """C-01: Event serializes to valid JSON."""
        event = ChapterCommitEvent.create("ch_001", "arc_a", "hash_a")
        data = event.model_dump()
        assert data["event_type"] == "chapter.commit"
        assert "commit_id" in data

        # Round-trip
        json_str = event.model_dump_json()
        reloaded = ChapterCommitEvent.model_validate_json(json_str)
        assert reloaded.commit_id == event.commit_id
        assert reloaded.chapter_id == event.chapter_id

    def test_event_default_values(self):
        """C-01: Default values are sensible."""
        event = ChapterCommitEvent.create("ch_001", "arc_a")
        assert event.ledger_offsets == {}
        assert event.source_artifacts == []
        assert event.context_mode == "legacy"
        assert event.canon_hash == ""


class TestChapterCommitLog:
    """Test in-memory commit log operations."""

    def test_append_and_count(self):
        log = ChapterCommitLog()
        e1 = ChapterCommitEvent.create("ch_001", "arc_a")
        e2 = ChapterCommitEvent.create("ch_002", "arc_a")

        log.append(e1)
        log.append(e2)

        assert len(log.commits) == 2
        assert log.last_commit_index == 1

    def test_get_by_chapter(self):
        log = ChapterCommitLog()
        log.append(ChapterCommitEvent.create("ch_001", "arc_a"))
        log.append(ChapterCommitEvent.create("ch_002", "arc_a"))
        log.append(ChapterCommitEvent.create("ch_001", "arc_a"))

        ch1_commits = log.get_by_chapter("ch_001")
        assert len(ch1_commits) == 2

    def test_get_latest(self):
        log = ChapterCommitLog()
        e1 = ChapterCommitEvent.create("ch_001", "arc_a")
        e2 = ChapterCommitEvent.create("ch_002", "arc_a")

        log.append(e1)
        log.append(e2)

        assert log.get_latest().commit_id == e2.commit_id

    def test_empty_log(self):
        log = ChapterCommitLog()
        assert log.get_latest() is None
        assert log.get_by_chapter("ch_001") == []

    def test_get_range(self):
        log = ChapterCommitLog()
        events = []
        for i in range(5):
            e = ChapterCommitEvent.create(f"ch_{i:03d}", "arc_a")
            events.append(e)
            log.append(e)

        subset = log.get_range(1, 3)
        assert len(subset) == 2
        assert subset[0].chapter_id == "ch_001"
        assert subset[1].chapter_id == "ch_002"


# ============================================================
# C-02: Persistent ChapterCommitStore Tests
# ============================================================

class TestChapterCommitStore:
    """Test persistent commit log storage."""

    @pytest.fixture
    def tmp_root(self):
        with tempfile.TemporaryDirectory() as d:
            yield Path(d)

    def test_append_and_load(self, tmp_root):
        """C-02: Events persist across store instances."""
        store = ChapterCommitStore(tmp_root)
        event = ChapterCommitEvent.create("ch_001", "arc_a", "hash_abc")
        store.append(event)

        # New store instance loads same data
        store2 = ChapterCommitStore(tmp_root)
        log = store2.load_all()
        assert len(log.commits) == 1
        assert log.commits[0].commit_id == event.commit_id

    def test_multiple_appends(self, tmp_root):
        """C-02: Multiple events append correctly."""
        store = ChapterCommitStore(tmp_root)
        for i in range(10):
            store.append(ChapterCommitEvent.create(f"ch_{i:03d}", "arc_a"))

        log = store.load_all()
        assert len(log.commits) == 10

    def test_count(self, tmp_root):
        """C-02: Count returns correct total."""
        store = ChapterCommitStore(tmp_root)
        assert store.count == 0

        store.append(ChapterCommitEvent.create("ch_001", "arc_a"))
        store.append(ChapterCommitEvent.create("ch_002", "arc_a"))
        assert store.count == 2

    def test_get_latest(self, tmp_root):
        """C-02: get_latest returns most recent event."""
        store = ChapterCommitStore(tmp_root)
        e1 = ChapterCommitEvent.create("ch_001", "arc_a")
        e2 = ChapterCommitEvent.create("ch_002", "arc_a")

        store.append(e1)
        store.append(e2)

        latest = store.get_latest()
        assert latest.commit_id == e2.commit_id

    def test_get_by_chapter(self, tmp_root):
        """C-02: Filter events by chapter_id."""
        store = ChapterCommitStore(tmp_root)
        store.append(ChapterCommitEvent.create("ch_001", "arc_a"))
        store.append(ChapterCommitEvent.create("ch_002", "arc_a"))
        store.append(ChapterCommitEvent.create("ch_001", "arc_a"))

        results = store.get_by_chapter("ch_001")
        assert len(results) == 2

    def test_empty_store(self, tmp_root):
        """C-02: Empty store handles gracefully."""
        store = ChapterCommitStore(tmp_root)
        assert store.count == 0
        assert store.get_latest() is None
        assert store.get_by_chapter("ch_001") == []

    def test_corrupted_line_skipped(self, tmp_root):
        """C-02: Corrupted JSON lines are skipped gracefully."""
        store = ChapterCommitStore(tmp_root)
        good_event = ChapterCommitEvent.create("ch_001", "arc_a", "hash_good")
        store.append(good_event)

        # Inject corrupted line directly
        log_path = tmp_root / store.LOG_FILE
        with open(log_path, "a", encoding="utf-8") as f:
            f.write("this is not valid json\n")

        log = store.load_all()
        assert len(log.commits) == 1
        assert log.commits[0].commit_id == good_event.commit_id


# ============================================================
# C-03: ProjectionRegistry Tests
# ============================================================

class TestProjectionRegistry:
    """Test projection registration and dispatch."""

    @pytest.fixture
    def registry(self):
        with tempfile.TemporaryDirectory() as d:
            yield ProjectionRegistry(Path(d))

    @pytest.fixture
    def sample_event(self):
        return ChapterCommitEvent.create("ch_001", "arc_a", "hash_abc", trace_id="trc_test")

    def test_register_and_dispatch(self, registry, sample_event):
        """C-03: Register a projection and dispatch an event."""

        def my_projection(event: ChapterCommitEvent):
            return registry.summary_projection(event)

        registry.register("my_proj", my_projection, "Test projection")
        records = registry.dispatch(sample_event)

        assert len(records) == 1
        assert records[0].status == ProjectionStatus.SUCCESS

    def test_multiple_projections(self, registry, sample_event):
        """C-03: Multiple projections all receive the event."""

        registry.register("proj_a", registry.summary_projection)
        registry.register("proj_b", registry.graph_projection)
        registry.register("proj_c", registry.index_projection)

        records = registry.dispatch(sample_event)
        assert len(records) == 3

    def test_disabled_projection_skipped(self, registry, sample_event):
        """C-03: Disabled projections are skipped."""

        registry.register("proj_a", registry.summary_projection)
        registry.register("proj_b", registry.graph_projection, enabled=False)

        records = registry.dispatch(sample_event)
        assert len(records) == 2

        skipped = [r for r in records if r.status == ProjectionStatus.SKIPPED]
        assert len(skipped) == 1
        assert skipped[0].projection_name == "proj_b"

    def test_enable_disable(self, registry, sample_event):
        """C-03: Toggle projection enable/disable."""

        registry.register("proj_a", registry.summary_projection)
        assert "proj_a" in registry.enabled_names

        registry.disable("proj_a")
        assert "proj_a" not in registry.enabled_names

        registry.enable("proj_a")
        assert "proj_a" in registry.enabled_names

    def test_unregister(self, registry, sample_event):
        """C-03: Unregistered projections are removed."""

        registry.register("proj_a", registry.summary_projection)
        registry.unregister("proj_a")

        records = registry.dispatch(sample_event)
        assert len(records) == 0

    def test_failing_projection_does_not_block_others(self, registry, sample_event):
        """C-03: One failing projection doesn't block others."""

        def failing_proj(event: ChapterCommitEvent):
            raise RuntimeError("Simulated failure")

        registry.register("good", registry.summary_projection)
        registry.register("bad", failing_proj)
        registry.register("also_good", registry.graph_projection)

        records = registry.dispatch(sample_event)
        assert len(records) == 3

        failed = [r for r in records if r.status == ProjectionStatus.FAILED]
        assert len(failed) == 1
        assert failed[0].projection_name == "bad"
        assert "Simulated failure" in failed[0].error_message

        success = [r for r in records if r.status == ProjectionStatus.SUCCESS]
        assert len(success) == 2

    def test_get_history(self, registry, sample_event):
        """C-03: History tracks projection executions."""

        registry.register("proj_a", registry.summary_projection)
        registry.dispatch(sample_event)

        e2 = ChapterCommitEvent.create("ch_002", "arc_a")
        registry.dispatch(e2)

        history = registry.get_history()
        assert len(history) == 2

        history_filtered = registry.get_history(commit_id=sample_event.commit_id)
        assert len(history_filtered) == 1

    def test_get_failed(self, registry, sample_event):
        """C-03: get_failed returns only failed projections."""

        def failing(event: ChapterCommitEvent):
            raise ValueError("test error")

        registry.register("good", registry.summary_projection)
        registry.register("bad", failing)

        registry.dispatch(sample_event)

        failed = registry.get_failed()
        assert len(failed) == 1
        assert failed[0].projection_name == "bad"

    def test_registered_names(self, registry):
        """C-03: List registered projections."""
        assert registry.registered_names == []

        registry.register("a", registry.summary_projection)
        registry.register("b", registry.graph_projection)

        assert set(registry.registered_names) == {"a", "b"}

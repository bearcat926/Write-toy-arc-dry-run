"""Integration test: AtomicApplyManager emits ChapterCommit events (Phase 3 C-02)."""

import json
import tempfile
from pathlib import Path

import pytest

from novel_workflow.system_scripts.atomic_apply_manager import AtomicApplyManager
from novel_workflow.schemas.chapter_commit import ChapterCommitStore, ChapterCommitEvent
from novel_workflow.schemas.gate import GateRecord
from novel_workflow.schemas.diff import LedgerDiff
from novel_workflow.system_scripts.projection_registry import ProjectionRegistry, ProjectionStatus


def setup_project(tmp_root: Path) -> Path:
    """Set up minimal project structure for testing."""
    (tmp_root / "arcs" / "test_arc" / "drafts").mkdir(parents=True)
    (tmp_root / "arcs" / "test_arc" / "reports").mkdir(parents=True)
    (tmp_root / "arcs" / "test_arc" / "archive").mkdir(parents=True)
    (tmp_root / "canon" / "manuscript").mkdir(parents=True)
    (tmp_root / "canon" / "characters" / "character_mind_cards").mkdir(parents=True)
    (tmp_root / "ledgers").mkdir(parents=True)
    (tmp_root / "workspace").mkdir(parents=True)

    # Create a draft file
    draft = tmp_root / "arcs" / "test_arc" / "drafts" / "ch_001.md"
    draft.write_text("# Chapter 1\n\nTest content.", encoding="utf-8")

    return tmp_root


def make_gate(arc_id: str = "test_arc", decision: str = "approved") -> GateRecord:
    return GateRecord(
        gate_id=f"gate_{arc_id}_ch_end",
        gate_type="arc_end",
        target_artifact=f"arcs/{arc_id}/drafts/ch_001.md",
        decision=decision,
        author_input_evidence="Author approval for testing purposes — verified chapter content meets arc requirements",
        author_id="test_author",
        source_artifacts=[f"arcs/{arc_id}/drafts/ch_001.md"],
    )


def make_ledger_diff(arc_id: str = "test_arc") -> LedgerDiff:
    return LedgerDiff(
        arc_id=arc_id,
        operations=[
            {
                "target_ledger": "timeline",
                "operation": "append_event",
                "source_artifact": "arcs/test_arc/drafts/ch_001.md",
                "data": {
                    "event_id": "evt_test_001",
                    "event_type": "chapter_written",
                    "chapter": "ch_001",
                    "description": "Chapter 1 completed",
                },
            }
        ],
    )


class TestApplyChapterCommit:
    """Test that AtomicApplyManager emits ChapterCommit after success."""

    @pytest.fixture
    def project(self):
        with tempfile.TemporaryDirectory() as d:
            yield setup_project(Path(d))

    def test_apply_without_commit_store_no_error(self, project):
        """Apply succeeds even without chapter commit configured."""
        mgr = AtomicApplyManager(project)
        gate = make_gate()
        diff = make_ledger_diff()

        result = mgr.apply(
            arc_id="test_arc",
            gate_record=gate,
            draft_files=["ch_001.md"],
            ledger_diff=diff,
            canon_diff=None,
            dry_run=False,
        )

        assert result["result"] == "success"

    def test_apply_emits_chapter_commit(self, project):
        """Apply with commit store emits a ChapterCommitEvent."""
        commit_store = ChapterCommitStore(project)
        registry = ProjectionRegistry(project)

        mgr = AtomicApplyManager(project)
        mgr.enable_chapter_commit(commit_store, registry)

        gate = make_gate()
        diff = make_ledger_diff()

        result = mgr.apply(
            arc_id="test_arc",
            gate_record=gate,
            draft_files=["ch_001.md"],
            ledger_diff=diff,
            canon_diff=None,
            dry_run=False,
        )

        assert result["result"] == "success"

        # Verify commit event was stored
        assert commit_store.count == 1

        event = commit_store.get_latest()
        assert event is not None
        assert event.event_type == "chapter.commit"
        assert event.arc_id == "test_arc"
        assert event.ledger_diff_hash == result["diff_hash"]

    def test_apply_emits_chapter_commit_multiple(self, project):
        """Multiple applies produce multiple commit events."""
        commit_store = ChapterCommitStore(project)

        mgr = AtomicApplyManager(project)
        mgr.enable_chapter_commit(commit_store)

        for i in range(3):
            chapter_id = f"ch_{i+1:03d}"
            draft_path = project / "arcs" / "test_arc" / "drafts" / f"{chapter_id}.md"
            draft_path.write_text(f"# Chapter {i+1}\n\nContent {i+1}.", encoding="utf-8")

            gate = make_gate()
            diff = LedgerDiff(
                arc_id="test_arc",
                operations=[
                    {
                        "target_ledger": "timeline",
                        "operation": "append_event",
                        "source_artifact": f"arcs/test_arc/drafts/{chapter_id}.md",
                        "data": {
                            "event_id": f"evt_{chapter_id}",
                            "event_type": "chapter_written",
                            "chapter": chapter_id,
                            "description": f"Chapter {i+1}",
                        },
                    }
                ],
            )

            result = mgr.apply(
                arc_id="test_arc",
                gate_record=gate,
                draft_files=[f"{chapter_id}.md"],
                ledger_diff=diff,
                canon_diff=None,
                dry_run=False,
            )
            assert result["result"] == "success"

        assert commit_store.count == 3

    def test_apply_with_projections(self, project):
        """Chapter commit dispatches to projection registry."""
        commit_store = ChapterCommitStore(project)
        registry = ProjectionRegistry(project)

        # Register a projection that records calls
        calls = []

        def counting_projection(event: ChapterCommitEvent):
            calls.append(event.commit_id)
            return registry.summary_projection(event)

        registry.register("counter", counting_projection)
        registry.register("graph", registry.graph_projection)
        registry.register("health", registry.health_projection)

        mgr = AtomicApplyManager(project)
        mgr.enable_chapter_commit(commit_store, registry)

        gate = make_gate()
        diff = make_ledger_diff()

        result = mgr.apply(
            arc_id="test_arc",
            gate_record=gate,
            draft_files=["ch_001.md"],
            ledger_diff=diff,
            canon_diff=None,
            dry_run=False,
        )

        assert result["result"] == "success"
        assert len(calls) == 1

        # All three projections should have been called
        history = registry.get_history()
        assert len(history) == 3
        assert all(r.status == ProjectionStatus.SUCCESS for r in history)

    def test_apply_failure_no_commit_event(self, project):
        """Failed apply does NOT emit ChapterCommit."""
        commit_store = ChapterCommitStore(project)

        mgr = AtomicApplyManager(project)
        mgr.enable_chapter_commit(commit_store)

        gate = make_gate(decision="approved")

        # Create a diff that will fail prevalidation (no source_artifact)
        diff = LedgerDiff(
            arc_id="test_arc",
            operations=[
                {
                    "target_ledger": "timeline",
                    "operation": "append_event",
                    # Missing source_artifact
                    "data": {"event_id": "evt_bad"},
                }
            ],
        )

        with pytest.raises(ValueError):
            mgr.apply(
                arc_id="test_arc",
                gate_record=gate,
                draft_files=["ch_001.md"],
                ledger_diff=diff,
                canon_diff=None,
                dry_run=False,
            )

        # No commit event should be emitted
        assert commit_store.count == 0

    def test_apply_already_consumed_prevents_commit(self, project):
        """Already consumed diff prevents both apply and commit."""
        commit_store = ChapterCommitStore(project)

        mgr = AtomicApplyManager(project)
        mgr.enable_chapter_commit(commit_store)

        gate = make_gate()
        diff = make_ledger_diff()

        # First apply succeeds
        result1 = mgr.apply(
            arc_id="test_arc",
            gate_record=gate,
            draft_files=["ch_001.md"],
            ledger_diff=diff,
            canon_diff=None,
            dry_run=False,
        )
        assert result1["result"] == "success"
        assert commit_store.count == 1

        # Second apply with same diff fails
        gate2 = make_gate()
        with pytest.raises(ValueError, match="ALREADY_CONSUMED"):
            mgr.apply(
                arc_id="test_arc",
                gate_record=gate2,
                draft_files=["ch_001.md"],
                ledger_diff=diff,
                canon_diff=None,
                dry_run=False,
            )

        # Commit count unchanged
        assert commit_store.count == 1

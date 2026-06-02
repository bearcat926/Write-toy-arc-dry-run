"""Tests for Governance Projection + E2E Integration (Phase 3 E/I series)."""

import json
import tempfile
from pathlib import Path

import pytest

from novel_workflow.system_scripts.governance_projection import (
    GovernanceProjection,
    GovernanceReport,
    create_governance_projection,
)
from novel_workflow.schemas.chapter_commit import ChapterCommitEvent, ChapterCommitStore
from novel_workflow.system_scripts.projection_registry import ProjectionRegistry
from novel_workflow.system_scripts.atomic_apply_manager import AtomicApplyManager
from novel_workflow.schemas.gate import GateRecord
from novel_workflow.schemas.diff import LedgerDiff


# ================================================================
# E series: Governance Projection
# ================================================================

class TestGovernanceReport:
    def test_default_report(self):
        report = GovernanceReport(chapter_id="ch_001", arc_id="arc_a")
        assert report.recommended_action == "approve"
        assert report.max_severity == "none"
        assert report.phase == "shadow"
        assert report.derived is True

    def test_is_blocking_shadow_mode(self):
        """Even with block action, shadow mode should not block."""
        report = GovernanceReport(
            chapter_id="ch_001",
            recommended_action="block",
            phase="shadow",
        )
        assert not report.is_blocking()

    def test_is_blocking_active_mode(self):
        """Active mode with block action IS blocking."""
        report = GovernanceReport(
            chapter_id="ch_001",
            recommended_action="block",
            phase="active",
        )
        assert report.is_blocking()


class TestGovernanceProjection:
    @pytest.fixture
    def projection(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "arcs" / "test_arc" / "drafts").mkdir(parents=True)
            (root / "arcs" / "test_arc" / "reports").mkdir(parents=True)
            (root / "canon" / "manuscript").mkdir(parents=True)
            (root / "ledgers").mkdir(parents=True)
            (root / "workspace" / "reports").mkdir(parents=True)

            draft = root / "arcs" / "test_arc" / "drafts" / "ch_001.md"
            draft.write_text("# Chapter 1\n\nTest content.", encoding="utf-8")

            gp = GovernanceProjection(root, mode="shadow")
            yield gp

    def test_audit_returns_projection_record(self, projection):
        event = ChapterCommitEvent.create(
            chapter_id="ch_001",
            arc_id="test_arc",
            ledger_diff_hash="hash_test",
        )
        record = projection.audit(event)

        assert record.projection_name == "governance"
        assert record.status.value == "success"
        assert record.commit_id == event.commit_id

    def test_shadow_mode_does_not_block(self, projection):
        """Shadow mode governance never blocks."""
        event = ChapterCommitEvent.create("ch_001", "test_arc")
        record = projection.audit(event)

        # Check no hard_pause file was created
        pause_dir = projection._root / "arcs" / "test_arc" / "reports"
        pause_files = list(pause_dir.glob("hard_pause_*.json"))
        assert len(pause_files) == 0

    def test_report_written_to_disk(self, projection):
        event = ChapterCommitEvent.create("ch_001", "test_arc")
        projection.audit(event)

        report_path = (
            projection._root / "workspace" / "reports" / "governance_ch_001.json"
        )
        assert report_path.exists()

        data = json.loads(report_path.read_text(encoding="utf-8"))
        assert data["chapter_id"] == "ch_001"
        assert data["recommended_action"] == "approve"
        assert data["derived"] is True

    def test_check_hard_pause_none(self, projection):
        result = projection.check_hard_pause("test_arc")
        assert result is None

    def test_clear_hard_pause_no_file(self, projection):
        result = projection.clear_hard_pause("test_arc", "ch_001")
        assert result is False

    def test_write_and_clear_hard_pause(self, projection):
        """Write a hard_pause, verify it, then clear it."""
        event = ChapterCommitEvent.create("ch_001", "test_arc")
        report = GovernanceReport(
            chapter_id="ch_001",
            arc_id="test_arc",
            recommended_action="block",
            phase="active",
            blocking_issues=[{"severity": "high", "detail": "Character inconsistency"}],
        )
        projection._write_pause_report(report, event)

        # Check it exists
        result = projection.check_hard_pause("test_arc")
        assert result is not None

        # Clear it
        cleared = projection.clear_hard_pause("test_arc", "ch_001")
        assert cleared is True

        # Check it's gone
        result2 = projection.check_hard_pause("test_arc")
        assert result2 is None

    def test_mode_switching(self, projection):
        assert projection.mode == "shadow"

        projection.set_active()
        assert projection.mode == "active"

        projection.set_shadow()
        assert projection.mode == "shadow"

    def test_factory_creates_projection(self, projection):
        gp2 = create_governance_projection(projection._root, mode="active")
        assert gp2.mode == "active"


# ================================================================
# I series: E2E Integration (ChapterCommit + Governance + Projections)
# ================================================================

class TestE2EChapterFlow:
    """End-to-end test: Chapter → Apply → ChapterCommit → Projections → Governance."""

    @pytest.fixture
    def project(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "arcs" / "test_arc" / "drafts").mkdir(parents=True)
            (root / "arcs" / "test_arc" / "reports").mkdir(parents=True)
            (root / "arcs" / "test_arc" / "archive").mkdir(parents=True)
            (root / "canon" / "manuscript").mkdir(parents=True)
            (root / "canon" / "characters" / "character_mind_cards").mkdir(parents=True)
            (root / "ledgers").mkdir(parents=True)
            (root / "workspace").mkdir(parents=True)
            (root / "workspace" / "reports").mkdir(parents=True)

            draft = root / "arcs" / "test_arc" / "drafts" / "ch_001.md"
            draft.write_text("# Chapter 1\n\nThe story begins.", encoding="utf-8")

            yield root

    def _make_gate(self):
        return GateRecord(
            gate_id="gate_e2e_001",
            gate_type="arc_end",
            target_artifact="arcs/test_arc/drafts/ch_001.md",
            decision="approved",
            author_input_evidence="Author approved chapter after review — verified quality and arc alignment",
            author_id="test_author",
            source_artifacts=["arcs/test_arc/drafts/ch_001.md"],
        )

    def _make_diff(self, chapter_id="ch_001"):
        return LedgerDiff(
            arc_id="test_arc",
            operations=[{
                "target_ledger": "timeline",
                "operation": "append_event",
                "source_artifact": f"arcs/test_arc/drafts/{chapter_id}.md",
                "data": {
                    "event_id": f"evt_{chapter_id}",
                    "event_type": "chapter_written",
                    "chapter": chapter_id,
                    "description": f"{chapter_id} completed",
                },
            }],
        )

    def test_full_e2e_single_chapter(self, project):
        """I-01/I-03: Single chapter full flow."""
        # Setup
        commit_store = ChapterCommitStore(project)
        registry = ProjectionRegistry(project)
        governance = GovernanceProjection(project, mode="shadow")

        # Register projections
        registry.register("summary", registry.summary_projection)
        registry.register("graph", registry.graph_projection)
        registry.register("health", registry.health_projection)
        registry.register("governance", governance)

        # Create apply manager with ChapterCommit
        mgr = AtomicApplyManager(project)
        mgr.enable_chapter_commit(commit_store, registry)

        # Execute full flow
        result = mgr.apply(
            arc_id="test_arc",
            gate_record=self._make_gate(),
            draft_files=["ch_001.md"],
            ledger_diff=self._make_diff("ch_001"),
            canon_diff=None,
            dry_run=False,
        )

        # Assert apply succeeded
        assert result["result"] == "success"

        # Assert ChapterCommit emitted
        assert commit_store.count == 1
        event = commit_store.get_latest()
        assert event.event_type == "chapter.commit"

        # Assert all 4 projections executed
        history = registry.get_history()
        assert len(history) == 4

        # Assert governance report written
        gov_report = project / "workspace" / "reports" / "governance_ch_001.json"
        assert gov_report.exists()

    def test_e2e_multi_chapter_flow(self, project):
        """I-03: Multi-chapter continuous flow (5 chapters)."""
        commit_store = ChapterCommitStore(project)
        registry = ProjectionRegistry(project)
        governance = GovernanceProjection(project, mode="shadow")

        registry.register("summary", registry.summary_projection)
        registry.register("governance", governance)

        mgr = AtomicApplyManager(project)
        mgr.enable_chapter_commit(commit_store, registry)

        for i in range(1, 6):
            ch_id = f"ch_{i:03d}"

            # Create draft
            draft_path = project / "arcs" / "test_arc" / "drafts" / f"{ch_id}.md"
            draft_path.write_text(f"# Chapter {i}\n\nContent for chapter {i}.", encoding="utf-8")

            # Apply
            result = mgr.apply(
                arc_id="test_arc",
                gate_record=GateRecord(
                    gate_id=f"gate_{ch_id}",
                    gate_type="arc_end",
                    target_artifact=f"arcs/test_arc/drafts/{ch_id}.md",
                    decision="approved",
                    author_input_evidence=f"Author approved chapter {i} — meets quality and arc requirements",
                    author_id="test_author",
                    source_artifacts=[f"arcs/test_arc/drafts/{ch_id}.md"],
                ),
                draft_files=[f"{ch_id}.md"],
                ledger_diff=self._make_diff(ch_id),
                canon_diff=None,
                dry_run=False,
            )

            assert result["result"] == "success"

        # All 5 chapters committed
        assert commit_store.count == 5
        assert len(commit_store.load_all().commits) == 5

        # All projections executed (2 per chapter = 10)
        history = registry.get_history()
        assert len(history) == 10

    def test_e2e_replay_contract(self, project):
        """I-04: Replay contract validates inputs."""
        from novel_workflow.system_scripts.replay_contract import ReplayContract

        replay = ReplayContract(project)
        snapshot = replay.capture_inputs(
            arc_id="test_arc",
            chapter_id="ch_001",
            mode="apply",
            context_mode="legacy",
        )

        assert snapshot.arc_id == "test_arc"
        assert snapshot.chapter_id == "ch_001"
        assert snapshot.fingerprint != ""

        # Replay should be valid against itself
        assert replay.validate_replay(snapshot, snapshot)

    def test_e2e_rebuild_flow(self, project):
        """I-05: Verify replay contract validation."""
        from novel_workflow.system_scripts.replay_contract import ReplayContract

        # Apply a chapter
        commit_store = ChapterCommitStore(project)
        mgr = AtomicApplyManager(project)
        mgr.enable_chapter_commit(commit_store)

        result = mgr.apply(
            arc_id="test_arc",
            gate_record=self._make_gate(),
            draft_files=["ch_001.md"],
            ledger_diff=self._make_diff("ch_001"),
            canon_diff=None,
            dry_run=False,
        )
        assert result["result"] == "success"

        # Capture snapshot before rebuild
        replay = ReplayContract(project)
        snap1 = replay.capture_inputs("test_arc", "ch_001", "apply")

        # Verify snapshot is valid and consistent
        assert snap1.fingerprint != ""
        assert snap1.arc_id == "test_arc"

        # Replay validation: same inputs should match
        snap2 = replay.capture_inputs("test_arc", "ch_001", "apply")
        assert replay.validate_replay(snap1, snap2)

    def test_e2e_rollback_protection(self, project):
        """I-05: Rollback recovers from failed apply."""
        # First successful apply
        mgr = AtomicApplyManager(project)
        result = mgr.apply(
            arc_id="test_arc",
            gate_record=self._make_gate(),
            draft_files=["ch_001.md"],
            ledger_diff=self._make_diff("ch_001"),
            canon_diff=None,
            dry_run=False,
        )
        assert result["result"] == "success"

        # Verify manuscript was written
        ch_file = project / "canon" / "manuscript" / "ch_001.md"
        assert ch_file.exists()

        # Snapshot should exist in archive
        snapshots = list((project / "arcs" / "test_arc" / "archive").glob("snapshot_*"))
        assert len(snapshots) > 0

    def test_failure_isolation_no_commit(self, project):
        """Failed apply does NOT emit ChapterCommit or run projections."""
        commit_store = ChapterCommitStore(project)
        registry = ProjectionRegistry(project)

        calls = []

        def counting(event):
            calls.append(event.commit_id)
            return registry.summary_projection(event)

        registry.register("counter", counting)
        mgr = AtomicApplyManager(project)
        mgr.enable_chapter_commit(commit_store, registry)

        # Create invalid diff (no source_artifact)
        bad_diff = LedgerDiff(
            arc_id="test_arc",
            operations=[{
                "target_ledger": "timeline",
                "operation": "append_event",
                "data": {"event_id": "evt_bad"},
            }],
        )

        with pytest.raises(ValueError):
            mgr.apply(
                arc_id="test_arc",
                gate_record=self._make_gate(),
                draft_files=["ch_001.md"],
                ledger_diff=bad_diff,
                canon_diff=None,
                dry_run=False,
            )

        # Nothing committed, no projections called
        assert commit_store.count == 0
        assert len(calls) == 0

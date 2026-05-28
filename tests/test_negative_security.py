"""P1.10-P1.18: Negative tests — security boundary enforcement."""
import json
import os
from pathlib import Path
from unittest.mock import patch
import pytest
from pydantic import ValidationError

from novel_workflow.guards.path_safety import PathSafetyGuard, PathSafetyError
from novel_workflow.system_scripts.atomic_apply_manager import AtomicApplyManager
from novel_workflow.schemas.gate import GateRecord
from novel_workflow.schemas.diff import LedgerDiff
from novel_workflow.schemas.progress import ProgressEntry


# --- P1.10: Symlink escape rejected by PathSafetyGuard ---
def test_symlink_escape_rejected(project_root: Path):
    """PathSafetyGuard must reject symlinks that escape workspace."""
    guard = PathSafetyGuard(project_root)
    target = project_root.parent / "outside.txt"
    target.write_text("evil")
    symlink_path = project_root / "arcs" / "arc_001" / "drafts" / "escape.md"
    symlink_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(str(target), str(symlink_path))
    except OSError:
        pytest.skip("Symlink creation not supported (requires admin on Windows)")

    with pytest.raises(PathSafetyError, match="SYMLINK_ESCAPE_REJECTED"):
        guard.check_write_path("arcs/arc_001/drafts/escape.md", "agent")


# --- P1.11: TOCTOU symlink race ---
def test_toctou_symlink_race_rejected(project_root: Path):
    """Guard check + write must reject if symlink target is replaced between check and write."""
    guard = PathSafetyGuard(project_root)
    # Create a valid file first
    valid_path = project_root / "arcs" / "arc_001" / "drafts" / "ch_001.md"
    valid_path.parent.mkdir(parents=True, exist_ok=True)
    valid_path.write_text("valid content")

    # Check passes for the valid path
    resolved = guard.check_write_path("arcs/arc_001/drafts/ch_001.md", "agent")
    assert resolved.exists()

    # Now simulate TOCTOU: replace the file with a symlink to outside
    evil_target = project_root.parent / "evil.txt"
    evil_target.write_text("evil content")
    try:
        valid_path.unlink()
        os.symlink(str(evil_target), str(valid_path))
    except OSError:
        pytest.skip("Symlink creation not supported (requires admin on Windows)")

    # Re-check should reject because resolved path escapes workspace
    with pytest.raises(PathSafetyError, match="SYMLINK_ESCAPE_REJECTED"):
        guard.check_write_path("arcs/arc_001/drafts/ch_001.md", "agent")


# --- P1.14: ProgressEntry(contains_narrative_fact=True) raises ---
def test_progress_entry_rejects_narrative_fact():
    """ProgressEntry must reject contains_narrative_fact=True."""
    with pytest.raises(ValidationError, match="NARRATIVE_FACT_FORBIDDEN"):
        ProgressEntry(
            event_type="chapter_completed",
            artifact_path="arcs/arc_001/drafts/ch_001.md",
            contains_narrative_fact=True,
        )


# --- P1.15: ProgressEntry details with denylist keyword raises ---
def test_progress_entry_rejects_denylist_keyword():
    """ProgressEntry must reject details containing denylist keywords."""
    with pytest.raises(ValidationError, match="DENYLIST_KEYWORD"):
        ProgressEntry(
            event_type="chapter_completed",
            artifact_path="arcs/arc_001/drafts/ch_001.md",
            details={"canon_fact": "something"},
        )


def test_progress_entry_rejects_ledger_entry_keyword():
    """ProgressEntry must reject 'ledger_entry' in details."""
    with pytest.raises(ValidationError, match="DENYLIST_KEYWORD"):
        ProgressEntry(
            event_type="chapter_completed",
            details={"ledger_entry": "data"},
        )


def test_progress_entry_rejects_narrative_event_keyword():
    """ProgressEntry must reject 'narrative_event' in details."""
    with pytest.raises(ValidationError, match="DENYLIST_KEYWORD"):
        ProgressEntry(
            event_type="chapter_completed",
            details={"narrative_event": "something happened"},
        )


def test_progress_entry_allows_safe_details():
    """ProgressEntry should accept details without denylist keywords."""
    entry = ProgressEntry(
        event_type="chapter_completed",
        artifact_path="arcs/arc_001/drafts/ch_001.md",
        details={"proposal_merged": True, "word_count": 5000},
        contains_narrative_fact=False,
    )
    assert entry.details["proposal_merged"] is True


# --- P1.16: Apply midway failure → rollback complete ---
def test_apply_midway_failure_rollback(project_root: Path):
    """If canonicalize raises during apply, all state must be restored."""
    (project_root / "ledgers/timeline.json").write_text(
        json.dumps({"schema_version": "1.0", "events": []})
    )
    (project_root / "arcs/arc_001/drafts/ch_001.md").write_text("# Ch 1")
    diff = LedgerDiff(
        arc_id="arc_001",
        operations=[{"type": "append", "target_ledger": "timeline",
                     "operation": "append_event",
                     "data": {"event_id": "e1", "summary": "test"}}],
    )
    gate = GateRecord(
        gate_id="ae_001", gate_type="arc_end", target_artifact="arc_001",
        decision="approved", author_input_evidence="Good",
        author_id="local_author", source_artifacts=[],
    )
    mgr = AtomicApplyManager(project_root)
    with patch.object(mgr._canonicalizer, 'canonicalize', side_effect=IOError("canonicalize fail")):
        with pytest.raises(IOError, match="canonicalize fail"):
            mgr.apply("arc_001", gate, ["ch_001.md"], diff, None)
    # Verify rollback: timeline restored, no new files
    timeline = json.loads((project_root / "ledgers/timeline.json").read_text())
    assert timeline["events"] == []
    # No apply_record should exist
    assert not (project_root / "arcs/arc_001/reports/apply_record.json").exists()
    # Consumed hashes should not have been updated
    consumed_path = project_root / "workspace/consumed_hashes.json"
    if consumed_path.exists():
        consumed = json.loads(consumed_path.read_text())
        assert len(consumed.get("consumed_hashes", [])) == 0


# --- P1.17: Stale/replay gate reused → apply reject ---
def test_stale_gate_reused_rejected(project_root: Path):
    """A gate that was already consumed must be rejected on replay."""
    (project_root / "ledgers/timeline.json").write_text(
        json.dumps({"schema_version": "1.0", "events": []})
    )
    (project_root / "arcs/arc_001/drafts/ch_001.md").write_text("# Ch 1")
    diff = LedgerDiff(
        arc_id="arc_001",
        operations=[{"type": "append", "target_ledger": "timeline",
                     "operation": "append_event",
                     "data": {"event_id": "e1", "summary": "test"}}],
    )
    gate = GateRecord(
        gate_id="ae_001", gate_type="arc_end", target_artifact="arc_001",
        decision="approved", author_input_evidence="Good",
        author_id="local_author", source_artifacts=[],
    )
    mgr = AtomicApplyManager(project_root)
    # First apply succeeds
    result = mgr.apply("arc_001", gate, ["ch_001.md"], diff, None)
    assert result["result"] == "success"
    # Second apply with same diff must be rejected (ALREADY_CONSUMED)
    with pytest.raises(ValueError, match="ALREADY_CONSUMED"):
        mgr.apply("arc_001", gate, ["ch_001.md"], diff, None)


# --- P1.18: Proposal disguised as ledger_diff → prevalidation rejects ---
def test_proposal_disguised_as_diff_rejected(project_root: Path):
    """A proposal formatted as ledger_diff must be rejected by prevalidation."""
    (project_root / "ledgers/timeline.json").write_text(
        json.dumps({"schema_version": "1.0", "events": []})
    )
    (project_root / "arcs/arc_001/drafts/ch_001.md").write_text("# Ch 1")
    # Create a "diff" that looks like a proposal (invalid target_ledger)
    diff = LedgerDiff(
        arc_id="arc_001",
        operations=[{"type": "append", "target_ledger": "invalid_ledger",
                     "operation": "append_event",
                     "data": {"event_id": "e1", "summary": "spoofed"}}],
    )
    gate = GateRecord(
        gate_id="ae_001", gate_type="arc_end", target_artifact="arc_001",
        decision="approved", author_input_evidence="Good",
        author_id="local_author", source_artifacts=[],
    )
    mgr = AtomicApplyManager(project_root)
    with pytest.raises(ValueError, match="INVALID_LEDGER"):
        mgr.apply("arc_001", gate, ["ch_001.md"], diff, None)

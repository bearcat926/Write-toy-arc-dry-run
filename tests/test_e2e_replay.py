"""PG2.2: E2E replay test — full lifecycle with rollback scenarios."""
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from novel_workflow.project_init import init_project
from novel_workflow.system_scripts.arc_state_manager import ArcWorkingStateManager
from novel_workflow.system_scripts.atomic_apply_manager import AtomicApplyManager
from novel_workflow.system_scripts.ledger_diff_generator import LedgerDiffGenerator
from novel_workflow.schemas.gate import GateRecord
from novel_workflow.schemas.diff import LedgerDiff
from novel_workflow.schemas.proposal import LedgerUpdateProposal


def _setup_workspace(root: Path):
    """Initialize project and create arc directories."""
    init_project(root)
    for d in ["drafts", "reviews", "proposals", "reports", "gates", "checkpoints", "archive"]:
        (root / "arcs" / "arc_001" / d).mkdir(parents=True, exist_ok=True)


def _seed_chapters(root: Path, count: int = 3):
    """Write chapter drafts."""
    for i in range(1, count + 1):
        (root / "arcs" / "arc_001" / "drafts" / f"ch_{i:03d}.md").write_text(f"# Chapter {i}\nContent")


def _seed_ledgers(root: Path):
    """Create empty ledgers."""
    (root / "ledgers" / "timeline.json").write_text(
        json.dumps({"schema_version": "1.0", "events": []})
    )


def _make_proposals(count: int = 3) -> list[dict]:
    """Generate proposal data for each chapter."""
    return [
        {"claim": f"Event {i}", "source_layer": "draft",
         "source_artifact": f"arcs/arc_001/drafts/ch_{i:03d}.md",
         "evidence": f"Evidence {i}", "confidence": "high",
         "target_ledger": "timeline", "operation": "append_event",
         "proposed_change": {"event_id": f"evt_{i}", "summary": f"Event {i}"}}
        for i in range(1, count + 1)
    ]


def _make_gate() -> GateRecord:
    return GateRecord(
        gate_id="ae_001", gate_type="arc_end", target_artifact="arc_001",
        decision="approved", author_input_evidence="Good arc",
        author_id="local_author", source_artifacts=[],
    )


def test_e2e_full_replay(tmp_path: Path):
    """PG2.2: Full E2E replay — fresh workspace → 3ch → gates → apply →
    rollback[canon fail] → rollback[ledger fail] → dup reject → resume.
    """
    root = tmp_path / "toy_project"
    _setup_workspace(root)
    _seed_ledgers(root)
    _seed_chapters(root, 3)

    aws_mgr = ArcWorkingStateManager(root)
    aws_mgr.initialize("arc_001")

    # Merge proposals
    proposals_data = _make_proposals(3)
    for i, pdata in enumerate(proposals_data):
        p = LedgerUpdateProposal(**pdata)
        aws_mgr.merge_proposal("arc_001", p, f"ch_{i+1:03d}")

    # Generate ledger_diff
    gen = LedgerDiffGenerator()
    diff_data = gen.generate(proposals_data)
    ledger_diff = LedgerDiff(arc_id="arc_001", operations=diff_data["operations"])

    # --- Scenario 1: Happy path apply ---
    apply_mgr = AtomicApplyManager(root)
    result = apply_mgr.apply("arc_001", _make_gate(), ["ch_001.md", "ch_002.md", "ch_003.md"], ledger_diff, None)
    assert result["result"] == "success"
    # Verify canon/manuscript has chapters
    for ch in ["ch_001.md", "ch_002.md", "ch_003.md"]:
        assert (root / "canon" / "manuscript" / ch).exists()
    # Verify ledgers updated
    timeline = json.loads((root / "ledgers" / "timeline.json").read_text())
    assert len(timeline["events"]) == 3

    # --- Scenario 2: Duplicate apply rejected ---
    with pytest.raises(ValueError, match="ALREADY_CONSUMED"):
        apply_mgr.apply("arc_001", _make_gate(), ["ch_001.md"], ledger_diff, None)

    # --- Scenario 3: Rollback on canonicalize failure ---
    # Create a new diff for a fresh apply attempt
    proposals_data_2 = [
        {"claim": "New event", "source_layer": "draft",
         "source_artifact": "arcs/arc_001/drafts/ch_001.md",
         "evidence": "New evidence", "confidence": "high",
         "target_ledger": "timeline", "operation": "append_event",
         "proposed_change": {"event_id": "evt_new", "summary": "New event"}}
    ]
    diff_data_2 = gen.generate(proposals_data_2)
    ledger_diff_2 = LedgerDiff(arc_id="arc_001", operations=diff_data_2["operations"])
    gate_2 = GateRecord(
        gate_id="ae_002", gate_type="arc_end", target_artifact="arc_001",
        decision="approved", author_input_evidence="Second arc",
        author_id="local_author", source_artifacts=[],
    )
    manuscript_before = set((root / "canon" / "manuscript").glob("*.md"))
    events_before = json.loads((root / "ledgers" / "timeline.json").read_text())["events"]

    with patch.object(apply_mgr._canonicalizer, 'canonicalize', side_effect=IOError("disk full")):
        with pytest.raises(IOError, match="disk full"):
            apply_mgr.apply("arc_001", gate_2, ["ch_001.md"], ledger_diff_2, None)

    # Verify rollback restored state
    manuscript_after = set((root / "canon" / "manuscript").glob("*.md"))
    assert manuscript_before == manuscript_after
    events_after = json.loads((root / "ledgers" / "timeline.json").read_text())["events"]
    assert events_after == events_before

    # --- Scenario 4: Rollback on ledger write failure ---
    proposals_data_3 = [
        {"claim": "Another event", "source_layer": "draft",
         "source_artifact": "arcs/arc_001/drafts/ch_002.md",
         "evidence": "More evidence", "confidence": "high",
         "target_ledger": "timeline", "operation": "append_event",
         "proposed_change": {"event_id": "evt_another", "summary": "Another event"}}
    ]
    diff_data_3 = gen.generate(proposals_data_3)
    ledger_diff_3 = LedgerDiff(arc_id="arc_001", operations=diff_data_3["operations"])
    gate_3 = GateRecord(
        gate_id="ae_003", gate_type="arc_end", target_artifact="arc_001",
        decision="approved", author_input_evidence="Third arc",
        author_id="local_author", source_artifacts=[],
    )

    with patch.object(apply_mgr, '_apply_ledger_diff', side_effect=IOError("ledger write fail")):
        with pytest.raises(IOError, match="ledger write fail"):
            apply_mgr.apply("arc_001", gate_3, ["ch_002.md"], ledger_diff_3, None)

    # Verify rollback
    events_after_3 = json.loads((root / "ledgers" / "timeline.json").read_text())["events"]
    assert events_after_3 == events_before

    # --- Scenario 5: Resume after rollback ---
    # A new diff should be able to apply successfully
    proposals_data_4 = [
        {"claim": "Resume event", "source_layer": "draft",
         "source_artifact": "arcs/arc_001/drafts/ch_003.md",
         "evidence": "Resume evidence", "confidence": "high",
         "target_ledger": "timeline", "operation": "append_event",
         "proposed_change": {"event_id": "evt_resume", "summary": "Resume event"}}
    ]
    diff_data_4 = gen.generate(proposals_data_4)
    ledger_diff_4 = LedgerDiff(arc_id="arc_001", operations=diff_data_4["operations"])
    gate_4 = GateRecord(
        gate_id="ae_004", gate_type="arc_end", target_artifact="arc_001",
        decision="approved", author_input_evidence="Resume arc",
        author_id="local_author", source_artifacts=[],
    )
    result_4 = apply_mgr.apply("arc_001", gate_4, ["ch_003.md"], ledger_diff_4, None)
    assert result_4["result"] == "success"
    # New event should be in ledger
    timeline_final = json.loads((root / "ledgers" / "timeline.json").read_text())
    assert len(timeline_final["events"]) == 4  # 3 original + 1 resume

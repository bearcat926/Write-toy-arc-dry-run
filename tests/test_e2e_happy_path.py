import json
from pathlib import Path
import pytest
from novel_workflow.project_init import init_project
from novel_workflow.system_scripts.arc_state_manager import ArcWorkingStateManager
from novel_workflow.system_scripts.atomic_apply_manager import AtomicApplyManager
from novel_workflow.schemas.gate import GateRecord
from novel_workflow.schemas.diff import LedgerDiff
from novel_workflow.schemas.proposal import LedgerUpdateProposal


def test_full_3_chapter_arc(tmp_path: Path):
    root = tmp_path / "toy_project"
    init_project(root)

    # 1. Direction gate
    gate_dir = root / "gates" / "direction_gate.json"
    gate_dir.write_text(json.dumps({
        "schema_version": "1.0", "gate_id": "dir_001", "gate_type": "direction",
        "target_artifact": "project", "decision": "approved",
        "author_input_evidence": "Fantasy YA adventure",
        "author_id": "local_author", "source_artifacts": [],
    }))

    # 2. Arc start gate
    gate_start = root / "arcs" / "arc_001" / "gates" / "arc_start_gate.json"
    gate_start.parent.mkdir(parents=True, exist_ok=True)
    gate_start.write_text(json.dumps({
        "schema_version": "1.0", "gate_id": "as_001", "gate_type": "arc_start",
        "target_artifact": "arc_001", "decision": "approved",
        "author_input_evidence": "Arc contract looks solid",
        "author_id": "local_author", "source_artifacts": [],
    }))

    # 3. Initialize arc working state
    aws_mgr = ArcWorkingStateManager(root)
    aws_mgr.initialize("arc_001")

    # 4. Write drafts
    for ch in ["ch_001", "ch_002", "ch_003"]:
        drafts_dir = root / "arcs" / "arc_001" / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        (drafts_dir / f"{ch}.md").write_text(f"# {ch} content")

    # 5. Merge proposals for each chapter
    proposals_data = [
        ("ch_001", {"claim": "A arrives", "source_layer": "draft",
                     "source_artifact": "arcs/arc_001/drafts/ch_001.md",
                     "evidence": "A walked in", "confidence": "high",
                     "target_ledger": "timeline", "operation": "append_event",
                     "proposed_change": {"event_id": "e1", "summary": "A arrives"}}),
        ("ch_002", {"claim": "A meets B", "source_layer": "draft",
                     "source_artifact": "arcs/arc_001/drafts/ch_002.md",
                     "evidence": "B greeted A", "confidence": "high",
                     "target_ledger": "timeline", "operation": "append_event",
                     "proposed_change": {"event_id": "e2", "summary": "A meets B"}}),
        ("ch_003", {"claim": "A faces challenge", "source_layer": "draft",
                     "source_artifact": "arcs/arc_001/drafts/ch_003.md",
                     "evidence": "A drew sword", "confidence": "high",
                     "target_ledger": "timeline", "operation": "append_event",
                     "proposed_change": {"event_id": "e3", "summary": "First challenge"}}),
    ]
    for ch, pdata in proposals_data:
        p = LedgerUpdateProposal(**pdata)
        aws_mgr.merge_proposal("arc_001", p, ch)

    # 6. Generate ledger_diff
    from novel_workflow.system_scripts.ledger_diff_generator import LedgerDiffGenerator
    gen = LedgerDiffGenerator()
    diff_data = gen.generate([pd for _, pd in proposals_data])
    ledger_diff = LedgerDiff(arc_id="arc_001", operations=diff_data["operations"])
    (root / "arcs" / "arc_001" / "reports").mkdir(parents=True, exist_ok=True)
    (root / "arcs" / "arc_001" / "reports" / "ledger_diff.json").write_text(
        json.dumps(ledger_diff.model_dump(mode="json"), indent=2)
    )

    # 7. Arc end gate
    gate_end = GateRecord(
        gate_id="ae_001", gate_type="arc_end", target_artifact="arc_001",
        decision="approved", author_input_evidence="Great arc, approve canonization",
        author_id="local_author", source_artifacts=[],
    )

    # 8. Atomic apply
    apply_mgr = AtomicApplyManager(root)
    result = apply_mgr.apply(
        "arc_001", gate_end,
        ["ch_001.md", "ch_002.md", "ch_003.md"],
        ledger_diff, None,
    )
    assert result["result"] == "success"

    # 9. Verify canon/manuscript updated
    for ch in ["ch_001", "ch_002", "ch_003"]:
        assert (root / "canon" / "manuscript" / f"{ch}.md").exists()

    # 10. Verify ledgers updated
    timeline = json.loads((root / "ledgers" / "timeline.json").read_text())
    events = timeline.get("events", timeline.get("timeline_entries", []))
    assert len(events) == 3

    # 11. Verify duplicate apply rejected
    with pytest.raises(ValueError, match="ALREADY_CONSUMED"):
        apply_mgr.apply("arc_001", gate_end, ["ch_001.md"], ledger_diff, None)

    # 12. Verify apply_record exists
    assert (root / "arcs" / "arc_001" / "reports" / "apply_record.json").exists()

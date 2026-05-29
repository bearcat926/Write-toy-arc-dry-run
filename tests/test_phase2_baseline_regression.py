"""Phase 2 baseline regression tests.

Ensures derived artifacts cannot enter source/proposal/apply pipelines.
"""
import json as _json
import pytest
from pathlib import Path
from novel_workflow.validators.source_artifact_policy import (
    is_derived_source,
    validate_source_artifact,
)
from novel_workflow.validators.derived_artifact_policy import is_derived_artifact


# All workspace derived prefixes that must be rejected
DERIVED_PATHS = [
    "workspace/summaries/ch_001_summary.json",
    "workspace/summaries/arc_001_summary.json",
    "workspace/reports/graph_health_report.md",
    "workspace/retrieval_traces/ch_001.jsonl",
    "workspace/phase2/meta.json",
    "workspace/narrative_graph_index.json",
    "workspace/foreshadow_lifecycle_index.json",
    "workspace/character_state/char_a.json",
    "workspace/arc_plan/arc_001_arc_plan.json",
]


@pytest.mark.parametrize("path", DERIVED_PATHS)
def test_derived_artifact_policy_recognizes(path):
    assert is_derived_artifact(path), f"Should be derived: {path}"


@pytest.mark.parametrize("path", DERIVED_PATHS)
def test_source_policy_rejects_as_source(path):
    assert is_derived_source(path), f"Should be derived source: {path}"
    result = validate_source_artifact("draft", path)
    assert not result.is_valid, f"Should reject as source: {path}"


@pytest.mark.parametrize("path", DERIVED_PATHS)
def test_derived_not_enter_apply(project_root: Path, path):
    """Derived source_artifact must be rejected by AtomicApplyManager."""
    from novel_workflow.system_scripts.atomic_apply_manager import AtomicApplyManager
    from novel_workflow.schemas.gate import GateRecord
    from novel_workflow.schemas.diff import LedgerDiff

    (project_root / "ledgers/timeline.json").write_text(
        _json.dumps({"schema_version": "1.0", "events": []})
    )
    (project_root / "arcs/arc_001/drafts/ch_001.md").write_text("# Ch 1")

    diff = LedgerDiff(
        arc_id="arc_001",
        operations=[{
            "target_ledger": "timeline",
            "operation": "append_event",
            "data": {"event_id": "e1", "summary": "test"},
            "source_artifact": path,
            "source_layer": "draft",
        }],
    )
    gate = GateRecord(
        gate_id="ae_001", gate_type="arc_end", target_artifact="arc_001",
        decision="approved", author_input_evidence="test",
        author_id="local_author", source_artifacts=[],
    )
    mgr = AtomicApplyManager(project_root)
    with pytest.raises(ValueError):
        mgr.apply("arc_001", gate, ["ch_001.md"], diff, None)

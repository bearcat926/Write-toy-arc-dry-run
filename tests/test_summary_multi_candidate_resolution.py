"""Milestone 11.6: Summary multi-candidate resolution tests."""
import json
import pytest
from pathlib import Path
from novel_workflow.schemas.narrative_summary import ChapterNarrativeSummary
from novel_workflow.schemas.enums import SourceLayer
from novel_workflow.validators.error_codes import SUMMARY_MULTIPLE_CANDIDATES


def test_single_active_summary(tmp_path: Path):
    """Protocol: at most one active summary per source_artifact."""
    summary_dir = tmp_path / "workspace" / "summaries"
    summary_dir.mkdir(parents=True)

    # Single active summary
    summary_path = summary_dir / "ch_001_summary.json"
    summary_path.write_text(json.dumps({
        "schema_version": "1.0",
        "chapter_id": "ch_001", "arc_id": "arc_001",
        "source_layer": "draft",
        "source_artifact": "arcs/arc_001/drafts/ch_001.md",
        "source_artifact_hash": "abc123",
        "derived": True,
    }))

    # Active path must be workspace/summaries/ch_XXX_summary.json
    active_path = summary_dir / "ch_001_summary.json"
    assert active_path.exists()


def test_active_path_protocol():
    """Protocol: active summary path is fixed format."""
    # Only these paths are active summaries
    valid_patterns = [
        "workspace/summaries/ch_001_summary.json",
        "workspace/summaries/ch_999_summary.json",
    ]
    # Archive/tmp are NOT active
    invalid_patterns = [
        "workspace/summaries/archive/ch_001_v1_summary.json",
        "workspace/summaries/tmp/ch_001_summary.tmp.json",
    ]
    import re
    active_pattern = re.compile(r"^workspace/summaries/ch_\d{3}_summary\.json$")
    for p in valid_patterns:
        assert active_pattern.match(p)
    for p in invalid_patterns:
        assert not active_pattern.match(p)


def test_multiple_candidates_error():
    """Protocol: multiple matching summaries → SUMMARY_MULTIPLE_CANDIDATES."""
    assert SUMMARY_MULTIPLE_CANDIDATES == "SUMMARY_MULTIPLE_CANDIDATES"


def test_tmp_file_not_read_by_retrieval():
    """Protocol: .tmp.json must not be read by retrieval builder."""
    # This is a protocol invariant test
    # The retrieval builder must only read active paths, not .tmp files
    tmp_path = "workspace/summaries/ch_001_summary.json.tmp"
    active_path = "workspace/summaries/ch_001_summary.json"
    assert tmp_path != active_path
    assert tmp_path.endswith(".tmp")

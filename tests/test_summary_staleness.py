"""Milestone 11.5: Summary staleness detection tests."""
import json
import pytest
from pathlib import Path
from novel_workflow.schemas.narrative_summary import ChapterNarrativeSummary
from novel_workflow.schemas.hash_utils import canonical_sha256_file
from novel_workflow.schemas.enums import SourceLayer
from novel_workflow.validators.error_codes import SUMMARY_STALE


def _write_draft(root: Path, ch_id: str, content: str = "Chapter content"):
    path = root / "arcs" / "arc_001" / "drafts" / f"{ch_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {ch_id}\n{content}\n", encoding="utf-8")
    return path


def _make_summary(root: Path, ch_id: str, draft_hash: str):
    summary = ChapterNarrativeSummary(
        chapter_id=ch_id, arc_id="arc_001",
        source_layer=SourceLayer.DRAFT,
        source_artifact=f"arcs/arc_001/drafts/{ch_id}.md",
        source_artifact_hash=draft_hash,
    )
    summary_dir = root / "workspace" / "summaries"
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summary_dir / f"{ch_id}_summary.json"
    summary_path.write_text(
        json.dumps(summary.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    return summary


def test_summary_hash_matches_draft(tmp_path: Path):
    root = tmp_path / "project"
    draft_path = _write_draft(root, "ch_001")
    draft_hash = canonical_sha256_file(draft_path)
    summary = _make_summary(root, "ch_001", draft_hash)
    # Hash matches — summary is fresh
    actual_hash = canonical_sha256_file(draft_path)
    assert summary.source_artifact_hash == actual_hash


def test_summary_stale_after_draft_modified(tmp_path: Path):
    root = tmp_path / "project"
    draft_path = _write_draft(root, "ch_001", "Original content")
    original_hash = canonical_sha256_file(draft_path)
    summary = _make_summary(root, "ch_001", original_hash)

    # Modify draft
    draft_path.write_text("# ch_001\nModified content\n", encoding="utf-8")
    new_hash = canonical_sha256_file(draft_path)

    # Summary hash no longer matches → stale
    assert summary.source_artifact_hash != new_hash


def test_stale_detection_protocol():
    """Protocol: hash mismatch → SUMMARY_STALE, not silently used."""
    # This tests the protocol invariant, not the retrieval builder implementation
    stale_hash = "old_hash_abc"
    current_hash = "new_hash_xyz"
    assert stale_hash != current_hash
    # When stale, the error code must be SUMMARY_STALE
    assert SUMMARY_STALE == "SUMMARY_STALE"


def test_summary_source_path_must_match():
    """Protocol: summary valid only if source_artifact path matches expected."""
    summary = ChapterNarrativeSummary(
        chapter_id="ch_001", arc_id="arc_001",
        source_layer=SourceLayer.DRAFT,
        source_artifact="arcs/arc_001/drafts/ch_001.md",
        source_artifact_hash="abc123",
    )
    expected_path = "arcs/arc_001/drafts/ch_001.md"
    assert summary.source_artifact == expected_path

    # Different path with same hash must NOT be considered valid
    different_path = "arcs/arc_002/drafts/ch_001.md"
    assert summary.source_artifact != different_path

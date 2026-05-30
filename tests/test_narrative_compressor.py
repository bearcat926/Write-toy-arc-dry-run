"""NarrativeCompressor tests."""
import json
import pytest
from pathlib import Path
from novel_workflow.system_scripts.narrative_compressor import NarrativeCompressor
from novel_workflow.schemas.enums import SourceLayer


def _seed_project(root: Path):
    """Create minimal project structure."""
    (root / "arcs" / "arc_001" / "drafts").mkdir(parents=True, exist_ok=True)
    (root / "arcs" / "arc_001" / "drafts" / "ch_001.md").write_text(
        "# Chapter 1: The Beginning\n\n"
        "Alice walked into the room. Bob looked up.\n\n"
        "\"You're late,\" Bob said.\n\n"
        "Alice sat down and opened her notebook.\n",
        encoding="utf-8",
    )


def test_compress_generates_summary(tmp_path: Path):
    _seed_project(tmp_path)
    compressor = NarrativeCompressor(tmp_path)
    summary = compressor.compress("arc_001", "ch_001")
    assert summary.chapter_id == "ch_001"
    assert summary.arc_id == "arc_001"
    assert summary.source_layer == SourceLayer.DRAFT
    assert summary.derived is True
    assert summary.source_artifact == "arcs/arc_001/drafts/ch_001.md"
    assert len(summary.source_artifact_hash) > 0


def test_compress_writes_file(tmp_path: Path):
    _seed_project(tmp_path)
    compressor = NarrativeCompressor(tmp_path)
    compressor.compress("arc_001", "ch_001")
    summary_path = tmp_path / "workspace" / "summaries" / "ch_001_summary.json"
    assert summary_path.exists()
    data = json.loads(summary_path.read_text())
    assert data["chapter_id"] == "ch_001"
    assert data["derived"] is True


def test_compress_extracts_retrieval_tags(tmp_path: Path):
    _seed_project(tmp_path)
    compressor = NarrativeCompressor(tmp_path)
    summary = compressor.compress("arc_001", "ch_001")
    assert len(summary.retrieval_tags) > 0
    assert "Chapter 1: The Beginning" in summary.retrieval_tags


def test_compress_missing_draft_raises(tmp_path: Path):
    compressor = NarrativeCompressor(tmp_path)
    with pytest.raises(FileNotFoundError, match="Draft not found"):
        compressor.compress("arc_001", "ch_999")


def test_compress_source_not_workspace(tmp_path: Path):
    """Summary must not be usable as source (enforced by schema validator)."""
    _seed_project(tmp_path)
    compressor = NarrativeCompressor(tmp_path)
    summary = compressor.compress("arc_001", "ch_001")
    assert not summary.source_artifact.startswith("workspace/")

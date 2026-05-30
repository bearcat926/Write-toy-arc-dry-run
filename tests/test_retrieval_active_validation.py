"""RetrievalValidator — active mode validation tests."""
import json
import pytest
from pathlib import Path
from novel_workflow.validators.retrieval_validator import RetrievalValidator
from novel_workflow.system_scripts.manifest_manager import ManifestManager
from novel_workflow.schemas.manifest import DerivedArtifactEntry


def _seed_manifest_with_summary(root: Path, stale: bool = False):
    """Create a manifest entry and summary file."""
    summary_path = root / "workspace" / "summaries" / "ch_001_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps({
        "chapter_id": "ch_001",
        "arc_id": "arc_001",
        "source_layer": "draft",
        "source_artifact": "arcs/arc_001/drafts/ch_001.md",
        "derived": True,
    }), encoding="utf-8")

    mgr = ManifestManager(root)
    mgr.register_artifact(DerivedArtifactEntry(
        artifact_path="workspace/summaries/ch_001_summary.json",
        artifact_type="narrative_summary",
        builder_name="NarrativeCompressor",
        stale=stale,
        stale_reason="test" if stale else "",
    ))
    mgr.save()


def test_valid_summary_passes(tmp_path: Path):
    _seed_manifest_with_summary(tmp_path)
    validator = RetrievalValidator(tmp_path)
    result = validator.validate_for_active("arc_001", "ch_001")
    assert result.is_valid is True


def test_missing_manifest_entry_fails(tmp_path: Path):
    validator = RetrievalValidator(tmp_path)
    result = validator.validate_for_active("arc_001", "ch_999")
    assert result.is_valid is False
    assert "SUMMARY_MISSING" in result.error_code


def test_stale_summary_fails(tmp_path: Path):
    _seed_manifest_with_summary(tmp_path, stale=True)
    validator = RetrievalValidator(tmp_path)
    result = validator.validate_for_active("arc_001", "ch_001")
    assert result.is_valid is False
    assert "SUMMARY_STALE" in result.error_code


def test_missing_file_fails(tmp_path: Path):
    """Manifest entry exists but file is missing."""
    mgr = ManifestManager(tmp_path)
    mgr.register_artifact(DerivedArtifactEntry(
        artifact_path="workspace/summaries/ch_002_summary.json",
        artifact_type="narrative_summary",
        builder_name="test",
    ))
    mgr.save()
    validator = RetrievalValidator(tmp_path)
    result = validator.validate_for_active("arc_001", "ch_002")
    assert result.is_valid is False


def test_validate_all_chapters(tmp_path: Path):
    _seed_manifest_with_summary(tmp_path)
    validator = RetrievalValidator(tmp_path)
    results = validator.validate_all_chapters("arc_001", ["ch_001", "ch_999"])
    assert results["ch_001"].is_valid is True
    assert results["ch_999"].is_valid is False

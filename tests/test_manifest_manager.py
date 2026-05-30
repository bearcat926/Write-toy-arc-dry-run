"""ManifestManager tests."""
import json
import pytest
from pathlib import Path
from novel_workflow.system_scripts.manifest_manager import ManifestManager
from novel_workflow.schemas.manifest import DerivedArtifactEntry


def test_load_creates_empty_manifest(tmp_path: Path):
    mgr = ManifestManager(tmp_path)
    manifest = mgr.load()
    assert manifest.entries == []
    assert manifest.schema_version == "1.0"


def test_register_artifact(tmp_path: Path):
    mgr = ManifestManager(tmp_path)
    entry = DerivedArtifactEntry(
        artifact_path="workspace/summaries/ch_001_summary.json",
        artifact_type="narrative_summary",
        builder_name="NarrativeCompressor",
    )
    mgr.register_artifact(entry)
    manifest = mgr.load()
    assert len(manifest.entries) == 1
    assert manifest.entries[0].artifact_path == "workspace/summaries/ch_001_summary.json"


def test_register_updates_existing(tmp_path: Path):
    mgr = ManifestManager(tmp_path)
    entry1 = DerivedArtifactEntry(
        artifact_path="workspace/summaries/ch_001_summary.json",
        artifact_type="narrative_summary",
        stale=False,
    )
    entry2 = DerivedArtifactEntry(
        artifact_path="workspace/summaries/ch_001_summary.json",
        artifact_type="narrative_summary",
        stale=True,
        stale_reason="source changed",
    )
    mgr.register_artifact(entry1)
    mgr.register_artifact(entry2)
    manifest = mgr.load()
    assert len(manifest.entries) == 1
    assert manifest.entries[0].stale is True


def test_mark_stale(tmp_path: Path):
    mgr = ManifestManager(tmp_path)
    entry = DerivedArtifactEntry(
        artifact_path="workspace/summaries/ch_001_summary.json",
        artifact_type="narrative_summary",
    )
    mgr.register_artifact(entry)
    mgr.mark_stale("workspace/summaries/ch_001_summary.json", "source hash changed")
    result = mgr.get_entry("workspace/summaries/ch_001_summary.json")
    assert result.stale is True
    assert result.stale_reason == "source hash changed"


def test_save_and_reload(tmp_path: Path):
    mgr = ManifestManager(tmp_path)
    entry = DerivedArtifactEntry(
        artifact_path="workspace/summaries/ch_001_summary.json",
        artifact_type="narrative_summary",
        builder_name="test",
    )
    mgr.register_artifact(entry)
    mgr.save()

    # Verify file exists
    manifest_path = tmp_path / "workspace" / "phase2" / "manifest.json"
    assert manifest_path.exists()

    # Reload and verify
    mgr2 = ManifestManager(tmp_path)
    manifest = mgr2.load()
    assert len(manifest.entries) == 1
    assert manifest.entries[0].builder_name == "test"


def test_get_entry_not_found(tmp_path: Path):
    mgr = ManifestManager(tmp_path)
    assert mgr.get_entry("nonexistent") is None

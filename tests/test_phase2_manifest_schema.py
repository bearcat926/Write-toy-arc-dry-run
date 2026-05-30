"""Phase 2 manifest schema tests."""
import json
import pytest
from novel_workflow.schemas.manifest import (
    DerivedArtifactEntry,
    InputManifest,
    Phase2Manifest,
)


def test_derived_artifact_entry_defaults():
    entry = DerivedArtifactEntry(
        artifact_path="workspace/summaries/ch_001_summary.json",
        artifact_type="narrative_summary",
    )
    assert entry.stale is False
    assert entry.stale_reason == ""
    assert entry.schema_version == "1.0"


def test_input_manifest_instantiation():
    im = InputManifest(
        snapshot_id="snap-001",
        input_files=[{"path": "canon/outline.md", "sha256": "abc123"}],
        complete=True,
    )
    assert im.complete is True
    assert len(im.input_files) == 1


def test_phase2_manifest_full():
    manifest = Phase2Manifest(
        batch_generation_id="batch-001",
        base_commit_sha="abc123",
        context_mode="retrieval_shadow",
        entries=[
            DerivedArtifactEntry(
                artifact_path="workspace/summaries/ch_001_summary.json",
                artifact_type="narrative_summary",
                builder_name="narrative_compressor",
            ),
        ],
        input_manifest=InputManifest(
            snapshot_id="snap-001",
            input_files=[],
        ),
    )
    assert len(manifest.entries) == 1
    assert manifest.entries[0].builder_name == "narrative_compressor"
    assert manifest.input_manifest.snapshot_id == "snap-001"


def test_manifest_serialization():
    manifest = Phase2Manifest(
        batch_generation_id="batch-002",
        entries=[DerivedArtifactEntry(
            artifact_path="workspace/phase2/meta.json",
            artifact_type="phase2_meta",
            stale=True,
            stale_reason="source changed",
        )],
    )
    data = json.loads(manifest.model_dump_json())
    assert data["entries"][0]["stale"] is True
    assert data["entries"][0]["stale_reason"] == "source changed"


def test_manifest_none_input():
    manifest = Phase2Manifest(batch_generation_id="batch-003")
    assert manifest.input_manifest is None
    assert manifest.entries == []

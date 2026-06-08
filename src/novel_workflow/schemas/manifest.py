"""Phase 2 manifest schema — tracks derived artifacts and their provenance.

Also includes DerivedArtifactStoreEntry (B-01) for Phase 3 unified store.
"""
from typing import Literal
from pydantic import Field, field_validator
from .common import SchemaVersioned, Timestamped


class DerivedArtifactStoreEntry(SchemaVersioned):
    """Phase 3 unified artifact entry (B-01).

    TEMP.md §8.4 defines the minimum artifact structure:
    artifact_id, artifact_type, schema_version, derived, generation_id,
    source_hashes, content_hash, status, trace_id.

    This is the canonical structure for the DerivedArtifactStore.
    """
    artifact_id: str
    artifact_type: str
    derived: bool = True
    generation_id: str = ""
    source_hashes: dict[str, str] = Field(default_factory=dict)
    content_hash: str = ""
    status: Literal["staged", "promoted", "stale", "invalid"] = "staged"
    trace_id: str = ""

    @field_validator("source_hashes", mode="before")
    @classmethod
    def _coerce_source_hashes(cls, value):
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, list):
            return {str(item): "" for item in value}
        return value


class DerivedArtifactEntry(SchemaVersioned):
    """Metadata for a single derived artifact."""
    artifact_path: str
    artifact_type: str
    source_artifacts: list[str] = Field(default_factory=list)
    source_artifact_hashes: dict[str, str] = Field(default_factory=dict)
    built_at: str = ""
    builder_name: str = ""
    base_commit_sha: str = ""
    context_mode: str = "legacy"
    content_hash: str = ""
    runtime_id: str = ""
    required: bool = False
    rebuildable: bool = True
    stale: bool = False
    stale_reason: str = ""

    @field_validator("source_artifact_hashes", mode="before")
    @classmethod
    def _coerce_source_artifact_hashes(cls, value):
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, list):
            return {str(item): "" for item in value}
        return value


class InputManifest(SchemaVersioned):
    """Snapshot of all inputs used in a single rebuild batch."""
    snapshot_id: str
    input_files: list[dict] = []
    input_generation_ids: dict[str, str] = {}
    complete: bool = True


class Phase2Manifest(SchemaVersioned, Timestamped):
    """Top-level manifest for Phase 2 derived artifacts."""
    batch_generation_id: str
    base_commit_sha: str = ""
    context_mode: str = "legacy"
    entries: list[DerivedArtifactEntry] = []
    input_manifest: InputManifest | None = None

"""Phase 2 manifest schema — tracks derived artifacts and their provenance."""
from typing import Literal
from pydantic import Field, field_validator
from .common import SchemaVersioned, Timestamped


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

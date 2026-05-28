"""Chapter narrative summary — derived artifact for semantic compression."""
from pydantic import field_validator
from .common import SchemaVersioned, Timestamped
from .enums import SourceLayer, ProtocolVersion


class ChapterNarrativeSummary(SchemaVersioned, Timestamped):
    chapter_id: str
    arc_id: str
    source_layer: SourceLayer
    source_artifact: str
    source_artifact_hash: str
    causal_events: list[str] = []
    character_state_changes: list[dict] = []
    emotional_residue: list[dict] = []
    unresolved_tensions: list[str] = []
    promises_created: list[str] = []
    promises_paid_off: list[str] = []
    foreshadow_updates: list[str] = []
    retrieval_tags: list[str] = []
    derived: bool = True
    protocol_version: ProtocolVersion = ProtocolVersion.PHASE2_V1

    @field_validator("derived")
    @classmethod
    def must_be_derived(cls, v: bool) -> bool:
        if not v:
            raise ValueError("SUMMARY_NOT_DERIVED: ChapterNarrativeSummary must be derived")
        return v

    @field_validator("source_layer")
    @classmethod
    def source_must_be_draft(cls, v: SourceLayer) -> SourceLayer:
        if v != SourceLayer.DRAFT:
            raise ValueError("SUMMARY_SOURCE_LAYER_INVALID: summary source must be draft")
        return v

    @field_validator("source_artifact")
    @classmethod
    def source_not_workspace(cls, v: str) -> str:
        if v.startswith("workspace/"):
            raise ValueError("SUMMARY_SOURCE_NOT_ALLOWED: source_artifact cannot be workspace derived")
        return v

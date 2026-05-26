from pydantic import BaseModel, field_validator
from .common import SchemaVersioned


class LedgerUpdateProposal(SchemaVersioned):
    claim: str
    source_layer: str  # "draft" | "canon" | "arc_working_state"
    source_artifact: str
    evidence: str
    confidence: str  # "high" | "medium" | "low"
    target_ledger: str  # "timeline" | "character_knowledge" | "foreshadowing"
    operation: str
    proposed_change: dict

    @field_validator("evidence")
    @classmethod
    def evidence_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("evidence must not be empty")
        return v

    @field_validator("source_layer", "source_artifact")
    @classmethod
    def source_fields_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("source fields must not be empty")
        return v

from pydantic import BaseModel, field_validator
from .common import SchemaVersioned, Timestamped


class GateRecord(SchemaVersioned, Timestamped):
    gate_id: str
    gate_type: str  # "direction" | "arc_start" | "arc_end"
    target_artifact: str
    decision: str  # "approved" | "rejected"
    author_input_evidence: str
    author_id: str
    source_artifacts: list[str]
    approval_level: str = "lightweight"  # "lightweight" | "strict"
    system_script_version: str = "0.1.0"
    synthetic: bool = False

    @field_validator("author_input_evidence")
    @classmethod
    def evidence_not_empty_when_approved(cls, v: str, info) -> str:
        if info.data.get("decision") == "approved" and not v:
            raise ValueError("author_input_evidence required for approved gate")
        return v

    @field_validator("author_id")
    @classmethod
    def author_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("author_id must be non-empty")
        return v

from pydantic import BaseModel, field_validator
from .common import SchemaVersioned, Timestamped
from ..config import PauseType

_PROGRESS_DENYLIST_KEYWORDS = {"canon_fact", "ledger_entry", "narrative_event"}


class ProgressEntry(SchemaVersioned, Timestamped):
    event_type: str
    artifact_path: str = ""
    details: dict = {}
    contains_narrative_fact: bool = False

    @field_validator("contains_narrative_fact")
    @classmethod
    def reject_narrative_fact(cls, v: bool) -> bool:
        if v:
            raise ValueError("NARRATIVE_FACT_FORBIDDEN: ProgressEntry cannot contain narrative facts")
        return v

    @field_validator("details")
    @classmethod
    def denylist_scan_details(cls, v: dict) -> dict:
        for key in v:
            if key in _PROGRESS_DENYLIST_KEYWORDS:
                raise ValueError(f"DENYLIST_KEYWORD: details contains forbidden key '{key}'")
        return v


class PauseReport(SchemaVersioned, Timestamped):
    pause_type: PauseType
    reason: str
    affected_artifacts: list[str] = []
    evidence: str = ""
    recommended_action: str = ""
    author_options: list[str] = []

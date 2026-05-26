from pydantic import BaseModel
from .common import SchemaVersioned, Timestamped
from ..config import PauseType


class ProgressEntry(SchemaVersioned, Timestamped):
    event_type: str
    artifact_path: str = ""
    details: dict = {}
    contains_narrative_fact: bool = False


class PauseReport(SchemaVersioned, Timestamped):
    pause_type: PauseType
    reason: str
    affected_artifacts: list[str] = []
    evidence: str = ""
    recommended_action: str = ""

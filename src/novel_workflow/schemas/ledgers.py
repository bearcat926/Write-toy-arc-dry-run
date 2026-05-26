from pydantic import BaseModel
from .common import SchemaVersioned


class TimelineEvent(SchemaVersioned):
    event_id: str
    time_marker: str
    summary: str
    participants: list[str] = []
    location: str = ""
    causes: list[str] = []
    effects: list[str] = []
    source_chapter: str = ""


class CharacterKnowledgeEntry(SchemaVersioned):
    character_id: str
    knowledge: str
    knowledge_source: str  # "saw" | "heard" | "inferred" | "document" | "mistaken"
    certainty: str = "confirmed"
    source_chapter: str = ""


class ForeshadowEntry(SchemaVersioned):
    foreshadow_id: str
    summary: str
    status: str = "introduced"
    reader_visible: bool = True
    source_chapter: str = ""

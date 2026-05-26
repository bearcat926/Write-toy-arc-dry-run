from pydantic import BaseModel
from .common import SchemaVersioned


class ArcWorkingStateEntry(SchemaVersioned):
    state_id: str
    source_chapter: str
    key: str
    value: str | int | float | bool | dict | list
    status: str = "working_accepted"
    approval_scope: str = "arc_internal_only"
    depends_on: list[str] = []

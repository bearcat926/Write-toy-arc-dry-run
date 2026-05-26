from pydantic import BaseModel
from .common import SchemaVersioned


class ChapterEffectReport(SchemaVersioned):
    chapter_id: str
    scene_goal: str = ""
    state_changes: list[str] = []
    character_choices: list[str] = []
    conflict_or_pressure_change: list[str] = []
    new_reader_questions: list[str] = []
    promises_paid_off: list[str] = []
    promises_created: list[str] = []
    pov_boundary_status: str = "pass"  # "pass" | "warning" | "fail"
    arc_contract_alignment: list[str] = []

from pydantic import BaseModel
from .common import SchemaVersioned


class ReviewReport(SchemaVersioned):
    reviewer_role: str  # "continuity_auditor" | "plot_doctor" | "character_coach" | "line_editor"
    blocking_issues: list[str] = []
    high_priority_revisions: list[str] = []
    optional_suggestions: list[str] = []
    do_not_change: list[str] = []
    evidence_quotes: list[str] = []
    recommended_action: str = "approve"  # "approve" | "revise" | "pause"


class RevisionBrief(SchemaVersioned):
    chapter_id: str
    items: list[str]  # max 5 high priority revisions
    source_reviews: list[str] = []  # reviewer roles that contributed

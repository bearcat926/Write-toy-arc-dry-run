from enum import Enum

SUPPORTED_SCHEMA_VERSIONS: set[str] = {"1.0"}


class PauseType(str, Enum):
    HARD_PAUSE = "hard_pause"
    CREATIVE_REVIEW = "creative_review"
    SOFT_WARNING = "soft_warning"


PAUSE_TAXONOMY = [pt.value for pt in PauseType]

RETRY_POLICY = {
    "max_schema_repairable": 2,
    "max_audit_failure": 2,
}

ROLE_ALLOWLIST = {
    "agent": {
        "read": ["canon", "ledgers", "approved_outline", "arc_contract",
                  "arc_working_state", "chapter_context", "character_mind_card", "rag_results"],
        "write": ["drafts", "reviews", "proposals", "revision_brief",
                   "polish_proposal", "draft_variants"],
    },
    "system_script": {
        "write": ["arc_working_state", "ledger_diff", "canon_diff",
                   "checkpoint", "gate_records", "pause_report", "rollback_snapshot"],
    },
    "plugin": {
        "read": ["canon", "ledgers", "arc_report", "dashboard_report"],
        "write": ["inspiration", "prompts", "variants", "profiles", "asset_index"],
    },
}

LEDGER_OPERATIONS = {
    "timeline": {"append_event", "correction"},
    "character_knowledge": {"append_knowledge", "mark_corrected"},
    "foreshadowing": {"introduce_foreshadow", "develop_foreshadow", "pay_off_foreshadow", "abandon_foreshadow"},
}

FORESHADOW_TRANSITIONS = {
    "introduced": {"developed", "paid_off", "abandoned"},
    "developed": {"paid_off", "abandoned"},
    "paid_off": set(),
    "abandoned": set(),
}

from enum import Enum

from pydantic import BaseModel


class FailureCategory(str, Enum):
    # Retryable (schema-repairable)
    MALFORMED_JSON = "malformed_json"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    WRONG_TYPE = "wrong_type"
    INVALID_ENUM = "invalid_enum"

    # Non-retryable
    EVIDENCE_NOT_FOUND = "evidence_not_found"
    CLAIM_EVIDENCE_MISMATCH = "claim_evidence_mismatch"
    CANON_DIRECT_CONFLICT = "canon_direct_conflict"
    PATH_VIOLATION = "path_violation"
    GATE_EVIDENCE_MISSING = "gate_evidence_missing"
    SECURITY_VIOLATION = "security_violation"
    AUDIT_BLOCKING = "audit_blocking"
    CHAPTER_EFFECT_FAIL = "chapter_effect_fail"
    AWS_CANON_CONFLICT = "aws_canon_conflict"
    APPLY_VALIDATION_FAIL = "apply_validation_fail"


RETRYABLE_CATEGORIES = {
    FailureCategory.MALFORMED_JSON,
    FailureCategory.MISSING_REQUIRED_FIELD,
    FailureCategory.WRONG_TYPE,
    FailureCategory.INVALID_ENUM,
}


class FailureEvent(BaseModel):
    category: FailureCategory
    source: str  # "proposal_validator", "gate_validator", "audit", "chapter_effect", etc.
    chapter_id: str = ""
    artifact_path: str = ""
    message: str = ""
    evidence: str = ""
    retryable: bool = False
    retry_count: int = 0
    max_retries: int = 2

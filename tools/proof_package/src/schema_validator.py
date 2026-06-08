"""Schema Validator — Phase 1+3 (B-03).

Validates schema_version and required fields for artifact types.
Phase 3 adds field-level validation via VALIDATORS registry.
"""
from typing import Callable
from ..config import SUPPORTED_SCHEMA_VERSIONS

# Phase 3: registry of per-type field validators
_VALIDATORS: dict[str, Callable[[dict], list[str]]] = {}


def register_validator(artifact_type: str, fn: Callable[[dict], list[str]]):
    """Register a field-level validator for an artifact type.

    fn(data) -> list of error strings (empty = valid).
    """
    _VALIDATORS[artifact_type] = fn


def _validate_derived_store_entry(data: dict) -> list[str]:
    """Validate DerivedArtifactStoreEntry required fields (B-03)."""
    errors = []
    for field in ("artifact_id", "artifact_type", "schema_version"):
        if field not in data or not data[field]:
            errors.append(f"MISSING_REQUIRED_FIELD: {field}")
    if "status" in data and data["status"] not in ("staged", "promoted", "stale", "invalid"):
        errors.append(f"INVALID_STATUS: {data['status']}")
    if "derived" in data and not isinstance(data["derived"], bool):
        errors.append("INVALID_TYPE: derived must be bool")
    return errors


def _validate_character_drift_finding(data: dict) -> list[str]:
    """Validate CharacterDriftFinding required fields."""
    errors = []
    for field in ("finding_id", "character_id", "chapter_id", "drift_type", "severity", "evidence"):
        if field not in data or not data[field]:
            errors.append(f"MISSING_REQUIRED_FIELD: {field}")
    valid_severities = ("soft_warning", "creative_review", "hard_pause")
    if "severity" in data and data["severity"] not in valid_severities:
        errors.append(f"INVALID_SEVERITY: {data['severity']}")
    return errors


def _validate_governance_report(data: dict) -> list[str]:
    """Validate GovernanceReport required fields."""
    errors = []
    for field in ("chapter_id", "max_severity", "recommended_action"):
        if field not in data:
            errors.append(f"MISSING_REQUIRED_FIELD: {field}")
    valid_actions = ("approve", "review", "block")
    if "recommended_action" in data and data["recommended_action"] not in valid_actions:
        errors.append(f"INVALID_ACTION: {data['recommended_action']}")
    return errors


# Register built-in validators
register_validator("derived_store_entry", _validate_derived_store_entry)
register_validator("character_drift_finding", _validate_character_drift_finding)
register_validator("governance_report", _validate_governance_report)


class SchemaValidator:
    def validate(self, data: dict) -> bool:
        version = data.get("schema_version")
        if version is None:
            raise ValueError("MISSING_SCHEMA_VERSION")
        if version not in SUPPORTED_SCHEMA_VERSIONS:
            raise ValueError(f"UNKNOWN_SCHEMA_VERSION: {version}")
        return True

    def validate_fields(self, artifact_type: str, data: dict) -> list[str]:
        """Phase 3: field-level validation for a specific artifact type.

        Returns list of error strings. Empty list = valid.
        Raises ValueError for schema_version issues.
        """
        self.validate(data)
        validator = _VALIDATORS.get(artifact_type)
        if validator:
            return validator(data)
        return []

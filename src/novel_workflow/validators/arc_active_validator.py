"""ArcActiveValidator — validates arc plan and beat plan for arc_active mode.

Checks that arc_plan and chapter_beat_plan exist in workspace and are non-stale.
"""
from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class ArcValidationResult:
    """Result of arc active validation."""
    is_valid: bool
    error_code: str = ""
    error_message: str = ""


class ArcActiveValidator:
    """Validates arc plan readiness for arc_active mode."""

    def __init__(self, root: Path):
        self._root = root

    def validate_arc_plan(self, arc_id: str) -> ArcValidationResult:
        """Check that arc plan exists and is valid."""
        plan_path = self._root / "workspace" / "arc_plan" / f"arc_{arc_id}_plan.json"
        if not plan_path.exists():
            return ArcValidationResult(
                is_valid=False,
                error_code="ARC_PLAN_MISSING",
                error_message=f"Arc plan not found: {plan_path}",
            )
        try:
            data = json.loads(plan_path.read_text(encoding="utf-8"))
            if data.get("stale", False):
                return ArcValidationResult(
                    is_valid=False,
                    error_code="ARC_PLAN_STALE",
                    error_message="Arc plan is stale",
                )
        except (json.JSONDecodeError, KeyError):
            return ArcValidationResult(
                is_valid=False,
                error_code="ARC_PLAN_INVALID",
                error_message="Arc plan file is invalid JSON",
            )
        return ArcValidationResult(is_valid=True)

    def validate_beat_plan(self, arc_id: str, chapter_id: str) -> ArcValidationResult:
        """Check that chapter beat plan exists and is valid."""
        beat_path = self._root / "workspace" / "arc_plan" / f"arc_{arc_id}_{chapter_id}_beat_plan.json"
        if not beat_path.exists():
            return ArcValidationResult(
                is_valid=False,
                error_code="BEAT_PLAN_MISSING",
                error_message=f"Beat plan not found: {beat_path}",
            )
        return ArcValidationResult(is_valid=True)

    def validate_for_active(self, arc_id: str, chapter_id: str) -> ArcValidationResult:
        """Full validation for arc_active mode."""
        # Check arc plan
        result = self.validate_arc_plan(arc_id)
        if not result.is_valid:
            return result
        # Check beat plan
        result = self.validate_beat_plan(arc_id, chapter_id)
        if not result.is_valid:
            return result
        return ArcValidationResult(is_valid=True)

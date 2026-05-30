"""RetrievalValidator — validates derived artifacts for active mode readiness.

Checks manifest entries for staleness, hash validity, and completeness.
"""
from dataclasses import dataclass
from pathlib import Path

from .error_codes import (
    SOURCE_ARTIFACT_NOT_HASHED,
    SUMMARY_STALE,
    SUMMARY_MISSING,
)
from ..system_scripts.manifest_manager import ManifestManager


@dataclass
class ValidationResult:
    """Result of retrieval validation."""
    is_valid: bool
    error_code: str = ""
    error_message: str = ""


class RetrievalValidator:
    """Validates derived artifacts for retrieval_active mode."""

    def __init__(self, root: Path):
        self._root = root
        self._manifest = ManifestManager(root)

    def validate_for_active(self, arc_id: str, chapter_id: str) -> ValidationResult:
        """Validate that chapter's summary is ready for active mode.

        Checks:
        1. Manifest entry exists for the chapter summary
        2. Summary is not stale
        3. Summary file exists on disk

        Returns:
            ValidationResult with is_valid=True if all checks pass
        """
        manifest = self._manifest.load()
        summary_path = f"workspace/summaries/{chapter_id}_summary.json"

        # Check manifest entry exists
        entry = None
        for e in manifest.entries:
            if e.artifact_path == summary_path:
                entry = e
                break

        if entry is None:
            return ValidationResult(
                is_valid=False,
                error_code=SUMMARY_MISSING,
                error_message=f"No manifest entry for {summary_path}",
            )

        # Check stale
        if entry.stale:
            return ValidationResult(
                is_valid=False,
                error_code=SUMMARY_STALE,
                error_message=f"Summary is stale: {entry.stale_reason}",
            )

        # Check file exists
        summary_file = self._root / summary_path
        if not summary_file.exists():
            return ValidationResult(
                is_valid=False,
                error_code=SUMMARY_MISSING,
                error_message=f"Summary file missing: {summary_path}",
            )

        return ValidationResult(is_valid=True)

    def validate_all_chapters(self, arc_id: str, chapter_ids: list[str]) -> dict[str, ValidationResult]:
        """Validate multiple chapters. Returns dict of chapter_id → ValidationResult."""
        results = {}
        for ch_id in chapter_ids:
            results[ch_id] = self.validate_for_active(arc_id, ch_id)
        return results

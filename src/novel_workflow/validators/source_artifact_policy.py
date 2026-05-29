"""Source artifact policy — restricts which files can be provenance sources."""
import re
from dataclasses import dataclass

from ..schemas.enums import SourceLayer, HashStrategy
from ..schemas.hash_utils import get_hash_strategy_for_source
from ..validators.error_codes import (
    DERIVED_SOURCE_NOT_ALLOWED,
    INVALID_SOURCE_LAYER,
    SOURCE_ARTIFACT_LAYER_MISMATCH,
    SOURCE_ARTIFACT_DENYLISTED,
    SOURCE_ARTIFACT_NOT_HASHED,
)


@dataclass
class ValidationResult:
    is_valid: bool
    error_code: str = ""
    error_category: str = ""


ALLOWED_SOURCE_PATTERNS: dict[str, re.Pattern] = {
    SourceLayer.DRAFT.value: re.compile(r"^arcs/[^/]+/drafts/ch_\d{3}\.md$"),
    SourceLayer.CANON.value: re.compile(
        r"^canon/(approved_outline\.md|manuscript/[^/]+\.md|characters/.+\.json)$"
    ),
    SourceLayer.ARC_WORKING_STATE.value: re.compile(
        r"^arcs/[^/]+/arc_working_state\.json$"
    ),
}

DENY_SOURCE_PREFIXES = (
    "workspace/metrics",
    "workspace/retrieval_traces/",
    "workspace/reports/",
    "workspace/phase2/",
    "workspace/narrative_graph_index",
    "workspace/foreshadow_lifecycle_index",
    "workspace/character_state/",
    "workspace/arc_plan/",
)

DERIVED_SOURCE_PREFIXES = (
    "workspace/summaries/",
    "workspace/reports/",
    "workspace/retrieval_traces/",
    "workspace/phase2/",
    "workspace/narrative_graph_index",
    "workspace/foreshadow_lifecycle_index",
    "workspace/character_state/",
    "workspace/arc_plan/",
)


def is_derived_source(source_artifact: str) -> bool:
    """Check if source_artifact points to a workspace derived file."""
    return any(source_artifact.startswith(p) for p in DERIVED_SOURCE_PREFIXES)


def validate_source_artifact(source_layer: str, source_artifact: str) -> ValidationResult:
    """Validate that a source artifact is an allowed provenance source."""
    # Check denylist first
    if any(source_artifact.startswith(p) for p in DENY_SOURCE_PREFIXES):
        return ValidationResult(
            is_valid=False,
            error_code=SOURCE_ARTIFACT_DENYLISTED,
            error_category="semantic_invalid",
        )

    # Check derived sources
    if source_artifact.startswith("workspace/summaries/"):
        return ValidationResult(
            is_valid=False,
            error_code=DERIVED_SOURCE_NOT_ALLOWED,
            error_category="semantic_invalid",
        )

    # Check source_layer is valid
    if source_layer not in ALLOWED_SOURCE_PATTERNS:
        return ValidationResult(
            is_valid=False,
            error_code=INVALID_SOURCE_LAYER,
            error_category="semantic_invalid",
        )

    # Check path matches layer pattern
    pattern = ALLOWED_SOURCE_PATTERNS[source_layer]
    if not pattern.match(source_artifact):
        return ValidationResult(
            is_valid=False,
            error_code=SOURCE_ARTIFACT_LAYER_MISMATCH,
            error_category="semantic_invalid",
        )

    # Check hash strategy — NOT_HASHED artifacts cannot be provenance sources
    strategy = get_hash_strategy_for_source(source_artifact)
    if strategy == HashStrategy.NOT_HASHED:
        return ValidationResult(
            is_valid=False,
            error_code=SOURCE_ARTIFACT_NOT_HASHED,
            error_category="semantic_invalid",
        )

    return ValidationResult(is_valid=True)

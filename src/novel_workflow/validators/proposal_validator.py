from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from ..schemas.proposal import LedgerUpdateProposal
from ..config import LEDGER_OPERATIONS


@dataclass
class ValidationResult:
    is_valid: bool
    error_code: str = ""
    error_category: str = ""  # "schema_repairable" | "semantic_invalid"


class ProposalValidator:
    def __init__(self, project_root: Path):
        self._root = project_root

    def validate(self, proposal: LedgerUpdateProposal) -> ValidationResult:
        # Check operation matches target_ledger
        allowed_ops = LEDGER_OPERATIONS.get(proposal.target_ledger, set())
        if proposal.operation not in allowed_ops:
            return ValidationResult(
                is_valid=False,
                error_code=f"INVALID_OPERATION: {proposal.operation} not in {allowed_ops}",
                error_category="schema_repairable",
            )

        # Check source_artifact is path-safe (no traversal, no absolute)
        pure = PurePosixPath(proposal.source_artifact)
        if ".." in pure.parts or pure.is_absolute():
            return ValidationResult(
                is_valid=False,
                error_code=f"UNSAFE_SOURCE_PATH: {proposal.source_artifact}",
                error_category="semantic_invalid",
            )

        # Check source artifact exists
        artifact_path = self._root / proposal.source_artifact
        if not artifact_path.exists():
            return ValidationResult(
                is_valid=False,
                error_code=f"INVALID_SOURCE_ARTIFACT: {proposal.source_artifact}",
                error_category="semantic_invalid",
            )

        # Check evidence is non-empty (already enforced by Pydantic, but double-check)
        if not proposal.evidence or not proposal.evidence.strip():
            return ValidationResult(
                is_valid=False,
                error_code="MISSING_EVIDENCE",
                error_category="schema_repairable",
            )

        return ValidationResult(is_valid=True)

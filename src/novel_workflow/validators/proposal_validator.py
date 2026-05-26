from dataclasses import dataclass
from pathlib import Path
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

        # Check source artifact exists
        artifact_path = self._root / proposal.source_artifact
        if not artifact_path.exists():
            return ValidationResult(
                is_valid=False,
                error_code=f"INVALID_SOURCE_ARTIFACT: {proposal.source_artifact}",
                error_category="semantic_invalid",
            )

        return ValidationResult(is_valid=True)

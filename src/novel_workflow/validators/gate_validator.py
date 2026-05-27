from ..schemas.gate import GateRecord


class GateValidator:
    def validate(self, gate: GateRecord) -> bool:
        if gate.decision == "approved":
            if not gate.author_input_evidence or not gate.author_input_evidence.strip():
                raise ValueError("MISSING_GATE_EVIDENCE")
            if gate.author_input_evidence.strip().startswith("auto_"):
                raise ValueError("AUTO_GENERATED_GATE_EVIDENCE")
            if hasattr(gate, 'approval_level') and gate.approval_level == "strict":
                if len(gate.author_input_evidence.strip()) < 20:
                    raise ValueError("STRICT_EVIDENCE_TOO_SHORT: strict gate requires evidence >= 20 characters")
        if gate.decision == "rejected":
            if not gate.author_input_evidence or not gate.author_input_evidence.strip():
                raise ValueError("REJECTED_GATE_EVIDENCE_REQUIRED")
        return True

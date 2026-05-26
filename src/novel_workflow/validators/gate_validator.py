from ..schemas.gate import GateRecord


class GateValidator:
    def validate(self, gate: GateRecord) -> bool:
        if gate.decision == "approved":
            if not gate.author_input_evidence or not gate.author_input_evidence.strip():
                raise ValueError("MISSING_GATE_EVIDENCE")
            if gate.author_input_evidence.strip().startswith("auto_"):
                raise ValueError("AUTO_GENERATED_GATE_EVIDENCE")
        return True

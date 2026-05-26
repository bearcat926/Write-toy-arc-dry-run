from ..config import FORESHADOW_TRANSITIONS


class LedgerDiffGenerator:
    def generate(self, proposals: list[dict]) -> dict:
        operations = []
        foreshadow_states: dict[str, str] = {}

        for p in proposals:
            ledger = p["target_ledger"]
            op = p["operation"]
            change = p["proposed_change"]

            if ledger == "foreshadowing":
                fs_id = change.get("foreshadow_id", "")
                status_from = change.get("status_from")
                status_to = change.get("status_to", "")

                if status_from is None:
                    foreshadow_states[fs_id] = "introduced"
                else:
                    allowed = FORESHADOW_TRANSITIONS.get(status_from, set())
                    if status_to not in allowed:
                        raise ValueError(
                            f"INVALID_FORESHADOW_TRANSITION: {status_from} -> {status_to}"
                        )
                    foreshadow_states[fs_id] = status_to

            operations.append({
                "type": "append" if "append" in op else op,
                "target_ledger": ledger,
                "operation": op,
                "data": change,
            })

        return {"schema_version": "1.0", "operations": operations}

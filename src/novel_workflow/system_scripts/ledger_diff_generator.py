from ..config import FORESHADOW_TRANSITIONS
from ..validators.source_artifact_policy import validate_source_artifact


class LedgerDiffGenerator:
    def generate(self, proposals: list[dict]) -> dict:
        operations = []
        foreshadow_states: dict[str, str] = {}

        for p in proposals:
            # Validate source provenance
            source_layer = p.get("source_layer", "")
            source_artifact = p.get("source_artifact", "")
            if not source_layer or not source_artifact:
                raise ValueError("MISSING_PROVENANCE: proposal lacks source_layer/source_artifact")
            result = validate_source_artifact(source_layer, source_artifact)
            if not result.is_valid:
                raise ValueError(f"{result.error_code}: {source_artifact}")

            ledger = p["target_ledger"]
            op = p["operation"]
            change = p["proposed_change"]

            if ledger == "timeline" and op == "correction":
                operations.append({
                    "type": "correction",
                    "target_ledger": ledger,
                    "operation": op,
                    "data": {**change, "corrects_event_id": change.get("corrects_event_id", change.get("event_id", ""))},
                    "source_layer": source_layer,
                    "source_artifact": source_artifact,
                    "source_artifact_hash": p.get("source_artifact_hash", ""),
                    "is_derived": False,
                })
                continue

            if ledger == "character_knowledge" and op == "mark_corrected":
                operations.append({
                    "type": "mark_corrected",
                    "target_ledger": ledger,
                    "operation": op,
                    "data": {**change, "corrects_previous": True},
                    "source_layer": source_layer,
                    "source_artifact": source_artifact,
                    "source_artifact_hash": p.get("source_artifact_hash", ""),
                    "is_derived": False,
                })
                continue

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
                "source_layer": source_layer,
                "source_artifact": source_artifact,
                "source_artifact_hash": p.get("source_artifact_hash", ""),
                "is_derived": False,
            })

        return {"schema_version": "1.0", "operations": operations}

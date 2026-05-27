import re as _re
from pathlib import Path, PurePosixPath
from ..config import ROLE_ALLOWLIST


class PathSafetyError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


# Agent positive allowlist: arcs/<arc_id>/(drafts|reviews|proposals|variants)/...
_AGENT_ALLOWED_PATTERN = _re.compile(r"^arcs/[^/]+/(drafts|reviews|proposals|variants)/")

# System script artifact-specific allowlists
_SYSTEM_SCRIPT_ALLOWED = {
    "arc_working_state": _re.compile(r"^arcs/[^/]+/arc_working_state\.json$"),
    "ledger_diff": _re.compile(r"^arcs/[^/]+/reports/ledger_diff\.json$"),
    "canon_diff": _re.compile(r"^arcs/[^/]+/reports/canon_diff\.json$"),
    "checkpoint": _re.compile(r"^arcs/[^/]+/checkpoints/.*\.json$"),
    "gate_record": _re.compile(r"^(gates/[^/]+\.json|arcs/[^/]+/gates/[^/]+\.json)$"),
    "pause_report": _re.compile(r"^arcs/[^/]+/reports/pause_report\.md$"),
    "arc_report": _re.compile(r"^arcs/[^/]+/reports/arc_report\.md$"),
    "apply_record": _re.compile(r"^arcs/[^/]+/reports/apply_record\.json$"),
    "rollback_snapshot": _re.compile(r"^arcs/[^/]+/archive/snapshot_.+$"),
    "consumed_hashes": _re.compile(r"^workspace/consumed_hashes\.json$"),
    "progress": _re.compile(r"^workspace/progress\.jsonl$"),
    "metrics": _re.compile(r"^workspace/metrics\.jsonl$"),
    "dashboard": _re.compile(r"^workspace/dashboard_report\.md$"),
    "canon_manuscript": _re.compile(r"^canon/manuscript/[^/]+\.md$"),
    "canon_characters": _re.compile(r"^canon/characters/character_mind_cards/[^/]+\.json$"),
    "ledgers": _re.compile(r"^ledgers/[^/]+\.json$"),
    "arc_contract": _re.compile(r"^arcs/[^/]+/arc_contract\.md$"),
    "direction_gate": _re.compile(r"^gates/direction_gate\.json$"),
}


class PathSafetyGuard:
    def __init__(self, project_root: Path):
        self._root = project_root.resolve()

    def check_write_path(self, path: str, role: str, artifact_type: str = "") -> Path:
        pure = PurePosixPath(path)

        # Reject traversal
        if ".." in pure.parts:
            raise PathSafetyError("PATH_TRAVERSAL_REJECTED", f"Path contains '..': {path}")

        # Reject absolute
        if pure.is_absolute():
            raise PathSafetyError("ABSOLUTE_PATH_REJECTED", f"Absolute path not allowed: {path}")

        # Reject Windows drive escape
        if len(path) >= 2 and path[1] == ":":
            raise PathSafetyError("ABSOLUTE_PATH_REJECTED", f"Windows drive path not allowed: {path}")

        resolved = (self._root / pure).resolve()

        # Reject symlink escape
        if not str(resolved).startswith(str(self._root)):
            raise PathSafetyError("SYMLINK_ESCAPE_REJECTED", f"Path escapes workspace: {path}")

        # Role-based positive allowlist
        if role == "agent":
            if not _AGENT_ALLOWED_PATTERN.match(path):
                raise PathSafetyError("AGENT_WRITE_DENIED",
                    f"Agent can only write to arcs/<id>/(drafts|reviews|proposals|variants)/. Got: {path}")

        elif role == "plugin":
            allowed = ROLE_ALLOWLIST.get("plugin", {}).get("write", [])
            top_dir = pure.parts[0] if pure.parts else ""
            if top_dir not in allowed:
                raise PathSafetyError("PLUGIN_WRITE_DENIED", f"Plugin cannot write to: {top_dir}")

        elif role == "system_script":
            # Artifact-type-aware allowlist
            if artifact_type and artifact_type in _SYSTEM_SCRIPT_ALLOWED:
                pattern = _SYSTEM_SCRIPT_ALLOWED[artifact_type]
                if not pattern.match(path):
                    raise PathSafetyError(
                        "SYSTEM_SCRIPT_ARTIFACT_MISMATCH",
                        f"Artifact type '{artifact_type}' does not match path: {path}"
                    )
            elif artifact_type:
                raise PathSafetyError(
                    "UNKNOWN_ARTIFACT_TYPE",
                    f"Unknown artifact type: {artifact_type}"
                )
            else:
                # No artifact_type specified: reject (caller must specify)
                raise PathSafetyError(
                    "MISSING_ARTIFACT_TYPE",
                    "system_script writes require artifact_type parameter"
                )

        else:
            raise PathSafetyError("UNKNOWN_ROLE", f"Unknown role: {role}")

        return resolved

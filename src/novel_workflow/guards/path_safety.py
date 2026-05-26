import re as _re
from pathlib import Path, PurePosixPath
from ..config import ROLE_ALLOWLIST


class PathSafetyError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


# Agent positive allowlist: arcs/<arc_id>/(drafts|reviews|proposals|variants)/...
_AGENT_ALLOWED_PATTERN = _re.compile(r"^arcs/[^/]+/(drafts|reviews|proposals|variants)/")


class PathSafetyGuard:
    def __init__(self, project_root: Path):
        self._root = project_root.resolve()

    def check_write_path(self, path: str, role: str) -> Path:
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
            # System script can write to any allowed path
            pass

        else:
            raise PathSafetyError("UNKNOWN_ROLE", f"Unknown role: {role}")

        return resolved

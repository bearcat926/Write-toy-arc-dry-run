"""RebuildLock — prevents concurrent derived artifact rebuilds.

Uses a JSON lock file at workspace/phase2/rebuild.lock.
"""
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path


LOCK_DIR = "workspace/phase2"
LOCK_FILE = "rebuild.lock"
LOCK_EXPIRY_SECONDS = 300  # 5 minutes


class RebuildLock:
    """File-based rebuild lock for Phase 2 derived artifacts."""

    def __init__(self, root: Path):
        self._root = root
        self._lock_dir = root / LOCK_DIR
        self._lock_path = self._lock_dir / LOCK_FILE

    def acquire(self, owner: str = "unknown") -> bool:
        """Try to acquire the rebuild lock. Returns True if acquired."""
        if self.is_locked():
            return False

        self._lock_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        lock_data = {
            "schema_version": "1.0",
            "owner": owner,
            "pid": os.getpid(),
            "acquired_at": now.isoformat(),
            "expires_at": datetime.fromtimestamp(
                now.timestamp() + LOCK_EXPIRY_SECONDS, tz=timezone.utc
            ).isoformat(),
        }

        try:
            self._lock_path.write_text(json.dumps(lock_data, indent=2), encoding="utf-8")
            return True
        except OSError:
            return False

    def release(self) -> None:
        """Release the lock if we own it."""
        if self._lock_path.exists():
            try:
                self._lock_path.unlink()
            except OSError:
                pass

    def is_locked(self) -> bool:
        """Check if lock exists and is not expired."""
        if not self._lock_path.exists():
            return False

        try:
            data = json.loads(self._lock_path.read_text(encoding="utf-8"))
            expires_at = datetime.fromisoformat(data.get("expires_at", ""))
            if datetime.now(timezone.utc) > expires_at:
                # Lock expired — auto-release
                self.release()
                return False
            return True
        except (json.JSONDecodeError, ValueError, KeyError):
            # Corrupt lock file — treat as locked
            return True

    def force_release(self) -> None:
        """Force release stale or corrupt lock."""
        if self._lock_path.exists():
            try:
                self._lock_path.unlink()
            except OSError:
                pass

    def get_lock_info(self) -> dict | None:
        """Get current lock info, or None if not locked."""
        if not self._lock_path.exists():
            return None
        try:
            return json.loads(self._lock_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

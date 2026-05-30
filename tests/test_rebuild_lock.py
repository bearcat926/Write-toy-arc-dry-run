"""RebuildLock tests."""
import json
import time
import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from novel_workflow.system_scripts.rebuild_lock import RebuildLock, LOCK_EXPIRY_SECONDS


def test_acquire_and_release(tmp_path: Path):
    lock = RebuildLock(tmp_path)
    assert lock.acquire("test") is True
    assert lock.is_locked() is True
    lock.release()
    assert lock.is_locked() is False


def test_double_acquire_fails(tmp_path: Path):
    lock = RebuildLock(tmp_path)
    assert lock.acquire("first") is True
    assert lock.acquire("second") is False
    lock.release()


def test_force_release(tmp_path: Path):
    lock = RebuildLock(tmp_path)
    lock.acquire("test")
    assert lock.is_locked() is True
    lock.force_release()
    assert lock.is_locked() is False


def test_expired_lock_auto_releases(tmp_path: Path):
    lock = RebuildLock(tmp_path)
    # Create an expired lock manually
    lock._lock_dir.mkdir(parents=True, exist_ok=True)
    expired_data = {
        "schema_version": "1.0",
        "owner": "old_process",
        "pid": 99999,
        "acquired_at": (datetime.now(timezone.utc) - timedelta(seconds=LOCK_EXPIRY_SECONDS + 10)).isoformat(),
        "expires_at": (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat(),
    }
    lock._lock_path.write_text(json.dumps(expired_data), encoding="utf-8")
    # Should detect as not locked (auto-release)
    assert lock.is_locked() is False
    # Lock file should be deleted
    assert not lock._lock_path.exists()


def test_get_lock_info(tmp_path: Path):
    lock = RebuildLock(tmp_path)
    assert lock.get_lock_info() is None
    lock.acquire("test_owner")
    info = lock.get_lock_info()
    assert info is not None
    assert info["owner"] == "test_owner"
    lock.release()


def test_release_nonexistent_lock(tmp_path: Path):
    lock = RebuildLock(tmp_path)
    # Should not raise
    lock.release()

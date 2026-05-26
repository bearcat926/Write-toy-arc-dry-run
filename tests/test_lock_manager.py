import pytest
from novel_workflow.guards.lock_manager import LockManager, LockTimeoutError


def test_acquire_release():
    mgr = LockManager()
    mgr.acquire("test_lock")
    mgr.release("test_lock")


def test_context_manager():
    mgr = LockManager()
    with mgr.hold("test_lock"):
        pass  # Should not raise


def test_release_unlocked():
    mgr = LockManager()
    mgr.release("nonexistent")  # Should not raise


def test_context_manager_finally_releases():
    mgr = LockManager()
    try:
        with mgr.hold("test_lock"):
            raise ValueError("test error")
    except ValueError:
        pass
    # Lock should be released, acquire should succeed
    mgr.acquire("test_lock")
    mgr.release("test_lock")

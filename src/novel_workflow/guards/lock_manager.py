import threading
from contextlib import contextmanager


class LockTimeoutError(Exception):
    pass


class LockManager:
    def __init__(self):
        self._locks: dict[str, threading.Lock] = {}
        self._lock_registry_lock = threading.Lock()

    def _get_lock(self, name: str) -> threading.Lock:
        with self._lock_registry_lock:
            if name not in self._locks:
                self._locks[name] = threading.Lock()
            return self._locks[name]

    def acquire(self, lock_name: str, timeout: float = 30.0) -> bool:
        lock = self._get_lock(lock_name)
        acquired = lock.acquire(timeout=timeout)
        if not acquired:
            raise LockTimeoutError(f"Failed to acquire lock '{lock_name}' within {timeout}s")
        return True

    def release(self, lock_name: str) -> None:
        lock = self._get_lock(lock_name)
        try:
            lock.release()
        except RuntimeError:
            pass  # Lock not held

    @contextmanager
    def hold(self, lock_name: str, timeout: float = 30.0):
        self.acquire(lock_name, timeout)
        try:
            yield
        finally:
            self.release(lock_name)

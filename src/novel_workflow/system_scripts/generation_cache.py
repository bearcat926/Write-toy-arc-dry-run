"""GenerationCache — generation-scoped cache for derived artifacts.

PatchB B-P0-02: Cache key includes generation_id.
Rollback invalidates all entries for old generation.
"""
from typing import Any


class GenerationCache:
    """In-memory cache with generation-scoped invalidation."""

    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._generation_keys: dict[str, set[str]] = {}  # generation_id → set of keys

    def get(self, key: str) -> Any | None:
        """Get cached value by key."""
        return self._cache.get(key)

    def put(self, key: str, value: Any, generation_id: str = "") -> None:
        """Store value with generation tracking."""
        self._cache[key] = value
        if generation_id:
            if generation_id not in self._generation_keys:
                self._generation_keys[generation_id] = set()
            self._generation_keys[generation_id].add(key)

    def invalidate_generation(self, generation_id: str) -> int:
        """Invalidate all cache entries for a generation. Returns count removed."""
        keys = self._generation_keys.get(generation_id, set())
        count = 0
        for key in keys:
            if key in self._cache:
                del self._cache[key]
                count += 1
        if generation_id in self._generation_keys:
            del self._generation_keys[generation_id]
        return count

    def clear(self) -> None:
        """Clear entire cache."""
        self._cache.clear()
        self._generation_keys.clear()

    def size(self) -> int:
        """Return cache size."""
        return len(self._cache)

"""StableGenerationPointer — sole entry point for reading stable derived artifacts.

PatchB B-P0-01: Stable Pointer Consistency Protocol.
Active readers must go through StableGenerationPointer, not directly to artifact paths.
"""
from pathlib import Path

from .manifest_manager import ManifestManager
from ..schemas.manifest import DerivedArtifactEntry


class StableSnapshot:
    """Immutable snapshot of stable artifact paths for a single read cycle.

    Active readers consume this snapshot instead of scanning workspace directly.
    """

    def __init__(self, entries: dict[str, DerivedArtifactEntry], root: Path):
        self._entries = entries
        self._root = root

    def get_path(self, artifact_type: str) -> Path | None:
        """Get the resolved filesystem path for a stable artifact type."""
        entry = self._entries.get(artifact_type)
        if entry is None:
            return None
        return self._root / entry.artifact_path

    def get_entry(self, artifact_type: str) -> DerivedArtifactEntry | None:
        """Get the manifest entry for a stable artifact type."""
        return self._entries.get(artifact_type)

    def has(self, artifact_type: str) -> bool:
        """Check if artifact type is in this snapshot."""
        return artifact_type in self._entries

    @property
    def artifact_types(self) -> list[str]:
        return list(self._entries.keys())


class StableGenerationPointer:
    """Provides stable-pointer access to derived artifacts.

    Only returns artifacts that are non-stale in the manifest.
    """

    def __init__(self, root: Path):
        self._root = root
        self._manifest = ManifestManager(root)

    def resolve_snapshot(self, required_types: list[str] | None = None) -> StableSnapshot:
        """Build a stable snapshot of all non-stale manifest entries.

        Args:
            required_types: If given, verify these types have at least one non-stale entry.
                Raises RuntimeError if any required type has entries but all are stale.

        Returns:
            StableSnapshot with resolved paths for all non-stale entries.

        Raises:
            RuntimeError: If a required type exists in manifest but all entries are stale.
        """
        manifest = self._manifest.load()
        stable: dict[str, DerivedArtifactEntry] = {}

        for entry in manifest.entries:
            if not entry.stale:
                # If multiple non-stale entries of same type, keep latest
                stable[entry.artifact_type] = entry

        if required_types:
            all_types = {e.artifact_type for e in manifest.entries}
            for rtype in required_types:
                if rtype in all_types and rtype not in stable:
                    raise RuntimeError(
                        f"Active mode blocked: artifact type '{rtype}' "
                        f"exists in manifest but all entries are stale"
                    )

        return StableSnapshot(stable, self._root)

    def get_stable(self, artifact_type: str) -> DerivedArtifactEntry | None:
        """Get the current stable entry for an artifact type.

        Returns None if no stable entry exists (stale or missing).
        """
        manifest = self._manifest.load()
        for entry in manifest.entries:
            if entry.artifact_type == artifact_type and not entry.stale:
                return entry
        return None

    def promote_to_stable(self, artifact_path: str) -> bool:
        """Promote an artifact to stable (mark non-stale).

        Returns True if promotion succeeded.
        """
        manifest = self._manifest.load()
        for entry in manifest.entries:
            if entry.artifact_path == artifact_path:
                entry.stale = False
                entry.stale_reason = ""
                self._manifest.save()
                return True
        return False

    def rollback_to_previous(self, artifact_type: str) -> bool:
        """Mark current stable as stale (rollback).

        Returns True if rollback succeeded.
        """
        manifest = self._manifest.load()
        for entry in manifest.entries:
            if entry.artifact_type == artifact_type and not entry.stale:
                entry.stale = True
                entry.stale_reason = "rollback"
                self._manifest.save()
                return True
        return False

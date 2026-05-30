"""StableGenerationPointer — sole entry point for reading stable derived artifacts.

PatchB B-P0-01: Stable Pointer Consistency Protocol.
Active readers must go through StableGenerationPointer, not directly to artifact paths.
"""
from pathlib import Path

from .manifest_manager import ManifestManager
from ..schemas.manifest import DerivedArtifactEntry


class StableGenerationPointer:
    """Provides stable-pointer access to derived artifacts.

    Only returns artifacts that are non-stale in the manifest.
    """

    def __init__(self, root: Path):
        self._root = root
        self._manifest = ManifestManager(root)

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

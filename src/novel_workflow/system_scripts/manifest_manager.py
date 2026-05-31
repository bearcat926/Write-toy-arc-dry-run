"""ManifestManager — runtime management for Phase 2 manifest.json.

Handles loading, registering artifacts, marking stale, and atomic save.
"""
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from ..schemas.manifest import Phase2Manifest, DerivedArtifactEntry


MANIFEST_DIR = "workspace/phase2"
MANIFEST_FILE = "manifest.json"


class ManifestManager:
    """Manages workspace/phase2/manifest.json lifecycle."""

    def __init__(self, root: Path):
        self._root = root
        self._manifest_dir = root / MANIFEST_DIR
        self._manifest_path = self._manifest_dir / MANIFEST_FILE
        self._manifest: Phase2Manifest | None = None

    def load(self) -> Phase2Manifest:
        """Load existing manifest or create empty one."""
        if self._manifest is not None:
            return self._manifest

        if self._manifest_path.exists():
            try:
                data = json.loads(self._manifest_path.read_text(encoding="utf-8"))
                self._manifest = Phase2Manifest.model_validate(data)
            except (json.JSONDecodeError, Exception):
                self._manifest = self._create_empty()
        else:
            self._manifest = self._create_empty()

        return self._manifest

    def register_artifact(self, entry: DerivedArtifactEntry) -> None:
        """Add or update an artifact entry in the manifest."""
        manifest = self.load()

        # Update existing or append
        updated = False
        for i, existing in enumerate(manifest.entries):
            if existing.artifact_path == entry.artifact_path:
                manifest.entries[i] = entry
                updated = True
                break

        if not updated:
            manifest.entries.append(entry)

        self._manifest = manifest

    def mark_stale(self, artifact_path: str, reason: str) -> None:
        """Mark an artifact as stale."""
        manifest = self.load()
        for entry in manifest.entries:
            if entry.artifact_path == artifact_path:
                entry.stale = True
                entry.stale_reason = reason
                break
        self._manifest = manifest

    def save(self) -> None:
        """Atomically write manifest to disk."""
        manifest = self.load()
        self._manifest_dir.mkdir(parents=True, exist_ok=True)

        # Atomic write: temp file + rename
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self._manifest_dir), suffix=".tmp", prefix="manifest_"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(manifest.model_dump_json(indent=2))
            os.replace(tmp_path, str(self._manifest_path))
        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def register_persisted_artifact(self, entry: DerivedArtifactEntry) -> None:
        """Register an artifact that has been written to disk. Validates existence and hash."""
        abs_path = self._root / entry.artifact_path

        if not abs_path.exists():
            raise FileNotFoundError(f"Manifest ghost entry: {entry.artifact_path}")

        # Compute actual hash
        import hashlib
        h = hashlib.sha256()
        with open(abs_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        actual_hash = h.hexdigest()

        if entry.content_hash and entry.content_hash != actual_hash:
            raise ValueError(f"Hash mismatch for {entry.artifact_path}")

        if entry.required and not entry.source_artifacts:
            raise ValueError(f"Required artifact {entry.artifact_path} has no source_artifacts")

        if not entry.content_hash:
            entry.content_hash = actual_hash

        self.register_artifact(entry)

    def verify_required_artifacts(self, *, active: bool = False) -> list[str]:
        """Verify all required artifacts exist and are not stale. Returns list of failures."""
        manifest = self.load()
        failures = []
        for entry in manifest.entries:
            if not entry.required:
                continue
            abs_path = self._root / entry.artifact_path
            if not abs_path.exists():
                failures.append(f"missing required: {entry.artifact_path}")
            elif entry.stale:
                failures.append(f"stale required: {entry.artifact_path}")
            elif active and entry.content_hash:
                import hashlib
                h = hashlib.sha256()
                with open(abs_path, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        h.update(chunk)
                if h.hexdigest() != entry.content_hash:
                    failures.append(f"hash mismatch: {entry.artifact_path}")
        return failures

    def get_entry(self, artifact_path: str) -> DerivedArtifactEntry | None:
        """Get manifest entry by artifact path."""
        manifest = self.load()
        for entry in manifest.entries:
            if entry.artifact_path == artifact_path:
                return entry
        return None

    @staticmethod
    def _create_empty() -> Phase2Manifest:
        return Phase2Manifest(
            batch_generation_id="",
            base_commit_sha="",
            context_mode="legacy",
            entries=[],
        )

"""ArtifactWriter — atomic write + manifest registration for derived artifacts.

TEMP.md §9.2: write tmp → fsync → atomic rename → sha256 → register → manifest.save()
"""
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from ..schemas.manifest import DerivedArtifactEntry
from .manifest_manager import ManifestManager


@dataclass
class ArtifactWriteResult:
    """Result of writing a derived artifact."""
    success: bool
    artifact_path: str
    content_hash: str
    error: str = ""


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_sources(root: Path, source_artifacts: list[str]) -> dict[str, str]:
    """Compute SHA-256 hashes for source artifacts."""
    result = {}
    for src in source_artifacts:
        src_path = root / src
        if src_path.exists():
            result[src] = sha256_file(src_path)
        else:
            result[src] = ""
    return result


class ArtifactWriter:
    """Writes derived artifacts atomically and registers them in manifest."""

    def __init__(self, root: Path):
        self._root = root
        self._manifest = ManifestManager(root)

    def write_json_artifact(
        self,
        *,
        rel_path: str,
        artifact_type: str,
        builder_name: str,
        payload: BaseModel | dict,
        source_artifacts: list[str],
        runtime_id: str = "",
        required: bool = False,
        rebuildable: bool = True,
        allow_empty_sources: bool = False,
    ) -> ArtifactWriteResult:
        """Write a JSON artifact atomically and register in manifest.

        Args:
            rel_path: Relative path for the artifact
            artifact_type: Type identifier
            builder_name: Name of the builder
            payload: Pydantic model or dict to write
            source_artifacts: List of source artifact paths
            runtime_id: Runtime identifier
            required: Whether artifact is required in active mode
            rebuildable: Whether artifact can be rebuilt
            allow_empty_sources: Allow empty source list

        Returns:
            ArtifactWriteResult with success status and hash
        """
        if not source_artifacts and not allow_empty_sources:
            return ArtifactWriteResult(
                success=False, artifact_path=rel_path, content_hash="",
                error="source_artifacts empty",
            )

        abs_path = self._root / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize
        if isinstance(payload, BaseModel):
            content = payload.model_dump_json(indent=2)
        else:
            content = json.dumps(payload, indent=2, ensure_ascii=False)

        # Atomic write
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(abs_path.parent), suffix=".tmp", prefix="artifact_"
            )
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(fd)
            os.replace(tmp_path, str(abs_path))
        except Exception as e:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            return ArtifactWriteResult(
                success=False, artifact_path=rel_path, content_hash="",
                error=str(e),
            )

        # Compute hashes
        content_hash = sha256_file(abs_path)
        source_hashes = sha256_sources(self._root, source_artifacts)

        # Register in manifest
        entry = DerivedArtifactEntry(
            artifact_path=rel_path,
            artifact_type=artifact_type,
            source_artifacts=source_artifacts,
            source_artifact_hashes=source_hashes,
            built_at=datetime.now(timezone.utc).isoformat(),
            builder_name=builder_name,
            content_hash=content_hash,
            runtime_id=runtime_id,
            required=required,
            rebuildable=rebuildable,
        )

        try:
            self._manifest.load()
            self._manifest.register_artifact(entry)
            self._manifest.save()
        except Exception as e:
            return ArtifactWriteResult(
                success=False, artifact_path=rel_path, content_hash=content_hash,
                error=f"manifest registration failed: {e}",
            )

        return ArtifactWriteResult(
            success=True, artifact_path=rel_path, content_hash=content_hash,
        )

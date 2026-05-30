"""RebuildOrchestrator — unified rebuild entry for derived artifacts.

Rebuilds in dependency order: summary → graph → lifecycle → drift → arc_plan → beat_plan → trace.
Uses RebuildLock to prevent concurrent rebuilds.
"""
from dataclasses import dataclass, field
from pathlib import Path

from .rebuild_lock import RebuildLock
from .manifest_manager import ManifestManager
from .narrative_compressor import NarrativeCompressor
from ..schemas.manifest import DerivedArtifactEntry


@dataclass
class RebuildResult:
    """Result of a rebuild operation."""
    success: bool
    rebuilt_artifacts: list[str] = field(default_factory=list)
    failed_artifacts: list[str] = field(default_factory=list)
    reason: str = ""


# Rebuild order: each depends on the previous
REBUILD_ORDER = [
    "summary",
    "graph",
    "lifecycle",
    "drift",
    "arc_plan",
    "beat_plan",
    "trace",
]


class RebuildOrchestrator:
    """Orchestrates derived artifact rebuilds in dependency order."""

    def __init__(self, root: Path):
        self._root = root
        self._lock = RebuildLock(root)
        self._manifest = ManifestManager(root)

    def rebuild(
        self,
        arc_id: str,
        chapter_id: str | None,
        reason: str,
    ) -> RebuildResult:
        """Rebuild derived artifacts for an arc/chapter.

        Args:
            arc_id: Arc identifier
            chapter_id: Chapter identifier (None for arc-level rebuild)
            reason: Why rebuild is needed (e.g. "source_changed", "stale")

        Returns:
            RebuildResult with success status and artifact lists
        """
        # Acquire lock
        if not self._lock.acquire("RebuildOrchestrator"):
            return RebuildResult(
                success=False,
                reason="rebuild lock already held by another process",
            )

        rebuilt = []
        failed = []

        try:
            # Step 1: Rebuild summary (if chapter-level)
            if chapter_id:
                try:
                    compressor = NarrativeCompressor(self._root)
                    summary = compressor.compress(arc_id, chapter_id)
                    rebuilt.append(f"workspace/summaries/{chapter_id}_summary.json")
                    # Register in manifest
                    entry = DerivedArtifactEntry(
                        artifact_path=f"workspace/summaries/{chapter_id}_summary.json",
                        artifact_type="narrative_summary",
                        builder_name="NarrativeCompressor",
                        source_artifacts=[f"arcs/{arc_id}/drafts/{chapter_id}.md"],
                        stale=False,
                    )
                    self._manifest.register_artifact(entry)
                except Exception as e:
                    failed.append(f"summary:{chapter_id}:{e}")

            # Steps 2-7: Graph, lifecycle, drift, arc_plan, beat_plan, trace
            # These are placeholders — actual builders will be wired in Wave 3-4
            for artifact_type in REBUILD_ORDER[1:]:
                # Check if builder exists in manifest
                entries = [e for e in self._manifest.load().entries
                          if e.artifact_type == artifact_type]
                if entries:
                    # Mark existing entries as needing rebuild
                    for entry in entries:
                        self._manifest.mark_stale(
                            entry.artifact_path, f"rebuild requested: {reason}"
                        )
                    rebuilt.append(f"{artifact_type}:{len(entries)} entries marked stale")

            # Save manifest
            self._manifest.save()

            return RebuildResult(
                success=len(failed) == 0,
                rebuilt_artifacts=rebuilt,
                failed_artifacts=failed,
                reason=reason,
            )

        finally:
            self._lock.release()

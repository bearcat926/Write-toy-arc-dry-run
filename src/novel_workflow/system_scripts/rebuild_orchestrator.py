"""RebuildOrchestrator — replacement-style refactor with adapter DAG.

TEMP.md §11: Real rebuild with adapter pattern, not placeholder mark-stale.
Rebuild order: summary → graph → lifecycle → drift → arc_plan → beat_plan → trace → structured_audit → calibration → manifest_verification
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from .rebuild_lock import RebuildLock
from .manifest_manager import ManifestManager
from .narrative_compressor import NarrativeCompressor
from ..schemas.manifest import DerivedArtifactEntry
from ..schemas.runtime_modes import RuntimeModes


@dataclass
class ArtifactWriteResult:
    success: bool
    artifact_path: str
    content_hash: str = ""
    error: str = ""


@dataclass
class RebuildReport:
    success: bool
    rebuilt: list[ArtifactWriteResult] = field(default_factory=list)
    failed: list[ArtifactWriteResult] = field(default_factory=list)
    reason: str = ""


class RebuildAdapter(Protocol):
    artifact_type: str
    required_in_active: bool

    def rebuild(
        self,
        *,
        arc_id: str,
        chapter_id: str | None,
        runtime_id: str,
        modes: RuntimeModes,
    ) -> list[ArtifactWriteResult]:
        ...


class SummaryRebuildAdapter:
    artifact_type = "narrative_summary"
    required_in_active = True

    def __init__(self, root: Path):
        self._root = root

    def rebuild(self, *, arc_id: str, chapter_id: str | None, runtime_id: str, modes: RuntimeModes) -> list[ArtifactWriteResult]:
        if not chapter_id:
            return []
        try:
            compressor = NarrativeCompressor(self._root)
            summary = compressor.compress(arc_id, chapter_id)
            # Register in manifest
            manifest = ManifestManager(self._root)
            manifest.load()
            manifest.register_artifact(DerivedArtifactEntry(
                artifact_path=f"workspace/summaries/{chapter_id}_summary.json",
                artifact_type="narrative_summary",
                builder_name="NarrativeCompressor",
                source_artifacts=[f"arcs/{arc_id}/drafts/{chapter_id}.md"],
            ))
            manifest.save()
            return [ArtifactWriteResult(
                success=True,
                artifact_path=f"workspace/summaries/{chapter_id}_summary.json",
            )]
        except Exception as e:
            return [ArtifactWriteResult(
                success=False,
                artifact_path=f"workspace/summaries/{chapter_id}_summary.json",
                error=str(e),
            )]


# Placeholder adapters for future implementation
class _PlaceholderAdapter:
    required_in_active = False

    def __init__(self, artifact_type: str):
        self.artifact_type = artifact_type

    def rebuild(self, *, arc_id, chapter_id, runtime_id, modes):
        return []


REBUILD_ORDER = [
    "summary",
    "graph",
    "lifecycle",
    "drift",
    "arc_plan",
    "beat_plan",
    "trace",
    "structured_audit",
    "calibration",
    "manifest_verification",
]


class RebuildOrchestrator:
    """Orchestrates derived artifact rebuilds in dependency order."""

    def __init__(self, root: Path):
        self._root = root
        self._lock = RebuildLock(root)
        self._manifest = ManifestManager(root)
        self._adapters: dict[str, object] = {
            "summary": SummaryRebuildAdapter(root),
        }

    def rebuild(
        self,
        *,
        arc_id: str,
        chapter_id: str | None,
        reason: str,
        modes: RuntimeModes | None = None,
        runtime_id: str = "",
    ) -> RebuildReport:
        if not self._lock.acquire("RebuildOrchestrator"):
            return RebuildReport(success=False, reason="lock held")

        rebuilt = []
        failed = []

        try:
            for step in REBUILD_ORDER:
                adapter = self._adapters.get(step)
                if adapter is None:
                    continue

                try:
                    results = adapter.rebuild(
                        arc_id=arc_id,
                        chapter_id=chapter_id,
                        runtime_id=runtime_id,
                        modes=modes or RuntimeModes.__new__(RuntimeModes),
                    )
                    for r in results:
                        if r.success:
                            rebuilt.append(r)
                        else:
                            failed.append(r)
                            if getattr(adapter, 'required_in_active', False) and modes and modes.active_manifest_required:
                                return RebuildReport(
                                    success=False,
                                    rebuilt=rebuilt,
                                    failed=failed,
                                    reason=f"required adapter {step} failed",
                                )
                except Exception as e:
                    failed.append(ArtifactWriteResult(
                        success=False, artifact_path=f"{step}:error", error=str(e),
                    ))

            self._manifest.save()
            return RebuildReport(
                success=len(failed) == 0,
                rebuilt=rebuilt,
                failed=failed,
                reason=reason,
            )
        finally:
            self._lock.release()

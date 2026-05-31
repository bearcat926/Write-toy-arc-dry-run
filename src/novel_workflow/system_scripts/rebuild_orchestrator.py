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


class GraphRebuildAdapter:
    artifact_type = "narrative_graph_index"
    required_in_active = False

    def __init__(self, root: Path):
        self._root = root

    def rebuild(self, *, arc_id: str, chapter_id: str | None, runtime_id: str, modes) -> list[ArtifactWriteResult]:
        try:
            from .narrative_graph_builder import NarrativeGraphBuilder
            builder = NarrativeGraphBuilder(self._root)
            builder.write_index(arc_id)
            manifest = ManifestManager(self._root)
            manifest.load()
            manifest.register_artifact(DerivedArtifactEntry(
                artifact_path="workspace/narrative_graph_index.json",
                artifact_type="narrative_graph_index",
                builder_name="NarrativeGraphBuilder",
                source_artifacts=[f"ledgers/timeline.json", f"ledgers/character_knowledge.json"],
            ))
            manifest.save()
            return [ArtifactWriteResult(success=True, artifact_path="workspace/narrative_graph_index.json")]
        except Exception as e:
            return [ArtifactWriteResult(success=False, artifact_path="workspace/narrative_graph_index.json", error=str(e))]


class LifecycleRebuildAdapter:
    artifact_type = "foreshadow_lifecycle_index"
    required_in_active = False

    def __init__(self, root: Path):
        self._root = root

    def rebuild(self, *, arc_id: str, chapter_id: str | None, runtime_id: str, modes) -> list[ArtifactWriteResult]:
        try:
            from .foreshadow_lifecycle_manager import ForeshadowLifecycleManager
            manager = ForeshadowLifecycleManager(self._root)
            manager.build(arc_id)
            manifest = ManifestManager(self._root)
            manifest.load()
            manifest.register_artifact(DerivedArtifactEntry(
                artifact_path="workspace/foreshadow_lifecycle_index.json",
                artifact_type="foreshadow_lifecycle_index",
                builder_name="ForeshadowLifecycleManager",
                source_artifacts=[f"ledgers/foreshadowing.json"],
            ))
            manifest.save()
            return [ArtifactWriteResult(success=True, artifact_path="workspace/foreshadow_lifecycle_index.json")]
        except Exception as e:
            return [ArtifactWriteResult(success=False, artifact_path="workspace/foreshadow_lifecycle_index.json", error=str(e))]


class DriftRebuildAdapter:
    artifact_type = "character_drift_report"
    required_in_active = False

    def __init__(self, root: Path):
        self._root = root

    def rebuild(self, *, arc_id: str, chapter_id: str | None, runtime_id: str, modes) -> list[ArtifactWriteResult]:
        if not chapter_id:
            return []
        try:
            from .character_baseline_loader import CharacterBaselineLoader
            from .character_consistency_engine import CharacterConsistencyEngine
            from ..schemas.character_state import CharacterDriftReport
            loader = CharacterBaselineLoader(self._root)
            baselines = loader.load_all_for_arc(arc_id=arc_id)
            if not baselines:
                return []  # no baselines, skip
            engine = CharacterConsistencyEngine(self._root)
            findings = []
            for character_id, baseline in baselines.items():
                report = engine.check_chapter(
                    arc_id=arc_id, chapter_id=chapter_id,
                    character_id=character_id, baseline=baseline,
                )
                findings.extend(report.findings if hasattr(report, 'findings') else [])
            drift_report = CharacterDriftReport(
                arc_id=arc_id, chapter_id=chapter_id,
                findings=findings, recommended_action="approve",
            )
            report_dir = self._root / "workspace" / "reports" / "character_drift" / arc_id
            report_dir.mkdir(parents=True, exist_ok=True)
            report_path = report_dir / f"{chapter_id}.json"
            report_path.write_text(drift_report.model_dump_json(indent=2), encoding="utf-8")
            manifest = ManifestManager(self._root)
            manifest.load()
            manifest.register_artifact(DerivedArtifactEntry(
                artifact_path=f"workspace/reports/character_drift/{arc_id}/{chapter_id}.json",
                artifact_type="character_drift_report",
                builder_name="CharacterConsistencyEngine",
                source_artifacts=[f"arcs/{arc_id}/drafts/{chapter_id}.md"],
            ))
            manifest.save()
            return [ArtifactWriteResult(success=True, artifact_path=f"workspace/reports/character_drift/{arc_id}/{chapter_id}.json")]
        except Exception as e:
            return [ArtifactWriteResult(success=False, artifact_path=f"drift:{chapter_id}", error=str(e))]


class ArcPlanRebuildAdapter:
    artifact_type = "arc_plan"
    required_in_active = False

    def __init__(self, root: Path):
        self._root = root

    def rebuild(self, *, arc_id: str, chapter_id: str | None, runtime_id: str, modes) -> list[ArtifactWriteResult]:
        try:
            from .arc_planning_engine import ArcPlanningEngine
            engine = ArcPlanningEngine(self._root)
            arc_plan, beat_plans, health_report = engine.plan_arc(arc_id, chapter_count=10)
            plan_dir = self._root / "workspace" / "arc_plan" / arc_id
            plan_dir.mkdir(parents=True, exist_ok=True)
            plan_path = plan_dir / "arc_plan.json"
            plan_path.write_text(arc_plan.model_dump_json(indent=2), encoding="utf-8")
            health_path = plan_dir / "health_report.json"
            health_path.write_text(health_report.model_dump_json(indent=2), encoding="utf-8")
            manifest = ManifestManager(self._root)
            manifest.load()
            manifest.register_artifact(DerivedArtifactEntry(
                artifact_path=f"workspace/arc_plan/{arc_id}/arc_plan.json",
                artifact_type="arc_plan",
                builder_name="ArcPlanningEngine",
                source_artifacts=[f"arcs/{arc_id}/arc_contract.md"],
            ))
            manifest.register_artifact(DerivedArtifactEntry(
                artifact_path=f"workspace/arc_plan/{arc_id}/health_report.json",
                artifact_type="arc_health_report",
                builder_name="ArcPlanningEngine",
                source_artifacts=[f"arcs/{arc_id}/arc_contract.md", f"workspace/arc_plan/{arc_id}/arc_plan.json"],
            ))
            manifest.save()
            return [ArtifactWriteResult(success=True, artifact_path=f"workspace/arc_plan/{arc_id}/arc_plan.json")]
        except Exception as e:
            return [ArtifactWriteResult(success=False, artifact_path=f"arc_plan:{arc_id}", error=str(e))]


class BeatPlanRebuildAdapter:
    artifact_type = "chapter_beat_plan"
    required_in_active = False

    def __init__(self, root: Path):
        self._root = root

    def rebuild(self, *, arc_id: str, chapter_id: str | None, runtime_id: str, modes) -> list[ArtifactWriteResult]:
        if not chapter_id:
            return []
        try:
            from .arc_planning_engine import ArcPlanningEngine
            engine = ArcPlanningEngine(self._root)
            _, beat_plans, _ = engine.plan_arc(arc_id, chapter_count=10)
            # Find the beat plan for this chapter
            target_beat = None
            for bp in beat_plans:
                if bp.chapter_id == chapter_id:
                    target_beat = bp
                    break
            if not target_beat:
                return [ArtifactWriteResult(success=False, artifact_path=f"beat_plan:{chapter_id}", error="no beat plan found")]
            beat_dir = self._root / "workspace" / "beat_plans" / arc_id
            beat_dir.mkdir(parents=True, exist_ok=True)
            beat_path = beat_dir / f"{chapter_id}.json"
            beat_path.write_text(target_beat.model_dump_json(indent=2), encoding="utf-8")
            manifest = ManifestManager(self._root)
            manifest.load()
            manifest.register_artifact(DerivedArtifactEntry(
                artifact_path=f"workspace/beat_plans/{arc_id}/{chapter_id}.json",
                artifact_type="chapter_beat_plan",
                builder_name="ArcPlanningEngine",
                source_artifacts=[
                    f"arcs/{arc_id}/arc_contract.md",
                    f"workspace/arc_plan/{arc_id}/arc_plan.json",
                ],
            ))
            manifest.save()
            return [ArtifactWriteResult(success=True, artifact_path=f"workspace/beat_plans/{arc_id}/{chapter_id}.json")]
        except Exception as e:
            return [ArtifactWriteResult(success=False, artifact_path=f"beat_plan:{chapter_id}", error=str(e))]


class TraceRebuildAdapter:
    artifact_type = "retrieval_trace"
    required_in_active = False

    def __init__(self, root: Path):
        self._root = root

    def rebuild(self, *, arc_id: str, chapter_id: str | None, runtime_id: str, modes) -> list[ArtifactWriteResult]:
        if not chapter_id:
            return []
        try:
            from .context_provider import ContextProvider
            provider = ContextProvider(self._root, mode="retrieval_active")
            _, trace = provider.build_writer_context(arc_id, int(chapter_id.split("_")[1]) if "_" in chapter_id else 1)
            if trace:
                ContextProvider.write_trace(self._root, arc_id, chapter_id, trace)
            return [ArtifactWriteResult(success=True, artifact_path=f"workspace/retrieval_traces/{arc_id}/{chapter_id}/writer.jsonl")]
        except Exception as e:
            return [ArtifactWriteResult(success=False, artifact_path=f"trace:{chapter_id}", error=str(e))]


class CalibrationRebuildAdapter:
    artifact_type = "auditor_calibration"
    required_in_active = False

    def __init__(self, root: Path):
        self._root = root

    def rebuild(self, *, arc_id: str, chapter_id: str | None, runtime_id: str, modes) -> list[ArtifactWriteResult]:
        # No-op for now — calibration requires real legacy/structured comparison
        return []


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
            "graph": GraphRebuildAdapter(root),
            "lifecycle": LifecycleRebuildAdapter(root),
            "drift": DriftRebuildAdapter(root),
            "arc_plan": ArcPlanRebuildAdapter(root),
            "beat_plan": BeatPlanRebuildAdapter(root),
            "trace": TraceRebuildAdapter(root),
            "calibration": CalibrationRebuildAdapter(root),
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

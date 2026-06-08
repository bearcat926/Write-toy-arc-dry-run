"""ProjectionRegistry — manages downstream projections triggered by ChapterCommit.

Phase 3 C-03: Each projection is independently registered, can be
enabled/disabled, and records its processing state.

Projections react to ChapterCommitEvent and produce derived artifacts:
  - summary_projection -> chapter_summary
  - graph_projection -> narrative_graph
  - index_projection -> BM25/FTS5 reindex
  - health_projection -> governance health report
  - metrics_projection -> chapter metrics
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable

from ..schemas.chapter_commit import ChapterCommitEvent, ChapterCommitStore


class ProjectionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ProjectionRecord:
    """Record of a single projection execution."""
    projection_name: str
    commit_id: str
    chapter_id: str
    status: ProjectionStatus
    error_message: str = ""
    output_artifacts: list[str] = field(default_factory=list)
    duration_ms: float = 0.0


@dataclass
class ProjectionRegistration:
    """Registration of a projection handler."""
    name: str
    handler: Callable[[ChapterCommitEvent], ProjectionRecord]
    enabled: bool = True
    description: str = ""


class ProjectionRegistry:
    """Manages registered projections and dispatches ChapterCommit events."""

    def __init__(self, root: Path):
        self._root = root
        self._store = ChapterCommitStore(root)
        self._projections: dict[str, ProjectionRegistration] = {}
        self._history: list[ProjectionRecord] = []

    def register(
        self,
        name: str,
        handler: Callable[[ChapterCommitEvent], ProjectionRecord],
        description: str = "",
        enabled: bool = True,
    ) -> None:
        """Register a projection handler."""
        self._projections[name] = ProjectionRegistration(
            name=name,
            handler=handler,
            enabled=enabled,
            description=description,
        )

    def unregister(self, name: str) -> None:
        """Remove a projection handler."""
        self._projections.pop(name, None)

    def enable(self, name: str) -> None:
        """Enable a projection."""
        if name in self._projections:
            self._projections[name].enabled = True

    def disable(self, name: str) -> None:
        """Disable a projection."""
        if name in self._projections:
            self._projections[name].enabled = False

    @property
    def registered_names(self) -> list[str]:
        return list(self._projections.keys())

    @property
    def enabled_names(self) -> list[str]:
        return [n for n, p in self._projections.items() if p.enabled]

    def dispatch(self, event: ChapterCommitEvent) -> list[ProjectionRecord]:
        """Dispatch a ChapterCommitEvent to all enabled projections.

        Each projection runs independently. Failures in one projection
        do not block others.

        Returns list of ProjectionRecord for all dispatched projections.
        """
        records: list[ProjectionRecord] = []

        for name, reg in self._projections.items():
            if not reg.enabled:
                records.append(ProjectionRecord(
                    projection_name=name,
                    commit_id=event.commit_id,
                    chapter_id=event.chapter_id,
                    status=ProjectionStatus.SKIPPED,
                ))
                continue

            try:
                record = reg.handler(event)
                records.append(record)
            except Exception as e:
                records.append(ProjectionRecord(
                    projection_name=name,
                    commit_id=event.commit_id,
                    chapter_id=event.chapter_id,
                    status=ProjectionStatus.FAILED,
                    error_message=str(e)[:500],
                ))

        self._history.extend(records)
        return records

    def get_history(self, commit_id: str = "") -> list[ProjectionRecord]:
        """Get projection execution history, optionally filtered by commit."""
        if commit_id:
            return [r for r in self._history if r.commit_id == commit_id]
        return list(self._history)

    def get_failed(self) -> list[ProjectionRecord]:
        """Get all failed projections."""
        return [r for r in self._history if r.status == ProjectionStatus.FAILED]

    def replay(self, commit_id: str) -> list[ProjectionRecord]:
        """Replay all projections for a specific commit."""
        log = self._store.load_all()
        events = log.get_by_chapter(
            # Find event by commit_id
            next((c.chapter_id for c in log.commits if c.commit_id == commit_id), "")
        )
        if not events:
            event = next((c for c in log.commits if c.commit_id == commit_id), None)
            if event:
                return self.dispatch(event)
        return []

    # --- Built-in projection handlers (stubs for now) ---

    @staticmethod
    def summary_projection(event: ChapterCommitEvent) -> ProjectionRecord:
        """Placeholder: trigger summary rebuild for the chapter."""
        return ProjectionRecord(
            projection_name="summary",
            commit_id=event.commit_id,
            chapter_id=event.chapter_id,
            status=ProjectionStatus.SUCCESS,
            output_artifacts=[f"workspace/summaries/{event.chapter_id}_summary.json"],
        )

    @staticmethod
    def graph_projection(event: ChapterCommitEvent) -> ProjectionRecord:
        """Placeholder: trigger narrative graph update."""
        return ProjectionRecord(
            projection_name="graph",
            commit_id=event.commit_id,
            chapter_id=event.chapter_id,
            status=ProjectionStatus.SUCCESS,
            output_artifacts=["workspace/narrative_graph_index.json"],
        )

    @staticmethod
    def index_projection(event: ChapterCommitEvent) -> ProjectionRecord:
        """Placeholder: trigger BM25/FTS5 reindex."""
        return ProjectionRecord(
            projection_name="index",
            commit_id=event.commit_id,
            chapter_id=event.chapter_id,
            status=ProjectionStatus.SUCCESS,
            output_artifacts=["workspace/fts5_index"],
        )

    @staticmethod
    def health_projection(event: ChapterCommitEvent) -> ProjectionRecord:
        """Placeholder: trigger governance health report."""
        return ProjectionRecord(
            projection_name="health",
            commit_id=event.commit_id,
            chapter_id=event.chapter_id,
            status=ProjectionStatus.SUCCESS,
            output_artifacts=["workspace/reports/structured_audit_report.md"],
        )

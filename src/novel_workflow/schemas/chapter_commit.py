"""ChapterCommit — canonical event emitted after successful chapter apply.

This is the Phase 3 unified event that drives all downstream projections:
  summary, graph, index, governance, health, metrics.

Design principle (from Phase 3 plan C section):
  - Event emitted ONLY after successful AtomicApply
  - Projection failures do NOT pollute canon
  - Each commit is traceable via trace_id
  - Commits form an append-only log for audit/replay
"""

import json
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel, Field


class ChapterCommitEvent(BaseModel):
    """A canonical event emitted when a chapter is successfully applied.

    Schema version: 1.0
    Event version: 1.0
    """
    event_type: str = "chapter.commit"
    event_version: str = "1.0"
    commit_id: str
    chapter_id: str
    arc_id: str
    ledger_diff_hash: str = ""
    canon_hash: str = ""
    ledger_offsets: dict[str, int] = Field(default_factory=dict)
    trace_id: str = ""
    source_artifacts: list[str] = Field(default_factory=list)
    context_mode: str = "legacy"
    applied_at: str = ""

    @classmethod
    def create(
        cls,
        chapter_id: str,
        arc_id: str,
        ledger_diff_hash: str = "",
        canon_hash: str = "",
        ledger_offsets: dict[str, int] | None = None,
        trace_id: str = "",
        source_artifacts: list[str] | None = None,
        context_mode: str = "legacy",
    ) -> "ChapterCommitEvent":
        """Factory: create a new commit event with generated commit_id."""
        # Generate deterministic commit_id from inputs
        id_parts = [arc_id, chapter_id, ledger_diff_hash[:16], trace_id[:16]]
        raw = "|".join(id_parts)
        commit_hash = hashlib.sha256(raw.encode()).hexdigest()[:12]
        commit_id = f"cmt_{commit_hash}"

        return cls(
            commit_id=commit_id,
            chapter_id=chapter_id,
            arc_id=arc_id,
            ledger_diff_hash=ledger_diff_hash,
            canon_hash=canon_hash,
            ledger_offsets=ledger_offsets or {},
            trace_id=trace_id,
            source_artifacts=source_artifacts or [],
            context_mode=context_mode,
            applied_at=datetime.now(timezone.utc).isoformat(),
        )


class ChapterCommitLog(BaseModel):
    """Append-only log of ChapterCommitEvents."""
    schema_version: str = "1.0"
    commits: list[ChapterCommitEvent] = Field(default_factory=list)
    last_commit_index: int = -1

    def append(self, event: ChapterCommitEvent) -> int:
        """Append event and return its index."""
        self.commits.append(event)
        self.last_commit_index = len(self.commits) - 1
        return self.last_commit_index

    def get_by_chapter(self, chapter_id: str) -> list[ChapterCommitEvent]:
        """Get all commits for a chapter."""
        return [c for c in self.commits if c.chapter_id == chapter_id]

    def get_latest(self) -> ChapterCommitEvent | None:
        """Get the most recent commit."""
        if not self.commits:
            return None
        return self.commits[-1]

    def get_range(self, start: int, end: int | None = None) -> list[ChapterCommitEvent]:
        """Get commits by index range."""
        if end is None:
            end = len(self.commits)
        return self.commits[start:end]


class ChapterCommitStore:
    """Persistent store for the ChapterCommit append-only log.

    Location: workspace/chapter_commits.jsonl
    """
    LOG_FILE = "workspace/chapter_commits.jsonl"

    def __init__(self, root: Path):
        self._root = root
        self._log_path = root / self.LOG_FILE

    def ensure_log(self) -> None:
        """Create log file if it doesn't exist."""
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._log_path.exists():
            self._log_path.write_text("", encoding="utf-8")

    def append(self, event: ChapterCommitEvent) -> int:
        """Append one event to the JSONL log.

        Returns the storage index (line number, 0-based).
        """
        self.ensure_log()
        line = event.model_dump_json()
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

        # Count lines for index
        with open(self._log_path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f) - 1

    def load_all(self) -> ChapterCommitLog:
        """Load all commits from the JSONL log."""
        log = ChapterCommitLog()
        if not self._log_path.exists():
            return log

        with open(self._log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = ChapterCommitEvent.model_validate_json(line)
                    log.append(event)
                except Exception:
                    continue  # Skip corrupted lines

        return log

    def get_by_chapter(self, chapter_id: str) -> list[ChapterCommitEvent]:
        """Get all commits for a specific chapter."""
        log = self.load_all()
        return log.get_by_chapter(chapter_id)

    def get_latest(self) -> ChapterCommitEvent | None:
        """Get the most recent commit."""
        log = self.load_all()
        return log.get_latest()

    def get_range(self, start: int, end: int | None = None) -> list[ChapterCommitEvent]:
        """Get commit range by index."""
        log = self.load_all()
        return log.get_range(start, end)

    @property
    def count(self) -> int:
        """Total number of commits."""
        log = self.load_all()
        return len(log.commits)

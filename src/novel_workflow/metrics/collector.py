"""Metrics collection for stress testing and production monitoring."""
import json
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel, Field


class ChapterMetrics(BaseModel):
    """Metrics recorded after each chapter completion."""
    arc_id: str
    chapter_id: str
    proposal_accepted: bool
    audit_failed: bool
    pause_triggered: bool
    pause_type: str | None = None  # hard_pause, creative_review, soft_warning
    retry_count: int = 0
    runtime_seconds: float = 0.0
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ArcReport(BaseModel):
    """Aggregated metrics for an entire arc."""
    arc_id: str
    chapters_total: int
    proposal_accept_rate: float
    audit_fail_rate: float
    pause_rate: float
    total_retries: int
    total_runtime_seconds: float
    aws_entry_count: int  # arc_working_state entries at end
    aws_file_size_bytes: int
    chapter_details: list[ChapterMetrics]


class MetricsCollector:
    """Collects per-chapter metrics and generates arc-level reports."""

    def __init__(self, project_root: Path):
        self._root = project_root
        self._metrics_dir = project_root / "workspace"
        self._metrics_dir.mkdir(parents=True, exist_ok=True)

    def record_chapter(self, metrics: ChapterMetrics):
        """Append a chapter metrics entry to the JSONL file."""
        path = self._metrics_dir / "metrics.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(metrics.model_dump(), ensure_ascii=False) + "\n")

    def load_chapter_metrics(self, arc_id: str) -> list[ChapterMetrics]:
        """Load all chapter metrics for an arc from JSONL."""
        path = self._metrics_dir / "metrics.jsonl"
        if not path.exists():
            return []
        entries = []
        for line in path.read_text(encoding="utf-8").strip().split("\n"):
            if not line:
                continue
            data = json.loads(line)
            if data.get("arc_id") == arc_id:
                entries.append(ChapterMetrics.model_validate(data))
        return entries

    def generate_report(self, arc_id: str) -> ArcReport:
        """Generate an arc-level report from collected metrics."""
        chapters = self.load_chapter_metrics(arc_id)
        if not chapters:
            raise ValueError(f"No metrics found for arc {arc_id}")

        total = len(chapters)
        accepted = sum(1 for c in chapters if c.proposal_accepted)
        audit_fails = sum(1 for c in chapters if c.audit_failed)
        pauses = sum(1 for c in chapters if c.pause_triggered)
        retries = sum(c.retry_count for c in chapters)
        runtime = sum(c.runtime_seconds for c in chapters)

        # Check arc_working_state size
        aws_path = self._root / "arcs" / arc_id / "arc_working_state.json"
        aws_size = aws_path.stat().st_size if aws_path.exists() else 0
        aws_data = json.loads(aws_path.read_text(encoding="utf-8")) if aws_path.exists() else {}
        aws_entries = len(aws_data.get("entries", []))

        return ArcReport(
            arc_id=arc_id,
            chapters_total=total,
            proposal_accept_rate=accepted / total if total else 0,
            audit_fail_rate=audit_fails / total if total else 0,
            pause_rate=pauses / total if total else 0,
            total_retries=retries,
            total_runtime_seconds=runtime,
            aws_entry_count=aws_entries,
            aws_file_size_bytes=aws_size,
            chapter_details=chapters,
        )

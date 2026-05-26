"""Tests for metrics collection."""
import json
from pathlib import Path
from novel_workflow.metrics.collector import MetricsCollector, ChapterMetrics


def test_record_and_load(tmp_path: Path):
    collector = MetricsCollector(tmp_path)
    collector.record_chapter(ChapterMetrics(
        arc_id="arc_001", chapter_id="ch_001",
        proposal_accepted=True, audit_failed=False,
        pause_triggered=False, runtime_seconds=1.5,
    ))
    collector.record_chapter(ChapterMetrics(
        arc_id="arc_001", chapter_id="ch_002",
        proposal_accepted=False, audit_failed=True,
        pause_triggered=True, pause_type="creative_review",
        retry_count=2, runtime_seconds=3.0,
    ))

    chapters = collector.load_chapter_metrics("arc_001")
    assert len(chapters) == 2
    assert chapters[0].proposal_accepted is True
    assert chapters[1].pause_type == "creative_review"


def test_generate_report(tmp_path: Path):
    collector = MetricsCollector(tmp_path)
    for i in range(5):
        collector.record_chapter(ChapterMetrics(
            arc_id="arc_001", chapter_id=f"ch_{i+1:03d}",
            proposal_accepted=i != 2,  # ch_003 rejected
            audit_failed=i == 2,
            pause_triggered=i == 2, pause_type="creative_review",
            runtime_seconds=2.0,
        ))
    # Create minimal arc_working_state
    aws_dir = tmp_path / "arcs" / "arc_001"
    aws_dir.mkdir(parents=True, exist_ok=True)
    (aws_dir / "arc_working_state.json").write_text(
        json.dumps({"schema_version": "1.0", "entries": [{"state_id": "aws_001"}]})
    )

    report = collector.generate_report("arc_001")
    assert report.chapters_total == 5
    assert report.proposal_accept_rate == 0.8  # 4/5
    assert report.audit_fail_rate == 0.2  # 1/5
    assert report.pause_rate == 0.2
    assert report.total_retries == 0
    assert report.aws_entry_count == 1

"""Drift streak escalation and Structured Auditor Phase A tests."""
import json
import pytest
from pathlib import Path
from novel_workflow.system_scripts.drift_streak_tracker import DriftStreakTracker
from novel_workflow.system_scripts.structured_auditor import StructuredAuditor, StructuredAuditReport


def test_single_drift_is_soft_warning():
    tracker = DriftStreakTracker()
    severity = tracker.record("hero|ooc|behavior|canon:hero:001", "hero", "ooc_behavior", "ch_001")
    assert severity == "soft_warning"


def test_two_consecutive_drifts_is_creative_review():
    tracker = DriftStreakTracker()
    tracker.record("hero|ooc|behavior|canon:hero:001", "hero", "ooc_behavior", "ch_001")
    severity = tracker.record("hero|ooc|behavior|canon:hero:001", "hero", "ooc_behavior", "ch_002")
    assert severity == "creative_review"


def test_three_consecutive_drifts_is_hard_pause():
    tracker = DriftStreakTracker()
    tracker.record("hero|ooc|behavior|canon:hero:001", "hero", "ooc_behavior", "ch_001")
    tracker.record("hero|ooc|behavior|canon:hero:001", "hero", "ooc_behavior", "ch_002")
    severity = tracker.record("hero|ooc|behavior|canon:hero:001", "hero", "ooc_behavior", "ch_003")
    assert severity == "hard_pause"


def test_streak_resets_on_non_consecutive():
    """Streak resets when chapters are non-consecutive."""
    tracker = DriftStreakTracker()
    tracker.record("hero|ooc|behavior|canon:hero:001", "hero", "ooc_behavior", "ch_001")
    assert tracker.get_streak("hero|ooc|behavior|canon:hero:001") == 1
    # ch_003 is non-consecutive with ch_001 (gap: ch_002)
    severity = tracker.record("hero|ooc|behavior|canon:hero:001", "hero", "ooc_behavior", "ch_003")
    assert severity == "soft_warning"  # Streak reset, starts fresh
    assert tracker.get_streak("hero|ooc|behavior|canon:hero:001") == 1


def test_different_drift_types_not_linked():
    tracker = DriftStreakTracker()
    tracker.record("hero|ooc|behavior|canon:hero:001", "hero", "ooc_behavior", "ch_001")
    severity = tracker.record("hero|voice|drift|canon:hero:002", "hero", "voice_drift", "ch_002")
    assert severity == "soft_warning"  # Different type, fresh streak


def test_manual_reset():
    tracker = DriftStreakTracker()
    tracker.record("hero|ooc|behavior|canon:hero:001", "hero", "ooc_behavior", "ch_001")
    tracker.reset_streak("hero|ooc|behavior|canon:hero:001")
    assert tracker.get_streak("hero|ooc|behavior|canon:hero:001") == 0


def test_structured_auditor_shadow_mode(tmp_path: Path):
    auditor = StructuredAuditor(tmp_path)
    report = auditor.audit_chapter("arc_001", "ch_001", "# Draft content")
    assert report.recommended_action == "approve"
    assert report.phase == "shadow"
    assert report.derived is True
    assert report.chapter_id == "ch_001"


def test_structured_auditor_writes_report(tmp_path: Path):
    auditor = StructuredAuditor(tmp_path)
    auditor.audit_chapter("arc_001", "ch_001")
    report_path = tmp_path / "workspace" / "reports" / "structured_audit_ch_001.json"
    assert report_path.exists()
    data = json.loads(report_path.read_text())
    assert data["phase"] == "shadow"

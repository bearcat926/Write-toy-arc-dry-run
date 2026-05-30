"""Auditor comparator tests — Phase B dual-run comparison."""
import pytest
from novel_workflow.system_scripts.auditor_comparator import AuditorComparator, ComparisonResult


def test_identical_findings_full_agreement():
    comparator = AuditorComparator()
    legacy = [{"type": "ooc_behavior", "description": "Character acted out of character", "severity": "soft_warning"}]
    structured = [{"drift_type": "ooc_behavior", "evidence": "Character acted out of character", "severity": "soft_warning"}]
    result = comparator.compare(legacy, structured)
    assert result.agreement_count == 1
    assert result.agreement_rate == 1.0
    assert len(result.missed_findings) == 0
    assert len(result.extra_findings) == 0


def test_structured_finds_more():
    comparator = AuditorComparator()
    legacy = [{"type": "ooc_behavior", "description": "OOC detected", "severity": "soft_warning"}]
    structured = [
        {"drift_type": "ooc_behavior", "evidence": "OOC detected", "severity": "soft_warning"},
        {"drift_type": "voice_drift", "evidence": "Voice changed", "severity": "soft_warning"},
    ]
    result = comparator.compare(legacy, structured)
    assert result.agreement_count == 1
    assert len(result.missed_findings) == 1
    assert result.missed_findings[0]["reason"] == "structured_has_legacy_misses"


def test_legacy_finds_more():
    comparator = AuditorComparator()
    legacy = [
        {"type": "ooc_behavior", "description": "OOC detected", "severity": "soft_warning"},
        {"type": "timeline_conflict", "description": "Timeline issue", "severity": "creative_review"},
    ]
    structured = [{"drift_type": "ooc_behavior", "evidence": "OOC detected", "severity": "soft_warning"}]
    result = comparator.compare(legacy, structured)
    assert len(result.extra_findings) == 1
    assert result.extra_findings[0]["reason"] == "legacy_has_structured_misses"


def test_severity_mismatch():
    comparator = AuditorComparator()
    legacy = [{"type": "ooc_behavior", "description": "Same issue", "severity": "soft_warning"}]
    structured = [{"drift_type": "ooc_behavior", "evidence": "Same issue", "severity": "creative_review"}]
    result = comparator.compare(legacy, structured)
    assert result.agreement_count == 1
    assert len(result.severity_diffs) == 1
    assert result.severity_diffs[0]["structured_severity"] == "creative_review"


def test_empty_inputs():
    comparator = AuditorComparator()
    result = comparator.compare([], [])
    assert result.agreement_rate == 1.0
    assert result.total_findings == 0

from novel_workflow.pause.pause_detector import EmergencyPauseDetector
from novel_workflow.config import PauseType


def test_path_traversal_is_hard_pause():
    det = EmergencyPauseDetector()
    report = det.detect_path_violation("PATH_TRAVERSAL_REJECTED", "../../../etc/passwd")
    assert report.pause_type == PauseType.HARD_PAUSE


def test_pov_violation_is_creative_review():
    det = EmergencyPauseDetector()
    report = det.detect_pov_violation("char_a", "secret_x")
    assert report.pause_type == PauseType.CREATIVE_REVIEW


def test_weak_hook_is_soft_warning():
    det = EmergencyPauseDetector()
    report = det.detect_quality_issue("weak_hook", "ch_001")
    assert report.pause_type == PauseType.SOFT_WARNING


def test_hard_pause_has_options():
    det = EmergencyPauseDetector()
    report = det.detect_path_violation("PATH_TRAVERSAL_REJECTED", "../../../etc/passwd")
    assert len(report.author_options) > 0
    assert any("Fix" in o for o in report.author_options)
    assert any("Archive" in o for o in report.author_options)


def test_creative_review_allows_continue():
    det = EmergencyPauseDetector()
    report = det.detect_pov_violation("char_a", "secret_x")
    assert any("Mark as intentional" in o for o in report.author_options)

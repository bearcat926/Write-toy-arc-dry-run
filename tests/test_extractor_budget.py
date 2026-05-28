"""P1.19-P1.20: Extractor character budget tests."""
from novel_workflow.crewai.flow import _apply_budget, DRAFT_BUDGET, REVIEW_BUDGET, TOTAL_CONTROLLABLE_BUDGET


def test_draft_budget_truncates_long_content():
    """Draft content exceeding 2000 chars must be truncated."""
    long_text = "x" * 3000
    result = _apply_budget(long_text, DRAFT_BUDGET)
    assert len(result) == DRAFT_BUDGET + len("\n...(truncated)")
    assert result.endswith("\n...(truncated)")


def test_draft_budget_preserves_short_content():
    """Draft content under 2000 chars must not be truncated."""
    short_text = "x" * 500
    result = _apply_budget(short_text, DRAFT_BUDGET)
    assert result == short_text
    assert "\n...(truncated)" not in result


def test_review_budget_truncates_long_content():
    """Review content exceeding 1000 chars must be truncated."""
    long_text = "y" * 2000
    result = _apply_budget(long_text, REVIEW_BUDGET)
    assert len(result) == REVIEW_BUDGET + len("\n...(truncated)")
    assert result.endswith("\n...(truncated)")


def test_review_budget_preserves_short_content():
    """Review content under 1000 chars must not be truncated."""
    short_text = "y" * 500
    result = _apply_budget(short_text, REVIEW_BUDGET)
    assert result == short_text


def test_controllable_content_within_budget():
    """P1.20: User-controllable content (draft + review + context) must stay under 10000 chars.

    Simulates the extractor prompt construction and checks that the draft + review
    portions (the user-controllable parts) are within budget.
    """
    # Worst case: both at max budget
    draft_at_budget = _apply_budget("x" * 5000, DRAFT_BUDGET)
    review_at_budget = _apply_budget("y" * 3000, REVIEW_BUDGET)
    controllable_len = len(draft_at_budget) + len(review_at_budget)
    assert controllable_len <= TOTAL_CONTROLLABLE_BUDGET, (
        f"Controllable content {controllable_len} exceeds budget {TOTAL_CONTROLLABLE_BUDGET}"
    )


def test_budget_constants():
    """Verify budget constants match design spec."""
    assert DRAFT_BUDGET == 2000
    assert REVIEW_BUDGET == 1000
    assert TOTAL_CONTROLLABLE_BUDGET == 10000

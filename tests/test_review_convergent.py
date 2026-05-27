from novel_workflow.schemas.review import ReviewReport
from novel_workflow.system_scripts.review_convergent import ReviewConvergent


def test_converge_single_review():
    conv = ReviewConvergent()
    reviews = [ReviewReport(
        reviewer_role="continuity_auditor",
        high_priority_revisions=["Fix timeline gap"],
    )]
    brief = conv.converge("ch_001", reviews)
    assert brief.chapter_id == "ch_001"
    assert len(brief.items) == 1
    assert brief.source_reviews == ["continuity_auditor"]


def test_converge_multiple_reviews_dedup():
    conv = ReviewConvergent()
    reviews = [
        ReviewReport(reviewer_role="continuity_auditor", high_priority_revisions=["Fix timeline", "Add transition"]),
        ReviewReport(reviewer_role="plot_doctor", high_priority_revisions=["Fix timeline", "Improve pacing"]),
    ]
    brief = conv.converge("ch_001", reviews)
    assert len(brief.items) == 3  # Fix timeline, Add transition, Improve pacing
    assert brief.source_reviews == ["continuity_auditor", "plot_doctor"]


def test_converge_cap_at_5():
    conv = ReviewConvergent()
    reviews = [ReviewReport(
        reviewer_role="line_editor",
        high_priority_revisions=[f"Fix issue {i}" for i in range(10)],
    )]
    brief = conv.converge("ch_001", reviews)
    assert len(brief.items) == 5


def test_parse_reviewer_output():
    """Raw reviewer output can be parsed into ReviewReport."""
    conv = ReviewConvergent()
    raw = "blocking_issues: Timeline gap between ch1 and ch2\nrecommended_action: revise"
    report = conv.parse_raw_review("continuity_auditor", raw)
    assert report.reviewer_role == "continuity_auditor"
    assert report.recommended_action == "revise"

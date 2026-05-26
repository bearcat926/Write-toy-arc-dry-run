from novel_workflow.schemas.review import ReviewReport, RevisionBrief


def test_review_report_defaults():
    r = ReviewReport(reviewer_role="continuity_auditor")
    assert r.schema_version == "1.0"
    assert r.recommended_action == "approve"
    assert r.blocking_issues == []


def test_review_report_with_issues():
    r = ReviewReport(
        reviewer_role="plot_doctor",
        blocking_issues=["Timeline gap between ch1 and ch2"],
        high_priority_revisions=["Add transition scene"],
        recommended_action="revise",
    )
    assert len(r.blocking_issues) == 1
    assert r.recommended_action == "revise"


def test_revision_brief():
    b = RevisionBrief(chapter_id="ch_001", items=["Fix timeline", "Add dialogue"])
    assert len(b.items) == 2

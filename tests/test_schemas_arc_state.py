from novel_workflow.schemas.arc_state import ArcWorkingStateEntry


def test_arc_state_entry_default():
    e = ArcWorkingStateEntry(
        state_id="aws_001",
        source_chapter="ch_001",
        key="character_a_location",
        value="tavern",
    )
    assert e.status == "working_accepted"
    assert e.depends_on == []


def test_arc_state_entry_with_deps():
    e = ArcWorkingStateEntry(
        state_id="aws_002",
        source_chapter="ch_002",
        key="character_a_knows_b",
        value=True,
        depends_on=["aws_001"],
    )
    assert e.depends_on == ["aws_001"]

from novel_workflow.schemas.chapter_effect import ChapterEffectReport
from novel_workflow.system_scripts.chapter_effect_checker import ChapterEffectChecker


def test_effect_report_valid():
    report = ChapterEffectReport(
        chapter_id="ch_001",
        scene_goal="Introduce protagonist",
        state_changes=["Protagonist arrives at tavern"],
        character_choices=["Protagonist decides to stay"],
        conflict_or_pressure_change=["Mysterious stranger enters"],
        new_reader_questions=["Who is the stranger?"],
    )
    checker = ChapterEffectChecker()
    passed, failures = checker.check(report)
    assert passed is True
    assert failures == []


def test_effect_report_missing_scene_goal():
    report = ChapterEffectReport(
        chapter_id="ch_001",
        scene_goal="",
        state_changes=["Something happened"],
        character_choices=["Choice made"],
        conflict_or_pressure_change=["Conflict"],
        new_reader_questions=["Question?"],
    )
    checker = ChapterEffectChecker()
    passed, failures = checker.check(report)
    assert passed is False
    assert len(failures) == 1
    assert "scene goal" in failures[0].lower()


def test_effect_report_multiple_failures():
    report = ChapterEffectReport(chapter_id="ch_001")
    checker = ChapterEffectChecker()
    passed, failures = checker.check(report)
    assert passed is False
    assert len(failures) == 5


def test_effect_report_populated_from_extractor_output():
    """ChapterEffectReport can be populated from structured extractor output."""
    from novel_workflow.schemas.chapter_effect import ChapterEffectReport
    report = ChapterEffectReport(
        chapter_id="ch_001",
        scene_goal="Introduce Kael at the forge",
        state_changes=["Kael discovers he can hear enchanted steel"],
        character_choices=["Kael decides to hide the discovery"],
        conflict_or_pressure_change=["Unknown magic awakens"],
        new_reader_questions=["What is the whispering steel?"],
    )
    checker = ChapterEffectChecker()
    passed, failures = checker.check(report)
    assert passed is True
    assert failures == []

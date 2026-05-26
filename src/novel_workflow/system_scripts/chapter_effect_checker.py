from ..schemas.chapter_effect import ChapterEffectReport


class ChapterEffectChecker:
    MINIMUM_RULES = [
        ("scene_goal", "Must have a clear scene goal"),
        ("state_changes", "Must have at least one state change"),
        ("character_choices", "Must have at least one character choice"),
        ("conflict_or_pressure_change", "Must have at least one conflict/pressure/info change"),
        ("new_reader_questions", "Must have at least one reader hook"),
    ]

    def check(self, report: ChapterEffectReport) -> tuple[bool, list[str]]:
        failures = []
        for field, message in self.MINIMUM_RULES:
            value = getattr(report, field, None)
            if not value:
                failures.append(message)
        return (len(failures) == 0, failures)

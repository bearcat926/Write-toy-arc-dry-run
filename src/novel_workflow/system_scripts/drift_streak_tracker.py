"""DriftStreakTracker — tracks consecutive drift findings for escalation.

Rules:
- streak=1 → soft_warning
- streak=2 → creative_review
- streak>=3 → hard_pause
- Non-consecutive chapters → streak resets
"""
from dataclasses import dataclass, field


@dataclass
class StreakRecord:
    """Record for a single drift type streak."""
    same_drift_key: str
    character_id: str
    drift_type: str
    streak_count: int = 0
    chapters: list[str] = field(default_factory=list)
    current_severity: str = "none"


class DriftStreakTracker:
    """Tracks consecutive drift findings and escalates severity."""

    def __init__(self):
        self._streaks: dict[str, StreakRecord] = {}

    def record(self, same_drift_key: str, character_id: str, drift_type: str, chapter_id: str) -> str:
        """Record a drift finding and return the escalated severity.

        If the finding is non-consecutive (gap in chapter IDs), resets the streak first.
        """
        if same_drift_key not in self._streaks:
            self._streaks[same_drift_key] = StreakRecord(
                same_drift_key=same_drift_key,
                character_id=character_id,
                drift_type=drift_type,
            )

        record = self._streaks[same_drift_key]

        # Check if this is a consecutive chapter
        if record.chapters:
            last_ch = record.chapters[-1]
            last_num = int(last_ch.split("_")[1]) if "_" in last_ch else 0
            curr_num = int(chapter_id.split("_")[1]) if "_" in chapter_id else 0
            if curr_num != last_num + 1:
                # Non-consecutive — reset streak
                record.streak_count = 0
                record.chapters = []
                record.current_severity = "none"

        record.streak_count += 1
        if chapter_id not in record.chapters:
            record.chapters.append(chapter_id)

        # Escalate severity
        if record.streak_count >= 3:
            record.current_severity = "hard_pause"
        elif record.streak_count >= 2:
            record.current_severity = "creative_review"
        else:
            record.current_severity = "soft_warning"

        return record.current_severity

    def get_streak(self, same_drift_key: str) -> int:
        """Get current streak count for a drift key."""
        if same_drift_key not in self._streaks:
            return 0
        return self._streaks[same_drift_key].streak_count

    def reset_streak(self, same_drift_key: str) -> None:
        """Manually reset a streak."""
        if same_drift_key in self._streaks:
            self._streaks[same_drift_key].streak_count = 0
            self._streaks[same_drift_key].chapters = []
            self._streaks[same_drift_key].current_severity = "none"

    def get_all_streaks(self) -> dict[str, StreakRecord]:
        """Get all active streaks."""
        return dict(self._streaks)

"""CharacterConsistencyEngine tests."""
import pytest
from pathlib import Path
from novel_workflow.system_scripts.character_consistency_engine import CharacterConsistencyEngine
from novel_workflow.schemas.character_state import CharacterBaseline


def _seed_project(root: Path, draft_content: str = "# Chapter 1\n\nHero walks in."):
    (root / "arcs" / "arc_001" / "drafts").mkdir(parents=True, exist_ok=True)
    (root / "arcs" / "arc_001" / "drafts" / "ch_001.md").write_text(draft_content, encoding="utf-8")


def test_no_findings_for_clean_draft(tmp_path: Path):
    _seed_project(tmp_path)
    engine = CharacterConsistencyEngine(tmp_path)
    baseline = CharacterBaseline(character_id="hero", stable_traits=["brave"])
    report = engine.check_chapter("arc_001", "ch_001", "hero", baseline)
    assert report.derived is True
    assert len(report.findings) == 0
    assert report.recommended_action == "approve"


def test_taboo_violation_detected(tmp_path: Path):
    _seed_project(tmp_path, "# Chapter 1\n\nThe hero committed betrayal.")
    engine = CharacterConsistencyEngine(tmp_path)
    baseline = CharacterBaseline(
        character_id="hero",
        taboos=["betrayal"],
    )
    report = engine.check_chapter("arc_001", "ch_001", "hero", baseline)
    assert len(report.findings) >= 1
    assert any(f.drift_type == "value_violation" for f in report.findings)
    assert report.recommended_action == "creative_review"


def test_voice_drift_detected(tmp_path: Path):
    _seed_project(tmp_path, "# Chapter 1\n\nPlain text with no character voice.")
    engine = CharacterConsistencyEngine(tmp_path)
    baseline = CharacterBaseline(
        character_id="hero",
        voice_markers=["by my honor", "I swear", "indeed"],
    )
    report = engine.check_chapter("arc_001", "ch_001", "hero", baseline)
    voice_findings = [f for f in report.findings if f.drift_type == "voice_drift"]
    assert len(voice_findings) == 1
    assert voice_findings[0].severity == "soft_warning"


def test_voice_markers_present_no_drift(tmp_path: Path):
    _seed_project(tmp_path, "# Chapter 1\n\nBy my honor, I swear this is indeed true.")
    engine = CharacterConsistencyEngine(tmp_path)
    baseline = CharacterBaseline(
        character_id="hero",
        voice_markers=["by my honor", "i swear", "indeed"],
    )
    report = engine.check_chapter("arc_001", "ch_001", "hero", baseline)
    voice_findings = [f for f in report.findings if f.drift_type == "voice_drift"]
    assert len(voice_findings) == 0


def test_missing_draft_returns_hard_pause(tmp_path: Path):
    engine = CharacterConsistencyEngine(tmp_path)
    baseline = CharacterBaseline(character_id="hero")
    report = engine.check_chapter("arc_001", "ch_999", "hero", baseline)
    assert len(report.findings) == 1
    assert report.findings[0].drift_type == "missing_draft"
    assert report.findings[0].severity == "hard_pause"
    assert report.recommended_action == "hard_pause"

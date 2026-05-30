"""ArcPlanningEngine tests."""
import pytest
from pathlib import Path
from novel_workflow.system_scripts.arc_planning_engine import ArcPlanningEngine


def _seed_contract(root: Path):
    (root / "arcs" / "arc_001").mkdir(parents=True, exist_ok=True)
    (root / "arcs" / "arc_001" / "arc_contract.md").write_text(
        "# Hero's Journey\n\n"
        "## Goal\nThe hero must defeat the dark lord.\n\n"
        "## Requirements\n"
        "- Hero must gather three artifacts\n"
        "- Hero must face inner demon\n\n"
        "## Prohibitions\n"
        "- No deus ex machina\n"
        "- Hero cannot use forbidden magic\n",
        encoding="utf-8",
    )


def test_plan_arc_generates_arc_plan(tmp_path: Path):
    _seed_contract(tmp_path)
    engine = ArcPlanningEngine(tmp_path)
    plan, beats, health = engine.plan_arc("arc_001", chapter_count=3)
    assert plan.arc_id == "arc_001"
    assert plan.derived is True
    assert len(plan.chapter_range) == 3
    assert "defeat" in plan.arc_goal.lower() or "dark lord" in plan.arc_goal.lower()


def test_plan_arc_generates_beat_plans(tmp_path: Path):
    _seed_contract(tmp_path)
    engine = ArcPlanningEngine(tmp_path)
    _, beats, _ = engine.plan_arc("arc_001", chapter_count=5)
    assert len(beats) == 5
    assert all(b.derived for b in beats)
    assert beats[0].chapter_id == "ch_001"
    assert beats[4].chapter_id == "ch_005"


def test_plan_arc_extracts_requirements(tmp_path: Path):
    _seed_contract(tmp_path)
    engine = ArcPlanningEngine(tmp_path)
    plan, _, _ = engine.plan_arc("arc_001")
    assert len(plan.hard_requirements) >= 1
    assert any("artifact" in r.lower() for r in plan.hard_requirements)


def test_plan_arc_extracts_prohibitions(tmp_path: Path):
    _seed_contract(tmp_path)
    engine = ArcPlanningEngine(tmp_path)
    plan, _, _ = engine.plan_arc("arc_001")
    assert len(plan.absolute_prohibitions) >= 1


def test_plan_arc_health_report(tmp_path: Path):
    _seed_contract(tmp_path)
    engine = ArcPlanningEngine(tmp_path)
    _, _, health = engine.plan_arc("arc_001")
    assert health.derived is True
    assert health.status == "pass"


def test_plan_arc_missing_contract_raises(tmp_path: Path):
    engine = ArcPlanningEngine(tmp_path)
    with pytest.raises(FileNotFoundError):
        engine.plan_arc("arc_999")

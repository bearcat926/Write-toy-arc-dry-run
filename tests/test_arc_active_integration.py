"""Arc active integration tests."""
import json
import pytest
from pathlib import Path
from novel_workflow.validators.arc_active_validator import ArcActiveValidator


def _seed_arc_plan(root: Path, arc_id: str = "arc_001", stale: bool = False):
    """Create minimal arc plan and beat plan."""
    plan_dir = root / "workspace" / "arc_plan"
    plan_dir.mkdir(parents=True, exist_ok=True)
    plan = {
        "schema_version": "1.0",
        "arc_id": arc_id,
        "stale": stale,
        "hard_requirements": [],
    }
    plan_path = plan_dir / f"arc_{arc_id}_plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    beat = {
        "schema_version": "1.0",
        "arc_id": arc_id,
        "chapter_id": "ch_001",
        "beats": [],
    }
    beat_path = plan_dir / f"arc_{arc_id}_ch_001_beat_plan.json"
    beat_path.write_text(json.dumps(beat), encoding="utf-8")


def test_arc_plan_valid(tmp_path: Path):
    _seed_arc_plan(tmp_path)
    validator = ArcActiveValidator(tmp_path)
    result = validator.validate_arc_plan("arc_001")
    assert result.is_valid is True


def test_arc_plan_missing(tmp_path: Path):
    validator = ArcActiveValidator(tmp_path)
    result = validator.validate_arc_plan("arc_999")
    assert result.is_valid is False
    assert "ARC_PLAN_MISSING" in result.error_code


def test_arc_plan_stale(tmp_path: Path):
    _seed_arc_plan(tmp_path, stale=True)
    validator = ArcActiveValidator(tmp_path)
    result = validator.validate_arc_plan("arc_001")
    assert result.is_valid is False
    assert "ARC_PLAN_STALE" in result.error_code


def test_beat_plan_valid(tmp_path: Path):
    _seed_arc_plan(tmp_path)
    validator = ArcActiveValidator(tmp_path)
    result = validator.validate_beat_plan("arc_001", "ch_001")
    assert result.is_valid is True


def test_beat_plan_missing(tmp_path: Path):
    _seed_arc_plan(tmp_path)
    validator = ArcActiveValidator(tmp_path)
    result = validator.validate_beat_plan("arc_001", "ch_999")
    assert result.is_valid is False
    assert "BEAT_PLAN_MISSING" in result.error_code


def test_validate_for_active_pass(tmp_path: Path):
    _seed_arc_plan(tmp_path)
    validator = ArcActiveValidator(tmp_path)
    result = validator.validate_for_active("arc_001", "ch_001")
    assert result.is_valid is True


def test_validate_for_active_missing_plan(tmp_path: Path):
    validator = ArcActiveValidator(tmp_path)
    result = validator.validate_for_active("arc_001", "ch_001")
    assert result.is_valid is False

"""Phase 2 failure_isolation configuration tests."""
import pytest
from pathlib import Path
from novel_workflow.system_scripts.context_provider import ContextProvider
from novel_workflow.config import FAILURE_ISOLATION_DEFAULTS


def test_legacy_default_is_best_effort(tmp_path: Path):
    provider = ContextProvider(tmp_path, mode="legacy")
    assert provider.get_failure_isolation() == "best_effort"


def test_shadow_default_is_chapter(tmp_path: Path):
    provider = ContextProvider(tmp_path, mode="retrieval_shadow")
    assert provider.get_failure_isolation() == "chapter"


def test_active_default_is_strict(tmp_path: Path):
    provider = ContextProvider(tmp_path, mode="retrieval_active")
    assert provider.get_failure_isolation() == "strict"
    provider2 = ContextProvider(tmp_path, mode="arc_active")
    assert provider2.get_failure_isolation() == "strict"


def test_env_override(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("NOVEL_WORKFLOW_FAILURE_ISOLATION", "strict")
    provider = ContextProvider(tmp_path, mode="legacy")
    assert provider.get_failure_isolation() == "strict"


def test_active_rejects_best_effort(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("NOVEL_WORKFLOW_FAILURE_ISOLATION", "best_effort")
    provider = ContextProvider(tmp_path, mode="retrieval_active")
    with pytest.raises(ValueError, match="cannot use failure_isolation"):
        provider.get_failure_isolation()


def test_invalid_env_value(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("NOVEL_WORKFLOW_FAILURE_ISOLATION", "invalid_mode")
    provider = ContextProvider(tmp_path, mode="legacy")
    with pytest.raises(ValueError, match="Invalid"):
        provider.get_failure_isolation()


def test_failure_isolation_defaults_cover_all_modes():
    assert "legacy" in FAILURE_ISOLATION_DEFAULTS
    assert "retrieval_shadow" in FAILURE_ISOLATION_DEFAULTS
    assert "retrieval_active" in FAILURE_ISOLATION_DEFAULTS
    assert "arc_active" in FAILURE_ISOLATION_DEFAULTS

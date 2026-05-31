"""Runtime mode resolver tests — TEMP.md §4."""
import os
import pytest
from novel_workflow.schemas.runtime_modes import (
    RuntimeContextMode, ArcRuntimeMode, AuditorRuntimeMode, RuntimeModes,
)
from novel_workflow.system_scripts.runtime_mode_resolver import RuntimeModeResolver


def test_default_modes():
    resolver = RuntimeModeResolver()
    modes = resolver.resolve()
    assert modes.context_mode == RuntimeContextMode.LEGACY
    assert modes.arc_mode == ArcRuntimeMode.OFF
    assert modes.auditor_mode == AuditorRuntimeMode.OFF


def test_context_mode_override(monkeypatch):
    monkeypatch.setenv("NOVEL_WORKFLOW_CONTEXT_MODE", "retrieval_active")
    modes = RuntimeModeResolver().resolve()
    assert modes.context_mode == RuntimeContextMode.RETRIEVAL_ACTIVE


def test_arc_mode_override(monkeypatch):
    monkeypatch.setenv("NOVEL_WORKFLOW_ARC_MODE", "arc_active")
    modes = RuntimeModeResolver().resolve()
    assert modes.arc_mode == ArcRuntimeMode.ACTIVE


def test_auditor_mode_override(monkeypatch):
    monkeypatch.setenv("NOVEL_WORKFLOW_AUDITOR_MODE", "auditor_dual_run")
    modes = RuntimeModeResolver().resolve()
    assert modes.auditor_mode == AuditorRuntimeMode.DUAL_RUN


def test_active_manifest_required():
    m1 = RuntimeModes(RuntimeContextMode.RETRIEVAL_ACTIVE, ArcRuntimeMode.OFF, AuditorRuntimeMode.OFF)
    assert m1.active_manifest_required is True
    m2 = RuntimeModes(RuntimeContextMode.LEGACY, ArcRuntimeMode.ACTIVE, AuditorRuntimeMode.OFF)
    assert m2.active_manifest_required is True
    m3 = RuntimeModes(RuntimeContextMode.LEGACY, ArcRuntimeMode.OFF, AuditorRuntimeMode.ENFORCE)
    assert m3.active_manifest_required is True
    m4 = RuntimeModes(RuntimeContextMode.LEGACY, ArcRuntimeMode.OFF, AuditorRuntimeMode.OFF)
    assert m4.active_manifest_required is False

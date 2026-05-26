import pytest
from pathlib import Path


def test_crewai_import():
    """Verify crewai is importable."""
    import crewai
    assert crewai is not None


def test_flow_import():
    """Verify run_novel_flow can be imported."""
    from novel_workflow.crewai.flow import run_novel_flow
    assert callable(run_novel_flow)


def test_agents_import():
    """Verify agent factory functions work."""
    from novel_workflow.crewai.agents import create_writer, create_auditor, create_extractor
    writer = create_writer()
    auditor = create_auditor()
    extractor = create_extractor()
    assert writer.role == "Novel Chapter Writer"
    assert auditor.role == "Continuity Auditor"
    assert extractor.role == "Knowledge Extractor"

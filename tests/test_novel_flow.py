import pytest
from pathlib import Path


def test_crewai_import():
    """Verify crewai is importable."""
    import crewai
    assert crewai is not None


def test_flow_import():
    """Verify NovelFlow can be imported and instantiated."""
    from novel_workflow.crewai.flow import NovelFlow, NovelFlowState
    state = NovelFlowState(
        arc_id="arc_001",
        chapters_total=3,
        project_root="/tmp/test",
    )
    flow = NovelFlow(state=state)
    assert flow.state.arc_id == "arc_001"
    assert flow.state.chapters_total == 3


def test_agents_import():
    """Verify agent factory functions work."""
    from novel_workflow.crewai.agents import create_writer, create_auditor, create_extractor
    writer = create_writer()
    auditor = create_auditor()
    extractor = create_extractor()
    assert writer.role == "Novel Chapter Writer"
    assert auditor.role == "Continuity Auditor"
    assert extractor.role == "Knowledge Extractor"

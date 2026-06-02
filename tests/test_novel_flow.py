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


def test_agents_import(monkeypatch):
    """Verify agent factory functions work (LLM config from key.txt)."""
    # Config auto-loads from key.txt; set temp env vars from config
    from novel_workflow.crewai.config import LLM_MODEL, LLM_BASE_URL, LLM_API_KEY
    if LLM_API_KEY:
        monkeypatch.setenv("OPENAI_API_KEY", LLM_API_KEY)
        monkeypatch.setenv("OPENAI_MODEL_NAME", LLM_MODEL)
        monkeypatch.setenv("OPENAI_API_BASE", LLM_BASE_URL)

    from novel_workflow.crewai.agents import create_writer, create_auditor, create_extractor

    try:
        writer = create_writer()
        auditor = create_auditor()
        extractor = create_extractor()
        assert writer.role == "Novel Chapter Writer"
        assert auditor.role == "Continuity Auditor"
        assert extractor.role == "Knowledge Extractor"
    except ImportError as e:
        pytest.skip(f"LLM initialization failed: {e}")


def test_context_order_aws_before_canon(project_root: Path):
    """AWS overlay should appear before canon in context."""
    from novel_workflow.crewai.flow import _build_context
    (project_root / "canon" / "approved_outline.md").write_text("# Outline")
    (project_root / "ledgers" / "timeline.json").write_text('{"schema_version":"1.0","events":[]}')
    (project_root / "arcs" / "arc_001" / "arc_working_state.json").write_text(
        '{"schema_version":"1.0","entries":[{"state_id":"aws_001","source_chapter":"ch_001","key":"k","value":"v","status":"working_accepted","depends_on":[]}]}'
    )
    context = _build_context(project_root, "arc_001", 2)
    aws_pos = context.find("Arc Working State")
    canon_pos = context.find("Approved Outline")
    assert aws_pos < canon_pos, "AWS should appear before canon in context"

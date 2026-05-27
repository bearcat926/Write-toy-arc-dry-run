"""Tests for proposal extraction - covers CrewAI wrapping, markdown blocks, nested JSON."""
import json
import pytest
from novel_workflow.crewai.flow import _extract_proposal


VALID_PROPOSAL = {
    "schema_version": "1.0",
    "claim": "Character A arrives at tavern",
    "source_layer": "draft",
    "source_artifact": "arcs/arc_001/drafts/ch_001.md",
    "evidence": "A walked through the heavy oak door",
    "confidence": "high",
    "target_ledger": "timeline",
    "operation": "append_event",
    "proposed_change": {"event_id": "e1", "summary": "A arrives"},
}


def test_pure_json():
    """Layer 1: Direct JSON output."""
    raw = json.dumps(VALID_PROPOSAL)
    result = _extract_proposal(raw)
    assert result is not None
    assert result["schema_version"] == "1.0"
    assert result["claim"] == "Character A arrives at tavern"


def test_json_with_whitespace():
    """Layer 1: JSON with leading/trailing whitespace."""
    raw = "  " + json.dumps(VALID_PROPOSAL) + "  \n"
    result = _extract_proposal(raw)
    assert result is not None


def test_markdown_code_block():
    """Layer 2: JSON wrapped in markdown code block."""
    raw = f"Here is the proposal:\n\n```json\n{json.dumps(VALID_PROPOSAL)}\n```\n\nEnd of proposal."
    result = _extract_proposal(raw)
    assert result is not None
    assert result["schema_version"] == "1.0"


def test_markdown_code_block_no_lang():
    """Layer 2: JSON wrapped in code block without language tag."""
    raw = f"```\n{json.dumps(VALID_PROPOSAL)}\n```"
    result = _extract_proposal(raw)
    assert result is not None


def test_crewai_wrapped_output():
    """Layer 3: CrewAI framework characters mixed with JSON."""
    raw = (
        "┌──────────────────────────┐\n"
        "│  Agent Output            │\n"
        "└──────────────────────────┘\n"
        f'{json.dumps(VALID_PROPOSAL)}\n'
        "┌──────────────────────────┐\n"
        "│  Completed               │\n"
        "└──────────────────────────┘\n"
    )
    result = _extract_proposal(raw)
    assert result is not None
    assert result["schema_version"] == "1.0"


def test_nested_json():
    """Layer 3: Nested JSON objects (proposed_change is nested)."""
    nested = {
        "schema_version": "1.0",
        "claim": "Complex proposal",
        "proposed_change": {
            "event_id": "e1",
            "nested": {"deep": True},
        },
    }
    raw = f"Agent output:\n{json.dumps(nested)}\nDone."
    result = _extract_proposal(raw)
    assert result is not None
    assert result["proposed_change"]["nested"]["deep"] is True


def test_no_schema_version():
    """Should return None if no schema_version found."""
    raw = '{"claim": "no schema version here"}'
    result = _extract_proposal(raw)
    assert result is None


def test_garbage_text():
    """Should return None for non-JSON text."""
    raw = "This is just a regular paragraph with no JSON at all."
    result = _extract_proposal(raw)
    assert result is None


def test_empty_string():
    """Should return None for empty input."""
    result = _extract_proposal("")
    assert result is None


def test_multiple_json_objects():
    """Should return the first valid one with schema_version."""
    raw = (
        '{"other": "data"}\n'
        f'{json.dumps(VALID_PROPOSAL)}\n'
    )
    result = _extract_proposal(raw)
    assert result is not None
    assert result["schema_version"] == "1.0"


def test_crewai_tool_output_style():
    """Real CrewAI output style: box drawing + metadata + JSON."""
    raw = (
        "│  Output: Wrote draft to /path/to/file                 │\n"
        "│  id: abc123                                           │\n"
        f'  {json.dumps(VALID_PROPOSAL)}\n'
        "│  LiteAgent Completed                                  │\n"
    )
    result = _extract_proposal(raw)
    assert result is not None
    assert result["claim"] == "Character A arrives at tavern"

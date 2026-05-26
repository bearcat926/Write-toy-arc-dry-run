import json
from pathlib import Path
from crewai.tools import tool
from ..guards.path_safety import PathSafetyGuard
from ..schemas.proposal import LedgerUpdateProposal

# Set at runtime by NovelFlow before dispatching agents
PROJECT_ROOT = Path(".")


@tool("write_draft")
def write_draft(path: str, content: str) -> str:
    """Write a chapter draft to the specified path under arcs/*/drafts/."""
    guard = PathSafetyGuard(PROJECT_ROOT)
    resolved = guard.check_write_path(path, "agent")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content)
    return f"Wrote draft to {resolved}"


@tool("write_review")
def write_review(path: str, content: str) -> str:
    """Write a review report to the specified path under arcs/*/reviews/."""
    guard = PathSafetyGuard(PROJECT_ROOT)
    resolved = guard.check_write_path(path, "agent")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content)
    return f"Wrote review to {resolved}"


@tool("write_proposal")
def write_proposal(path: str, content: str) -> str:
    """Write a ledger update proposal (valid JSON) to the specified path under arcs/*/proposals/."""
    guard = PathSafetyGuard(PROJECT_ROOT)
    resolved = guard.check_write_path(path, "agent")
    data = json.loads(content)
    LedgerUpdateProposal.model_validate(data)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content)
    return f"Wrote proposal to {resolved}"

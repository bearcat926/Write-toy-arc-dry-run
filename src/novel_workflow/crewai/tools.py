import json
import os
import re
from pathlib import Path
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from ..guards.path_safety import PathSafetyGuard
from ..schemas.proposal import LedgerUpdateProposal


def _get_project_root() -> Path:
    """Get PROJECT_ROOT from environment variable (thread-safe) or global default."""
    env_root = os.environ.get("NOVEL_WORKFLOW_PROJECT_ROOT")
    if env_root:
        return Path(env_root)
    # Fallback: check if PROJECT_ROOT global was set
    if PROJECT_ROOT != Path("."):
        return PROJECT_ROOT
    # Last resort: current directory
    return Path(".")


# Set at runtime by NovelFlow before dispatching agents
PROJECT_ROOT = Path(".")


class WriteDraftInput(BaseModel):
    path: str = Field(description="Path to write the draft, e.g. arcs/arc_001/drafts/ch_001.md")
    content: str = Field(description="The chapter draft content in markdown")


class WriteDraftTool(BaseTool):
    name: str = "write_draft"
    description: str = "Write a chapter draft to the specified path under arcs/*/drafts/."
    args_schema: type[BaseModel] = WriteDraftInput
    _project_root: Path = Path(".")

    def set_project_root(self, root: Path):
        self._project_root = root

    def _run(self, path: str, content: str) -> str:
        project_root = self._project_root if self._project_root != Path(".") else _get_project_root()
        guard = PathSafetyGuard(project_root)
        resolved = guard.check_write_path(path, "agent")
        resolved = resolved.resolve()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
        return f"Wrote draft to {resolved}"


class WriteReviewInput(BaseModel):
    path: str = Field(description="Path to write the review, e.g. arcs/arc_001/reviews/ch_001_review.md")
    content: str = Field(description="The review content in markdown")


class WriteReviewTool(BaseTool):
    name: str = "write_review"
    description: str = "Write a review report to the specified path under arcs/*/reviews/."
    args_schema: type[BaseModel] = WriteReviewInput
    _project_root: Path = Path(".")

    def set_project_root(self, root: Path):
        self._project_root = root

    def _run(self, path: str, content: str) -> str:
        project_root = self._project_root if self._project_root != Path(".") else _get_project_root()
        guard = PathSafetyGuard(project_root)
        resolved = guard.check_write_path(path, "agent")
        resolved = resolved.resolve()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
        return f"Wrote review to {resolved}"


class WriteProposalInput(BaseModel):
    path: str = Field(description="Path to write the proposal, e.g. arcs/arc_001/proposals/ch_001_ledger_update_proposal.json")
    content: str = Field(description="The proposal as a JSON string")


class WriteProposalTool(BaseTool):
    name: str = "write_proposal"
    description: str = "Write a ledger update proposal (valid JSON) to the specified path under arcs/*/proposals/."
    args_schema: type[BaseModel] = WriteProposalInput
    _project_root: Path = Path(".")

    def set_project_root(self, root: Path):
        self._project_root = root

    def _run(self, path: str, content: str) -> str:
        project_root = self._project_root if self._project_root != Path(".") else _get_project_root()
        guard = PathSafetyGuard(project_root)
        resolved = guard.check_write_path(path, "agent")
        resolved = resolved.resolve()
        # Clean markdown code block wrappers
        cleaned = content.strip()
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned)
        cleaned = re.sub(r'\n?```\s*$', '', cleaned)
        cleaned = cleaned.strip()
        data = json.loads(cleaned)
        LedgerUpdateProposal.model_validate(data)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, indent=2, ensure_ascii=False))
            f.flush()
        return f"Wrote proposal to {resolved}"


# Export tool instances with result_as_answer=True
# This ensures CrewAI Agent uses tool output as the task result
write_draft = WriteDraftTool(result_as_answer=True)
write_review = WriteReviewTool(result_as_answer=True)
write_proposal = WriteProposalTool(result_as_answer=True)

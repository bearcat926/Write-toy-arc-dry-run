import json
import re
from pathlib import Path
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from ..guards.path_safety import PathSafetyGuard
from ..schemas.proposal import LedgerUpdateProposal

# Set at runtime by NovelFlow before dispatching agents
PROJECT_ROOT = Path(".")


class WriteDraftInput(BaseModel):
    path: str = Field(description="Path to write the draft, e.g. arcs/arc_001/drafts/ch_001.md")
    content: str = Field(description="The chapter draft content in markdown")


class WriteDraftTool(BaseTool):
    name: str = "write_draft"
    description: str = "Write a chapter draft to the specified path under arcs/*/drafts/."
    args_schema: type[BaseModel] = WriteDraftInput

    def _run(self, path: str, content: str) -> str:
        import sys
        guard = PathSafetyGuard(PROJECT_ROOT)
        resolved = guard.check_write_path(path, "agent")
        resolved = resolved.resolve()  # Ensure absolute path
        resolved.parent.mkdir(parents=True, exist_ok=True)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
        # Verify write
        if resolved.exists():
            size = resolved.stat().st_size
            print(f"[TOOL] Successfully wrote {size} bytes to {resolved}", file=sys.stderr)
        else:
            print(f"[TOOL] WARNING: File not found after write: {resolved}", file=sys.stderr)
        return f"Wrote draft to {resolved}"


class WriteReviewInput(BaseModel):
    path: str = Field(description="Path to write the review, e.g. arcs/arc_001/reviews/ch_001_review.md")
    content: str = Field(description="The review content in markdown")


class WriteReviewTool(BaseTool):
    name: str = "write_review"
    description: str = "Write a review report to the specified path under arcs/*/reviews/."
    args_schema: type[BaseModel] = WriteReviewInput

    def _run(self, path: str, content: str) -> str:
        guard = PathSafetyGuard(PROJECT_ROOT)
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

    def _run(self, path: str, content: str) -> str:
        guard = PathSafetyGuard(PROJECT_ROOT)
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

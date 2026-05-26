"""
NovelFlow: Orchestrate Writer -> Auditor -> Extractor pipeline.
Uses CrewAI Agents for LLM calls but Python for orchestration and file I/O.
"""
import json
import os
import re
from pathlib import Path

from crewai import Agent, LLM

from ..system_scripts.arc_state_manager import ArcWorkingStateManager
from ..system_scripts.ledger_diff_generator import LedgerDiffGenerator
from ..system_scripts.atomic_apply_manager import AtomicApplyManager
from ..schemas.gate import GateRecord
from ..schemas.diff import LedgerDiff
from ..schemas.proposal import LedgerUpdateProposal
from ..validators.proposal_validator import ProposalValidator
from .config import LLM_MODEL, LLM_BASE_URL, LLM_API_KEY
from .tools import safe_write_draft, safe_write_review, safe_write_proposal


def _create_llm() -> LLM:
    llm = LLM(
        model=f"openai/{LLM_MODEL}",
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        max_tokens=32000,
    )
    llm.supports_function_calling = lambda: True
    return llm


def _build_context(root: Path, arc_id: str, current_ch: int) -> str:
    """Build context from canon + ledgers + arc_working_state + previous chapters."""
    parts = []

    canon_outline = root / "canon" / "approved_outline.md"
    if canon_outline.exists():
        parts.append(f"## Approved Outline\n{canon_outline.read_text(encoding='utf-8', errors='replace')}")

    for ledger_file in (root / "ledgers").glob("*.json"):
        parts.append(f"## Ledger: {ledger_file.stem}\n{ledger_file.read_text(encoding='utf-8', errors='replace')}")

    aws_path = root / "arcs" / arc_id / "arc_working_state.json"
    if aws_path.exists():
        parts.append(f"## Arc Working State\n{aws_path.read_text(encoding='utf-8', errors='replace')}")

    for prev_ch in range(1, current_ch):
        prev_path = root / "arcs" / arc_id / "drafts" / f"ch_{prev_ch:03d}.md"
        if prev_path.exists():
            parts.append(f"## Previous Chapter ch_{prev_ch:03d}\n{prev_path.read_text(encoding='utf-8', errors='replace')}")

    return "\n\n".join(parts) if parts else "(empty project)"


def _extract_proposal(raw_output: str) -> dict | None:
    """Extract proposal JSON from LLM output."""
    # Try to find JSON in the output
    json_matches = re.findall(r'\{[^{}]*"schema_version"[^{}]*\}', raw_output, re.DOTALL)
    for match in json_matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    # Try parsing entire output
    try:
        return json.loads(raw_output.strip())
    except json.JSONDecodeError:
        pass
    return None


def run_novel_flow(
    project_root: str | Path,
    arc_id: str = "arc_001",
    chapters_total: int = 3,
    dry_run: bool = False,
    arc_end_gate: GateRecord | None = None,
) -> dict:
    """
    Run the full novel flow: initialize -> chapters -> finalize.
    Returns a dict with results and file paths.

    Args:
        dry_run: If True, auto-approves arc_end gate (for testing only).
                 If False, arc_end_gate must be provided by the caller.
        arc_end_gate: Gate record from the author. Required when dry_run=False.
    """
    if not dry_run and arc_end_gate is None:
        raise ValueError("arc_end_gate is required when dry_run=False. "
                         "The system cannot approve gates on behalf of the author.")
    root = Path(project_root).resolve()
    llm = _create_llm()
    aws_mgr = ArcWorkingStateManager(root)
    proposal_validator = ProposalValidator(root)

    # Create arc directories
    for d in ["drafts", "reviews", "proposals", "reports", "gates", "checkpoints", "archive"]:
        (root / "arcs" / arc_id / d).mkdir(parents=True, exist_ok=True)

    # Initialize arc_working_state
    aws_mgr.initialize(arc_id)
    print(f"[NovelFlow] Initialized arc {arc_id} at {root}")

    # Create agents
    writer = Agent(
        role="Novel Chapter Writer",
        goal="Write a compelling chapter that advances the story based on the provided context",
        backstory="You are a skilled fiction writer who crafts engaging chapters.",
        llm=llm,
        verbose=False,
    )
    auditor = Agent(
        role="Continuity Auditor",
        goal="Review the chapter draft for consistency with canon, ledgers, and arc_contract.",
        backstory="You are a meticulous continuity checker.",
        llm=llm,
        verbose=False,
    )
    extractor = Agent(
        role="Knowledge Extractor",
        goal="Extract narrative facts from the chapter as structured JSON.",
        backstory="You identify narrative facts that need to be recorded in story ledgers.",
        llm=llm,
        verbose=False,
    )

    chapter_results = []
    validated_proposals = []  # Collect only validated proposals during chapter loop

    for ch_num in range(1, chapters_total + 1):
        ch_id = f"ch_{ch_num:03d}"
        print(f"\n[NovelFlow] === Chapter {ch_id} ===")

        context = _build_context(root, arc_id, ch_num)

        # Writer
        print(f"[NovelFlow] Writer starting...")
        writer_result = writer.kickoff(
            f"Write chapter {ch_id} of the story.\n\n"
            f"Story context:\n{context}\n\n"
            f"Write ONLY the chapter content in markdown format."
        )
        content = writer_result.raw if hasattr(writer_result, 'raw') else str(writer_result)
        draft_path = safe_write_draft(root, f"arcs/{arc_id}/drafts/{ch_id}.md", content)
        print(f"[NovelFlow] Draft saved to {draft_path}")

        # Auditor
        draft_content = draft_path.read_text(encoding="utf-8", errors="replace")
        print(f"[NovelFlow] Auditor starting...")
        auditor_result = auditor.kickoff(
            f"Review chapter {ch_id} for continuity issues.\n\n"
            f"Draft:\n{draft_content}\n\n"
            f"Story context:\n{context}\n\n"
            f"Write ONLY the review content."
        )
        content = auditor_result.raw if hasattr(auditor_result, 'raw') else str(auditor_result)
        review_path = safe_write_review(root, f"arcs/{arc_id}/reviews/{ch_id}_review.md", content)
        print(f"[NovelFlow] Review saved to {review_path}")

        # Extractor
        review_content = review_path.read_text(encoding="utf-8", errors="replace")
        print(f"[NovelFlow] Extractor starting...")
        extractor_result = extractor.kickoff(
            f"Extract narrative facts from chapter {ch_id} as JSON.\n\n"
            f"Draft:\n{draft_content}\n\n"
            f"Review:\n{review_content}\n\n"
            f"Output a JSON object with this structure:\n"
            f'{{"schema_version": "1.0", "claim": "...", "source_layer": "draft", '
            f'"source_artifact": "arcs/{arc_id}/drafts/{ch_id}.md", '
            f'"evidence": "...", "confidence": "high", '
            f'"target_ledger": "timeline", "operation": "append_event", '
            f'"proposed_change": {{"event_id": "...", "summary": "..."}}}}\n\n'
            f"Output ONLY the JSON, no other text."
        )
        raw_output = extractor_result.raw if hasattr(extractor_result, 'raw') else str(extractor_result)
        proposal_data = _extract_proposal(raw_output)
        if proposal_data:
            try:
                proposal_path = safe_write_proposal(
                    root,
                    f"arcs/{arc_id}/proposals/{ch_id}_ledger_update_proposal.json",
                    json.dumps(proposal_data),
                )
                print(f"[NovelFlow] Proposal saved to {proposal_path}")

                # Validate and merge
                proposal = LedgerUpdateProposal.model_validate(proposal_data)
                result = proposal_validator.validate(proposal)
                if result.is_valid:
                    aws_mgr.merge_proposal(arc_id, proposal, ch_id)
                    validated_proposals.append(proposal_data)
                    print(f"[NovelFlow] Merged proposal: {proposal.claim}")
                else:
                    print(f"[NovelFlow] Proposal invalid ({result.error_code})")
            except Exception as e:
                print(f"[NovelFlow] Proposal validation error: {e}")
        else:
            print(f"[NovelFlow] Could not extract proposal from output")

        chapter_results.append(ch_id)
        print(f"[NovelFlow] Chapter {ch_id} complete")

    # Finalize
    print(f"\n[NovelFlow] === Finalizing arc {arc_id} ===")

    # Generate ledger_diff from validated proposals only
    gen = LedgerDiffGenerator()
    diff_data = gen.generate(validated_proposals)
    ledger_diff = LedgerDiff(arc_id=arc_id, operations=diff_data["operations"])
    (root / "arcs" / arc_id / "reports" / "ledger_diff.json").write_text(
        json.dumps(ledger_diff.model_dump(mode="json"), indent=2)
    )

    # Create or use provided arc_end gate
    if dry_run:
        gate = GateRecord(
            gate_id=f"ae_{arc_id}",
            gate_type="arc_end",
            target_artifact=arc_id,
            decision="approved",
            author_input_evidence="[DRY RUN] auto-approved for testing only",
            author_id="dry_run_system",
            source_artifacts=[],
        )
    else:
        gate = arc_end_gate

    # Atomic apply
    apply_mgr = AtomicApplyManager(root)
    draft_files = [f"{ch_id}.md" for ch_id in chapter_results]
    apply_result = apply_mgr.apply(arc_id, gate, draft_files, ledger_diff, None)
    print(f"[NovelFlow] Apply result: {apply_result}")

    return {
        "chapters": chapter_results,
        "apply_result": apply_result,
        "manuscript_dir": str(root / "canon" / "manuscript"),
        "ledgers_dir": str(root / "ledgers"),
    }

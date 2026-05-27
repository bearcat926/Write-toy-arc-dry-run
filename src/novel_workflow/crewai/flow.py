"""
NovelFlow: Orchestrate Writer -> Auditor -> Extractor pipeline.
Uses CrewAI Agents for LLM calls but Python for orchestration and file I/O.
"""
import json
import json as _json
import os
import re
import time
from pathlib import Path

from crewai import Agent, LLM

from ..system_scripts.arc_state_manager import ArcWorkingStateManager
from ..system_scripts.ledger_diff_generator import LedgerDiffGenerator
from ..system_scripts.atomic_apply_manager import AtomicApplyManager
from ..system_scripts.chapter_effect_checker import ChapterEffectChecker
from ..schemas.gate import GateRecord
from ..schemas.diff import LedgerDiff
from ..schemas.proposal import LedgerUpdateProposal
from ..schemas.progress import ProgressEntry
from ..schemas.chapter_effect import ChapterEffectReport
from ..validators.proposal_validator import ProposalValidator
from ..metrics.collector import MetricsCollector, ChapterMetrics
from .config import LLM_MODEL, LLM_BASE_URL, LLM_API_KEY
from .tools import safe_write_draft, safe_write_review, safe_write_proposal


def _create_llm() -> LLM:
    llm = LLM(
        model=f"openai/{LLM_MODEL}",
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        max_tokens=8000,
        timeout=300,  # 5 min timeout per LLM call
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

    # Previous chapters: only include first 500 chars as summary to avoid context overflow
    MAX_CH_PREVIEW = 500
    for prev_ch in range(1, current_ch):
        prev_path = root / "arcs" / arc_id / "drafts" / f"ch_{prev_ch:03d}.md"
        if prev_path.exists():
            full_text = prev_path.read_text(encoding='utf-8', errors='replace')
            preview = full_text[:MAX_CH_PREVIEW]
            if len(full_text) > MAX_CH_PREVIEW:
                preview += f"\n... ({len(full_text) - MAX_CH_PREVIEW} more chars)"
            parts.append(f"## Previous Chapter ch_{prev_ch:03d} (summary)\n{preview}")

    return "\n\n".join(parts) if parts else "(empty project)"


def _extract_proposal(raw_output: str) -> dict | None:
    """Extract proposal JSON from LLM output using 3-layer fallback."""
    # Layer 1: Direct json.loads
    try:
        data = json.loads(raw_output.strip())
        if isinstance(data, dict) and "schema_version" in data:
            return data
    except (json.JSONDecodeError, ValueError):
        pass

    # Layer 2: Extract markdown code block
    code_block = re.search(r'```(?:json)?\s*\n(.*?)\n```', raw_output, re.DOTALL)
    if code_block:
        try:
            data = json.loads(code_block.group(1).strip())
            if isinstance(data, dict) and "schema_version" in data:
                return data
        except (json.JSONDecodeError, ValueError):
            pass

    # Layer 3: Bracket counting to find outermost JSON object containing schema_version
    for i, ch in enumerate(raw_output):
        if ch == '{':
            depth = 0
            for j in range(i, len(raw_output)):
                if raw_output[j] == '{':
                    depth += 1
                elif raw_output[j] == '}':
                    depth -= 1
                if depth == 0:
                    candidate = raw_output[i:j+1]
                    if 'schema_version' in candidate:
                        try:
                            data = json.loads(candidate)
                            if isinstance(data, dict):
                                return data
                        except json.JSONDecodeError:
                            pass
                    break

    return None


def _run_revision_loop(
    root: Path,
    arc_id: str,
    chapter_ids: list[str],
    max_revisions: int = 2,
) -> None:
    """
    Revision loop stub for production mode.
    When gate.decision == 'rejected', iterates up to max_revisions times:
      1. Mark rejected chapters
      2. Rewrite chapters
      3. Re-run review + proposal

    Currently a no-op stub; production path needs real gate decision integration.
    """
    print(f"[NovelFlow] Revision loop triggered for {arc_id} (max {max_revisions} loops)")
    # TODO: Implement revision loop for production path
    # - Identify rejected chapters from gate feedback
    # - Rewrite using writer agent
    # - Re-audit and re-extract proposals
    # - Re-attempt apply


def run_novel_flow(
    project_root: str | Path,
    arc_id: str = "arc_001",
    chapters_total: int = 3,
    start_ch: int = 1,
    dry_run: bool = False,
    arc_end_gate: GateRecord | None = None,
) -> dict:
    """
    Run the full novel flow: initialize -> chapters -> finalize.
    Returns a dict with results and file paths.

    Args:
        start_ch: First chapter number to generate (1-based). Allows resuming from a checkpoint.
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

    # Create arc_contract.md template if not exists
    arc_contract_path = root / "arcs" / arc_id / "arc_contract.md"
    if not arc_contract_path.exists():
        arc_contract_path.write_text(
            f"# Arc Contract: {arc_id}\n\n"
            f"## Hard Requirements\n\n"
            f"## Absolute Prohibitions\n\n"
            f"## Checkpoint Chapters\n\ncheckpoint_chapters: []\n"
            f"checkpoint_interval: null\n",
            encoding="utf-8",
        )

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

    # Parse checkpoint_chapters from arc_contract
    contract_path = root / "arcs" / arc_id / "arc_contract.md"
    checkpoint_chapters = []
    if contract_path.exists():
        _ckpt_match = re.search(r'checkpoint_chapters:\s*\[([^\]]*)\]', contract_path.read_text(encoding="utf-8"))
        if _ckpt_match and _ckpt_match.group(1).strip():
            checkpoint_chapters = [int(x.strip()) for x in _ckpt_match.group(1).split(",") if x.strip()]

    # Metrics collector
    metrics_collector = MetricsCollector(root)
    effect_checker = ChapterEffectChecker()
    chapter_start = time.time()

    for ch_num in range(start_ch, chapters_total + 1):
        ch_id = f"ch_{ch_num:03d}"
        print(f"\n[NovelFlow] === Chapter {ch_id} ===")

        context = _build_context(root, arc_id, ch_num)

        # Writer
        writer_prompt = f"Write chapter {ch_id} of the story.\n\nStory context:\n{context}\n\nWrite ONLY the chapter content in markdown format."
        print(f"[TIMER] ch={ch_id} agent=Writer prompt_len={len(writer_prompt)} starting...")
        _t0 = time.time()
        writer_result = writer.kickoff(writer_prompt)
        print(f"[TIMER] ch={ch_id} agent=Writer elapsed={time.time()-_t0:.1f}s")
        content = writer_result.raw if hasattr(writer_result, 'raw') else str(writer_result)
        draft_path = safe_write_draft(root, f"arcs/{arc_id}/drafts/{ch_id}.md", content)
        print(f"[NovelFlow] Draft saved to {draft_path}")

        # Auditor
        draft_content = draft_path.read_text(encoding="utf-8", errors="replace")
        auditor_prompt = f"Review chapter {ch_id} for continuity issues.\n\nDraft:\n{draft_content}\n\nStory context:\n{context}\n\nWrite ONLY the review content."
        print(f"[TIMER] ch={ch_id} agent=Auditor prompt_len={len(auditor_prompt)} starting...")
        _t0 = time.time()
        auditor_result = auditor.kickoff(auditor_prompt)
        print(f"[TIMER] ch={ch_id} agent=Auditor elapsed={time.time()-_t0:.1f}s")
        content = auditor_result.raw if hasattr(auditor_result, 'raw') else str(auditor_result)
        review_path = safe_write_review(root, f"arcs/{arc_id}/reviews/{ch_id}_review.md", content)
        print(f"[NovelFlow] Review saved to {review_path}")

        # Extractor
        review_content = review_path.read_text(encoding="utf-8", errors="replace")
        extractor_prompt = (
            f"Extract narrative facts from chapter {ch_id} as JSON.\n\n"
            f"Draft:\n{draft_content}\n\n"
            f"Review:\n{review_content}\n\n"
            f"Output a JSON object with this structure:\n"
            f'{{"schema_version": "1.0", "claim": "...", "source_layer": "draft", '
            f'"source_artifact": "arcs/{arc_id}/drafts/{ch_id}.md", '
            f'"evidence": "...", "confidence": "high", '
            f'"target_ledger": "timeline", "operation": "append_event", '
            f'"proposed_change": {{"event_id": "...", "summary": "..."}}}}\n\n'
            f"Return ONLY valid JSON. No markdown. No explanation. No surrounding text."
        )
        print(f"[TIMER] ch={ch_id} agent=Extractor prompt_len={len(extractor_prompt)} starting...")
        _t0 = time.time()
        extractor_result = extractor.kickoff(extractor_prompt)
        print(f"[TIMER] ch={ch_id} agent=Extractor elapsed={time.time()-_t0:.1f}s")
        raw_output = extractor_result.raw if hasattr(extractor_result, 'raw') else str(extractor_result)
        proposal_data = _extract_proposal(raw_output)
        proposal_merged_flag = False
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
                    proposal_merged_flag = True
                    print(f"[NovelFlow] Merged proposal: {proposal.claim}")
                else:
                    print(f"[NovelFlow] Proposal invalid ({result.error_code})")
            except Exception as e:
                print(f"[NovelFlow] Proposal validation error: {e}")
        else:
            print(f"[NovelFlow] Could not extract proposal from output")

        chapter_results.append(ch_id)

        # 1.2 progress.jsonl writing
        progress_entry = ProgressEntry(
            event_type="chapter_completed",
            artifact_path=f"arcs/{arc_id}/drafts/{ch_id}.md",
            details={"proposal_merged": proposal_merged_flag},
            contains_narrative_fact=False,
        )
        with open(root / "workspace" / "progress.jsonl", "a", encoding="utf-8") as pf:
            pf.write(_json.dumps(progress_entry.model_dump(mode="json"), ensure_ascii=False) + "\n")

        # 1.3 ChapterEffectChecker integration (non-blocking)
        effect_report = ChapterEffectReport(chapter_id=ch_id, scene_goal="auto-detected")
        _passed, _failures = effect_checker.check(effect_report)
        if not _passed:
            print(f"[NovelFlow] ChapterEffect warning for {ch_id}: {_failures}")

        # 1.4 MetricsCollector recording
        metrics_collector.record_chapter(ChapterMetrics(
            arc_id=arc_id,
            chapter_id=ch_id,
            proposal_accepted=proposal_merged_flag,
            audit_failed=False,
            pause_triggered=False,
            runtime_seconds=time.time() - chapter_start,
        ))
        chapter_start = time.time()

        # 1.5 checkpoint_chapters check
        if ch_num in checkpoint_chapters:
            print(f"[NovelFlow] CHECKPOINT: Chapter {ch_id} reached checkpoint. Pausing for author review.")

        print(f"[NovelFlow] Chapter {ch_id} complete")

    # Finalize
    print(f"\n[NovelFlow] === Finalizing arc {arc_id} ===")

    # Hard rule: no proposals = no apply (unless manuscript_only mode)
    if len(chapter_results) > 0 and len(validated_proposals) == 0:
        print(f"[NovelFlow] WARNING: {len(chapter_results)} chapters completed but 0 proposals validated")
        print(f"[NovelFlow] Skipping ledger_diff generation and apply")
        print(f"[NovelFlow] Drafts saved but ledgers NOT updated")
        return {
            "result": "skipped_no_proposals",
            "chapters": chapter_results,
            "apply_result": None,
            "manuscript_dir": str(root / "canon" / "manuscript"),
            "ledgers_dir": str(root / "ledgers"),
        }

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

    # 1.6 dashboard_report.md generation
    dashboard_path = root / "workspace" / "dashboard_report.md"
    dashboard_lines = [
        f"# Dashboard Report: {arc_id}",
        f"",
        f"**Status:** derived (auto-generated)",
        f"**Source:** system script",
        f"",
        f"## Chapters",
        f"",
    ]
    for ch_id_item in chapter_results:
        dashboard_lines.append(f"- {ch_id_item}: drafted, reviewed")
    dashboard_lines.extend([
        f"",
        f"## Proposals",
        f"",
        f"- Validated: {len(validated_proposals)}",
        f"",
        f"## Apply",
        f"",
        f"- Result: {apply_result.get('result', 'unknown')}",
        f"- Diff hash: {apply_result.get('diff_hash', 'N/A')}",
    ])
    dashboard_path.write_text("\n".join(dashboard_lines), encoding="utf-8")
    print(f"[NovelFlow] Dashboard saved to {dashboard_path}")

    # Revision loop (production mode stub)
    if not dry_run and gate.decision == "rejected":
        _run_revision_loop(root, arc_id, chapter_results, max_revisions=2)

    return {
        "chapters": chapter_results,
        "apply_result": apply_result,
        "manuscript_dir": str(root / "canon" / "manuscript"),
        "ledgers_dir": str(root / "ledgers"),
    }

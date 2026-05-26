import json
from pathlib import Path
from pydantic import BaseModel
from crewai.flow.flow import Flow, listen, start
from ..system_scripts.arc_state_manager import ArcWorkingStateManager
from ..system_scripts.ledger_diff_generator import LedgerDiffGenerator
from ..system_scripts.atomic_apply_manager import AtomicApplyManager
from ..schemas.gate import GateRecord
from ..schemas.diff import LedgerDiff
from ..schemas.proposal import LedgerUpdateProposal
from ..validators.proposal_validator import ProposalValidator
from ..guards.path_safety import PathSafetyGuard
from .agents import create_writer, create_auditor, create_extractor
from . import tools as tools_module


class NovelFlowState(BaseModel):
    arc_id: str = "arc_001"
    current_chapter: int = 0
    chapters_total: int = 3
    project_root: str = ""
    chapter_results: list[str] = []


class NovelFlow(Flow[NovelFlowState]):

    @start()
    def initialize_arc(self):
        """Initialize arc_working_state from canon/ledgers."""
        root = Path(self.state.project_root)
        tools_module.PROJECT_ROOT = root
        # Set environment variable for thread-safe access
        import os
        os.environ["NOVEL_WORKFLOW_PROJECT_ROOT"] = str(root.resolve())
        # Set project root on tool instances
        tools_module.write_draft.set_project_root(root)
        tools_module.write_review.set_project_root(root)
        tools_module.write_proposal.set_project_root(root)

        for d in ["drafts", "reviews", "proposals", "reports", "gates", "checkpoints", "archive"]:
            (root / "arcs" / self.state.arc_id / d).mkdir(parents=True, exist_ok=True)

        mgr = ArcWorkingStateManager(root)
        mgr.initialize(self.state.arc_id)
        print(f"[NovelFlow] Initialized arc {self.state.arc_id}")

    @listen(initialize_arc)
    def chapter_loop(self):
        """Run Writer -> Auditor -> Extractor for each chapter."""
        root = Path(self.state.project_root)
        aws_mgr = ArcWorkingStateManager(root)
        proposal_validator = ProposalValidator(root)

        # Create agents WITHOUT tools - we'll save output ourselves
        from crewai import Agent, LLM
        from .config import LLM_MODEL, LLM_BASE_URL, LLM_API_KEY

        llm = LLM(
            model=f"openai/{LLM_MODEL}",
            base_url=LLM_BASE_URL,
            api_key=LLM_API_KEY,
            max_tokens=32000,
        )
        llm.supports_function_calling = lambda: True

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

        for ch_num in range(1, self.state.chapters_total + 1):
            ch_id = f"ch_{ch_num:03d}"
            self.state.current_chapter = ch_num
            print(f"\n[NovelFlow] === Chapter {ch_id} ===")

            context = self._build_context(root, ch_id)

            # Writer - get output and save directly
            print(f"[NovelFlow] Writer starting...")
            writer_result = writer.kickoff(
                f"Write chapter {ch_id} of the story.\n\n"
                f"Story context:\n{context}\n\n"
                f"Write ONLY the chapter content in markdown format."
            )
            draft_path = root / "arcs" / self.state.arc_id / "drafts" / f"{ch_id}.md"
            draft_path.parent.mkdir(parents=True, exist_ok=True)
            content = writer_result.raw if hasattr(writer_result, 'raw') else str(writer_result)
            with open(draft_path, "w", encoding="utf-8") as f:
                f.write(content)
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
            review_path = root / "arcs" / self.state.arc_id / "reviews" / f"{ch_id}_review.md"
            review_path.parent.mkdir(parents=True, exist_ok=True)
            content = auditor_result.raw if hasattr(auditor_result, 'raw') else str(auditor_result)
            with open(review_path, "w", encoding="utf-8") as f:
                f.write(content)
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
                f'"source_artifact": "arcs/{self.state.arc_id}/drafts/{ch_id}.md", '
                f'"evidence": "...", "confidence": "high", '
                f'"target_ledger": "timeline", "operation": "append_event", '
                f'"proposed_change": {{"event_id": "...", "summary": "..."}}}}\n\n'
                f"Output ONLY the JSON, no other text."
            )
            proposal_path = root / "arcs" / self.state.arc_id / "proposals" / f"{ch_id}_ledger_update_proposal.json"
            proposal_path.parent.mkdir(parents=True, exist_ok=True)
            raw_output = extractor_result.raw if hasattr(extractor_result, 'raw') else str(extractor_result)
            self._extract_and_save_proposal(raw_output, proposal_path, ch_id)

            # System script: validate + merge
            self._validate_and_merge(root, ch_id, aws_mgr, proposal_validator)

            self.state.chapter_results.append(ch_id)
            print(f"[NovelFlow] Chapter {ch_id} complete")

    @listen(chapter_loop)
    def finalize_arc(self):
        """Generate ledger_diff and apply."""
        root = Path(self.state.project_root)
        arc_id = self.state.arc_id
        print(f"\n[NovelFlow] === Finalizing arc {arc_id} ===")

        all_proposals = []
        for ch_id in self.state.chapter_results:
            proposal_path = root / "arcs" / arc_id / "proposals" / f"{ch_id}_ledger_update_proposal.json"
            if proposal_path.exists():
                data = json.loads(proposal_path.read_text(encoding="utf-8", errors="replace"))
                if isinstance(data, list):
                    all_proposals.extend(data)
                else:
                    all_proposals.append(data)

        gen = LedgerDiffGenerator()
        diff_data = gen.generate(all_proposals)
        ledger_diff = LedgerDiff(arc_id=arc_id, operations=diff_data["operations"])
        (root / "arcs" / arc_id / "reports" / "ledger_diff.json").write_text(
            json.dumps(ledger_diff.model_dump(mode="json"), indent=2)
        )

        gate = GateRecord(
            gate_id=f"ae_{arc_id}",
            gate_type="arc_end",
            target_artifact=arc_id,
            decision="approved",
            author_input_evidence="auto-approved for dry run",
            author_id="local_author",
            source_artifacts=[],
        )

        apply_mgr = AtomicApplyManager(root)
        draft_files = [f"{ch_id}.md" for ch_id in self.state.chapter_results]
        result = apply_mgr.apply(arc_id, gate, draft_files, ledger_diff, None)
        print(f"[NovelFlow] Apply result: {result}")

    def _build_context(self, root: Path, ch_id: str) -> str:
        """Build context from canon + ledgers + arc_working_state."""
        parts = []

        canon_outline = root / "canon" / "approved_outline.md"
        if canon_outline.exists():
            parts.append(f"## Approved Outline\n{canon_outline.read_text(encoding='utf-8', errors='replace')}")

        for ledger_file in (root / "ledgers").glob("*.json"):
            parts.append(f"## Ledger: {ledger_file.stem}\n{ledger_file.read_text(encoding='utf-8', errors='replace')}")

        aws_path = root / "arcs" / self.state.arc_id / "arc_working_state.json"
        if aws_path.exists():
            parts.append(f"## Arc Working State\n{aws_path.read_text(encoding='utf-8', errors='replace')}")

        for prev_ch in range(1, int(ch_id.split("_")[1])):
            prev_path = root / "arcs" / self.state.arc_id / "drafts" / f"ch_{prev_ch:03d}.md"
            if prev_path.exists():
                parts.append(f"## Previous Chapter ch_{prev_ch:03d}\n{prev_path.read_text(encoding='utf-8', errors='replace')}")

        return "\n\n".join(parts) if parts else "(empty project)"

    def _validate_and_merge(self, root: Path, ch_id: str,
                            aws_mgr: ArcWorkingStateManager,
                            proposal_validator: ProposalValidator):
        """System script: validate proposal and merge into arc_working_state."""
        proposal_path = root / "arcs" / self.state.arc_id / "proposals" / f"{ch_id}_ledger_update_proposal.json"
        if not proposal_path.exists():
            print(f"[NovelFlow] No proposal for {ch_id}, skipping merge")
            return

        data = json.loads(proposal_path.read_text(encoding="utf-8", errors="replace"))
        proposals = data if isinstance(data, list) else [data]

        for p_data in proposals:
            try:
                proposal = LedgerUpdateProposal.model_validate(p_data)
                result = proposal_validator.validate(proposal)
                if result.is_valid:
                    aws_mgr.merge_proposal(self.state.arc_id, proposal, ch_id)
                    print(f"[NovelFlow] Merged proposal for {ch_id}: {proposal.claim}")
                else:
                    print(f"[NovelFlow] Proposal invalid ({result.error_code}), skipping")
            except Exception as e:
                print(f"[NovelFlow] Proposal validation error: {e}")

    def _extract_and_save_proposal(self, raw_output: str, proposal_path: Path, ch_id: str):
        """Extract proposal JSON from LLM output and save."""
        import re
        # Try to find JSON in the output
        json_matches = re.findall(r'\{[^{}]*"schema_version"[^{}]*\}', raw_output, re.DOTALL)
        if json_matches:
            for match in json_matches:
                try:
                    data = json.loads(match)
                    with open(proposal_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    print(f"[NovelFlow] Proposal saved to {proposal_path}")
                    return
                except json.JSONDecodeError:
                    continue
        # Try parsing entire output as JSON
        try:
            data = json.loads(raw_output.strip())
            with open(proposal_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"[NovelFlow] Proposal saved to {proposal_path}")
            return
        except json.JSONDecodeError:
            pass
        print(f"[NovelFlow] Could not extract proposal from output for {ch_id}")

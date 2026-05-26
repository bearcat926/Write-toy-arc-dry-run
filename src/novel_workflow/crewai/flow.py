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

        writer = create_writer()
        auditor = create_auditor()
        extractor = create_extractor()

        for ch_num in range(1, self.state.chapters_total + 1):
            ch_id = f"ch_{ch_num:03d}"
            self.state.current_chapter = ch_num
            print(f"\n[NovelFlow] === Chapter {ch_id} ===")

            context = self._build_context(root, ch_id)

            # Writer
            print(f"[NovelFlow] Writer starting...")
            writer_result = writer.kickoff(
                f"Write chapter {ch_id} of the story.\n\n"
                f"Story context:\n{context}\n\n"
                f"IMPORTANT: You MUST use the write_draft tool to save your chapter. "
                f"Save to: arcs/{self.state.arc_id}/drafts/{ch_id}.md"
            )
            # Fallback: if tool wasn't called, save output directly
            draft_path = root / "arcs" / self.state.arc_id / "drafts" / f"{ch_id}.md"
            if not draft_path.exists():
                print(f"[NovelFlow] Tool not called, saving writer output directly")
                draft_path.parent.mkdir(parents=True, exist_ok=True)
                content = writer_result.raw if hasattr(writer_result, 'raw') else str(writer_result)
                with open(draft_path, "w", encoding="utf-8") as f:
                    f.write(content)

            # Auditor
            draft_content = draft_path.read_text(encoding="utf-8", errors="replace") if draft_path.exists() else "(no draft)"
            print(f"[NovelFlow] Auditor starting...")
            auditor_result = auditor.kickoff(
                f"Review chapter {ch_id} for continuity issues.\n\n"
                f"Draft:\n{draft_content}\n\n"
                f"Story context:\n{context}\n\n"
                f"IMPORTANT: You MUST use the write_review tool to save your review. "
                f"Save to: arcs/{self.state.arc_id}/reviews/{ch_id}_review.md"
            )
            # Fallback
            review_path = root / "arcs" / self.state.arc_id / "reviews" / f"{ch_id}_review.md"
            if not review_path.exists():
                print(f"[NovelFlow] Tool not called, saving auditor output directly")
                review_path.parent.mkdir(parents=True, exist_ok=True)
                content = auditor_result.raw if hasattr(auditor_result, 'raw') else str(auditor_result)
                with open(review_path, "w", encoding="utf-8") as f:
                    f.write(content)

            # Extractor
            review_content = review_path.read_text(encoding="utf-8", errors="replace") if review_path.exists() else "(no review)"
            print(f"[NovelFlow] Extractor starting...")
            extractor_result = extractor.kickoff(
                f"Extract narrative facts from chapter {ch_id}.\n\n"
                f"Draft:\n{draft_content}\n\n"
                f"Review:\n{review_content}\n\n"
                f"IMPORTANT: You MUST use the write_proposal tool to save proposals as JSON to: "
                f"arcs/{self.state.arc_id}/proposals/{ch_id}_ledger_update_proposal.json\n\n"
                f"Each proposal must include: schema_version, claim, source_layer, source_artifact, evidence, confidence, target_ledger, operation, proposed_change."
            )
            # Fallback: extract proposal from output
            proposal_path = root / "arcs" / self.state.arc_id / "proposals" / f"{ch_id}_ledger_update_proposal.json"
            if not proposal_path.exists():
                print(f"[NovelFlow] Tool not called, extracting proposal from output")
                self._extract_proposal_from_output(extractor_result, proposal_path, ch_id)

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

    def _extract_proposal_from_output(self, result, proposal_path: Path, ch_id: str):
        """Extract proposal JSON from Agent output when tool wasn't called."""
        import re
        raw = result.raw if hasattr(result, 'raw') else str(result)
        # Try to find JSON in the output
        json_matches = re.findall(r'\{[^{}]*"schema_version"[^{}]*\}', raw, re.DOTALL)
        if json_matches:
            for match in json_matches:
                try:
                    data = json.loads(match)
                    proposal_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(proposal_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    print(f"[NovelFlow] Extracted proposal from output for {ch_id}")
                    return
                except json.JSONDecodeError:
                    continue
        # If no valid JSON found, create a minimal proposal
        print(f"[NovelFlow] Could not extract proposal from output for {ch_id}")

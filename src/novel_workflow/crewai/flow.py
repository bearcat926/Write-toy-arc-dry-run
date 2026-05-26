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
            writer.kickoff(
                f"Write chapter {ch_id} of the story.\n\n"
                f"Story context:\n{context}\n\n"
                f"Write the draft to: arcs/{self.state.arc_id}/drafts/{ch_id}.md"
            )

            # Auditor
            draft_path = root / "arcs" / self.state.arc_id / "drafts" / f"{ch_id}.md"
            draft_content = draft_path.read_text() if draft_path.exists() else "(no draft)"
            print(f"[NovelFlow] Auditor starting...")
            auditor.kickoff(
                f"Review chapter {ch_id} for continuity issues.\n\n"
                f"Draft:\n{draft_content}\n\n"
                f"Story context:\n{context}\n\n"
                f"Write review to: arcs/{self.state.arc_id}/reviews/{ch_id}_review.md"
            )

            # Extractor
            review_path = root / "arcs" / self.state.arc_id / "reviews" / f"{ch_id}_review.md"
            review_content = review_path.read_text() if review_path.exists() else "(no review)"
            print(f"[NovelFlow] Extractor starting...")
            extractor.kickoff(
                f"Extract narrative facts from chapter {ch_id}.\n\n"
                f"Draft:\n{draft_content}\n\n"
                f"Review:\n{review_content}\n\n"
                f"Write proposals to: arcs/{self.state.arc_id}/proposals/{ch_id}_ledger_update_proposal.json\n\n"
                f"Each proposal must include: schema_version, claim, source_layer, source_artifact, evidence, confidence, target_ledger, operation, proposed_change."
            )

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
                data = json.loads(proposal_path.read_text())
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
            parts.append(f"## Approved Outline\n{canon_outline.read_text()}")

        for ledger_file in (root / "ledgers").glob("*.json"):
            parts.append(f"## Ledger: {ledger_file.stem}\n{ledger_file.read_text()}")

        aws_path = root / "arcs" / self.state.arc_id / "arc_working_state.json"
        if aws_path.exists():
            parts.append(f"## Arc Working State\n{aws_path.read_text()}")

        for prev_ch in range(1, int(ch_id.split("_")[1])):
            prev_path = root / "arcs" / self.state.arc_id / "drafts" / f"ch_{prev_ch:03d}.md"
            if prev_path.exists():
                parts.append(f"## Previous Chapter ch_{prev_ch:03d}\n{prev_path.read_text()}")

        return "\n\n".join(parts) if parts else "(empty project)"

    def _validate_and_merge(self, root: Path, ch_id: str,
                            aws_mgr: ArcWorkingStateManager,
                            proposal_validator: ProposalValidator):
        """System script: validate proposal and merge into arc_working_state."""
        proposal_path = root / "arcs" / self.state.arc_id / "proposals" / f"{ch_id}_ledger_update_proposal.json"
        if not proposal_path.exists():
            print(f"[NovelFlow] No proposal for {ch_id}, skipping merge")
            return

        data = json.loads(proposal_path.read_text())
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

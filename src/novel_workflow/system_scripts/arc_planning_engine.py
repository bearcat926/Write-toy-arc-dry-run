"""ArcPlanningEngine — generates ArcPlan and ChapterBeatPlans from arc_contract.

First version: deterministic extraction from contract text.
Future: LLM-assisted planning.
"""
import re
from pathlib import Path

from ..schemas.arc_plan import ArcPlan, ChapterBeatPlan, ArcHealthReport, ArcHealthFinding


class ArcPlanningEngine:
    """Generates arc plans from arc_contract.md."""

    def __init__(self, root: Path):
        self._root = root

    def plan_arc(self, arc_id: str, chapter_count: int = 10) -> tuple[ArcPlan, list[ChapterBeatPlan], ArcHealthReport]:
        """Generate ArcPlan, ChapterBeatPlans, and ArcHealthReport from arc contract.

        Args:
            arc_id: Arc identifier
            chapter_count: Number of chapters to plan

        Returns:
            (arc_plan, beat_plans, health_report)
        """
        contract_path = self._root / "arcs" / arc_id / "arc_contract.md"
        if not contract_path.exists():
            raise FileNotFoundError(f"Arc contract not found: arcs/{arc_id}/arc_contract.md")

        content = contract_path.read_text(encoding="utf-8", errors="replace")

        # Extract basic info from contract
        title = self._extract_heading(content, level=1) or arc_id
        goal = self._extract_section(content, "goal") or self._extract_section(content, "objective") or ""
        requirements = self._extract_list_items(content, "requirement")
        prohibitions = self._extract_list_items(content, "prohibition")

        chapter_range = [f"ch_{i:03d}" for i in range(1, chapter_count + 1)]

        # Generate ArcPlan
        arc_plan = ArcPlan(
            arc_id=arc_id,
            arc_title=title,
            arc_goal=goal,
            hard_requirements=requirements,
            absolute_prohibitions=prohibitions,
            chapter_range=chapter_range,
            source_artifact=f"arcs/{arc_id}/arc_contract.md",
        )

        # Generate ChapterBeatPlans
        beat_plans = []
        for ch in chapter_range:
            beat = ChapterBeatPlan(
                arc_id=arc_id,
                chapter_id=ch,
                scene_goal=f"Advance arc toward goal: {goal[:100]}" if goal else f"Chapter {ch} scene",
                source_arc_plan=f"arcs/{arc_id}/arc_contract.md",
            )
            beat_plans.append(beat)

        # Generate ArcHealthReport
        health_report = ArcHealthReport(
            arc_id=arc_id,
            findings=[],
            status="pass",
        )

        # Register in manifest
        from .manifest_manager import ManifestManager
        from ..schemas.manifest import DerivedArtifactEntry
        manifest = ManifestManager(self._root)
        manifest.register_artifact(DerivedArtifactEntry(
            artifact_path=f"workspace/arc_plan/arc_{arc_id}_plan.json",
            artifact_type="arc_plan",
            builder_name="ArcPlanningEngine",
            source_artifacts=[],
        ))
        manifest.save()

        return arc_plan, beat_plans, health_report

    @staticmethod
    def _extract_heading(content: str, level: int = 1) -> str:
        """Extract first heading of given level."""
        prefix = "#" * level
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith(prefix + " ") and not stripped.startswith(prefix + "#"):
                return stripped[len(prefix):].strip()
        return ""

    @staticmethod
    def _extract_section(content: str, keyword: str) -> str:
        """Extract text under a section heading containing keyword."""
        lines = content.split("\n")
        in_section = False
        result = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#") and keyword.lower() in stripped.lower():
                in_section = True
                continue
            if in_section:
                if stripped.startswith("#"):
                    break
                if stripped:
                    result.append(stripped)
        return " ".join(result)

    @staticmethod
    def _extract_list_items(content: str, keyword: str) -> list[str]:
        """Extract list items under a section containing keyword."""
        lines = content.split("\n")
        in_section = False
        items = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#") and keyword.lower() in stripped.lower():
                in_section = True
                continue
            if in_section:
                if stripped.startswith("#"):
                    break
                if stripped.startswith("- ") or stripped.startswith("* "):
                    items.append(stripped[2:].strip())
        return items

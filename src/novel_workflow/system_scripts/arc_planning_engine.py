"""ArcPlanningEngine — generates ArcPlan, ChapterBeatPlans, and ArcHealthReport.

TEMP.md §8.2: plan_arc() must be pure (generate objects only).
TEMP.md §8.3: ensure_arc_artifacts() handles persistence.
"""
from pathlib import Path

from ..schemas.arc_plan import ArcPlan, ChapterBeatPlan, ArcHealthReport
from .artifact_writer import ArtifactWriter


class ArcPlanningEngine:
    """Generates and persists arc planning artifacts."""

    def __init__(self, root: Path):
        self._root = root

    def plan_arc(self, arc_id: str, chapter_count: int = 10) -> tuple[ArcPlan, list[ChapterBeatPlan], ArcHealthReport]:
        """Pure function: generate planning objects. No side effects."""
        contract_path = self._root / "arcs" / arc_id / "arc_contract.md"
        if not contract_path.exists():
            raise FileNotFoundError(f"Arc contract not found: arcs/{arc_id}/arc_contract.md")

        content = contract_path.read_text(encoding="utf-8", errors="replace")

        title = self._extract_heading(content, level=1) or arc_id
        goal = self._extract_section(content, "goal") or self._extract_section(content, "objective") or ""
        requirements = self._extract_list_items(content, "requirement")
        prohibitions = self._extract_list_items(content, "prohibition")

        chapter_range = [f"ch_{i:03d}" for i in range(1, chapter_count + 1)]

        arc_plan = ArcPlan(
            arc_id=arc_id,
            arc_title=title,
            arc_goal=goal,
            hard_requirements=requirements,
            absolute_prohibitions=prohibitions,
            chapter_range=chapter_range,
            source_artifact=f"arcs/{arc_id}/arc_contract.md",
        )

        beat_plans = []
        for ch in chapter_range:
            beat = ChapterBeatPlan(
                arc_id=arc_id,
                chapter_id=ch,
                scene_goal=f"Advance arc toward goal: {goal[:100]}" if goal else f"Chapter {ch} scene",
                source_arc_plan=f"arcs/{arc_id}/arc_contract.md",
            )
            beat_plans.append(beat)

        health_report = ArcHealthReport(
            arc_id=arc_id,
            findings=[],
            status="pass",
        )

        return arc_plan, beat_plans, health_report

    def ensure_arc_artifacts(
        self,
        *,
        arc_id: str,
        chapter_count: int,
        runtime_id: str = "",
        required: bool = False,
    ) -> dict:
        """Generate and persist arc artifacts. Returns persisted paths."""
        arc_plan, beat_plans, health_report = self.plan_arc(arc_id, chapter_count)
        writer = ArtifactWriter(self._root)

        source = [f"arcs/{arc_id}/arc_contract.md"]

        results = {}

        # Persist ArcPlan
        plan_path = f"workspace/arc_plan/{arc_id}_plan.json"
        r = writer.write_json_artifact(
            rel_path=plan_path,
            artifact_type="arc_plan",
            builder_name="ArcPlanningEngine",
            payload=arc_plan,
            source_artifacts=source,
            runtime_id=runtime_id,
            required=required,
        )
        results["arc_plan"] = r

        # Persist ChapterBeatPlans
        for beat in beat_plans:
            beat_path = f"workspace/arc_plan/{arc_id}_{beat.chapter_id}_beat_plan.json"
            r = writer.write_json_artifact(
                rel_path=beat_path,
                artifact_type="chapter_beat_plan",
                builder_name="ArcPlanningEngine",
                payload=beat,
                source_artifacts=source,
                runtime_id=runtime_id,
                required=required,
            )
            results[beat.chapter_id] = r

        # Persist HealthReport
        health_path = f"workspace/arc_plan/{arc_id}_health_report.json"
        r = writer.write_json_artifact(
            rel_path=health_path,
            artifact_type="arc_health_report",
            builder_name="ArcPlanningEngine",
            payload=health_report,
            source_artifacts=source,
            runtime_id=runtime_id,
            required=required,
        )
        results["health_report"] = r

        return results

    @staticmethod
    def _extract_heading(content: str, level: int = 1) -> str:
        prefix = "#" * level + " "
        for line in content.split("\n"):
            if line.strip().startswith(prefix):
                return line.strip()[len(prefix):].strip()
        return ""

    @staticmethod
    def _extract_section(content: str, keyword: str) -> str:
        lines = content.split("\n")
        capture = False
        result = []
        for line in lines:
            if line.lower().startswith(f"#") and keyword.lower() in line.lower():
                capture = True
                continue
            if capture and line.startswith("#"):
                break
            if capture:
                result.append(line)
        return "\n".join(result).strip()

    @staticmethod
    def _extract_list_items(content: str, keyword: str) -> list[str]:
        section = ArcPlanningEngine._extract_section(content, keyword)
        items = []
        for line in section.split("\n"):
            line = line.strip()
            if line.startswith("- ") or line.startswith("* "):
                items.append(line[2:].strip())
        return items

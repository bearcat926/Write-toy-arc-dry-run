"""RebuildDAG — defines rebuild dependency order at three levels.

PatchB B-P0-04: Rebuild DAG completeness.
Minimal: summary only
Recommended: summary → graph → lifecycle
Complete: summary → graph → lifecycle → drift → arc → beat → trace
"""

# Three DAG levels
MINIMAL_DAG = ["summary"]

RECOMMENDED_DAG = ["summary", "graph", "lifecycle"]

COMPLETE_DAG = ["summary", "graph", "lifecycle", "drift", "arc_plan", "beat_plan", "trace"]


class RebuildDAG:
    """Defines rebuild dependency order."""

    @staticmethod
    def get_order(level: str = "complete") -> list[str]:
        """Get rebuild order for the specified level."""
        if level == "minimal":
            return list(MINIMAL_DAG)
        elif level == "recommended":
            return list(RECOMMENDED_DAG)
        else:
            return list(COMPLETE_DAG)

    @staticmethod
    def get_downstream(artifact_type: str, level: str = "complete") -> list[str]:
        """Get all artifacts that depend on the given type."""
        order = RebuildDAG.get_order(level)
        if artifact_type not in order:
            return []
        idx = order.index(artifact_type)
        return order[idx + 1:]

    @staticmethod
    def validate_order(rebuilt: list[str], level: str = "complete") -> bool:
        """Validate that rebuild was done in correct dependency order."""
        expected = RebuildDAG.get_order(level)
        seen = set()
        for artifact_type in rebuilt:
            if artifact_type in expected:
                deps = set()
                idx = expected.index(artifact_type)
                for dep in expected[:idx]:
                    deps.add(dep)
                if not deps.issubset(seen):
                    return False
                seen.add(artifact_type)
        return True

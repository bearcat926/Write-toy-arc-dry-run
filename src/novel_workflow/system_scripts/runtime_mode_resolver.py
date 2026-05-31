"""RuntimeModeResolver — resolves three independent mode axes from env/config.

TEMP.md §4.2: Resolves context, arc, and auditor modes independently.
"""
import os

from ..schemas.runtime_modes import (
    RuntimeContextMode,
    ArcRuntimeMode,
    AuditorRuntimeMode,
    RuntimeModes,
)


class RuntimeModeResolver:
    """Resolves runtime modes from environment variables."""

    def resolve(self) -> RuntimeModes:
        return RuntimeModes(
            context_mode=RuntimeContextMode(
                os.getenv("NOVEL_WORKFLOW_CONTEXT_MODE", "legacy")
            ),
            arc_mode=ArcRuntimeMode(
                os.getenv("NOVEL_WORKFLOW_ARC_MODE", "arc_off")
            ),
            auditor_mode=AuditorRuntimeMode(
                os.getenv("NOVEL_WORKFLOW_AUDITOR_MODE", "auditor_off")
            ),
        )

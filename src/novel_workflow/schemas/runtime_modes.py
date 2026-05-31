"""Runtime mode definitions — three independent mode axes.

TEMP.md §4: Context, Arc, and Auditor modes must be separate.
"""
import os
from dataclasses import dataclass
from enum import StrEnum


class RuntimeContextMode(StrEnum):
    LEGACY = "legacy"
    RETRIEVAL_SHADOW = "retrieval_shadow"
    RETRIEVAL_ACTIVE = "retrieval_active"


class ArcRuntimeMode(StrEnum):
    OFF = "arc_off"
    SHADOW = "arc_shadow"
    DUAL_RUN = "arc_dual_run"
    ACTIVE = "arc_active"


class AuditorRuntimeMode(StrEnum):
    OFF = "auditor_off"
    SHADOW = "auditor_shadow"
    DUAL_RUN = "auditor_dual_run"
    ENFORCE = "auditor_enforce"


@dataclass(frozen=True)
class RuntimeModes:
    context_mode: RuntimeContextMode
    arc_mode: ArcRuntimeMode
    auditor_mode: AuditorRuntimeMode

    @property
    def active_manifest_required(self) -> bool:
        return (
            self.context_mode == RuntimeContextMode.RETRIEVAL_ACTIVE
            or self.arc_mode == ArcRuntimeMode.ACTIVE
            or self.auditor_mode == AuditorRuntimeMode.ENFORCE
        )

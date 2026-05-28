"""Phase 2 metadata — tracks derived data versions and rebuild state."""
from .common import SchemaVersioned, Timestamped
from .enums import ProtocolVersion


class Phase2Meta(SchemaVersioned, Timestamped):
    phase2_data_version: str = "1.0"
    protocol_version: ProtocolVersion = ProtocolVersion.PHASE2_V1
    generated_by_commit: str = ""
    artifact_versions: dict[str, str] = {}
    compatible_summary_versions: list[str] = ["1.0"]
    compatible_retrieval_versions: list[str] = ["1.0"]
    compatible_trace_versions: list[str] = ["1.0"]
    derived_rebuild_required: bool = False
    last_rebuild_reason: str = ""

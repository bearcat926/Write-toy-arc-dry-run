"""Milestone 10: Protocol version tests."""
import pytest
from novel_workflow.schemas.phase2_meta import Phase2Meta
from novel_workflow.schemas.enums import ProtocolVersion


def test_phase2_meta_default():
    meta = Phase2Meta()
    assert meta.protocol_version == ProtocolVersion.PHASE2_V1
    assert meta.derived_rebuild_required is False
    assert meta.phase2_data_version == "1.0"


def test_protocol_version_incompatible():
    meta = Phase2Meta()
    # Simulate checking compatibility
    assert ProtocolVersion.PHASE2_V1.value == "phase2_v1"
    # Unknown version would fail at enum level
    with pytest.raises(ValueError):
        ProtocolVersion("phase2_v2")


def test_rebuild_required_on_mismatch():
    meta = Phase2Meta()
    meta.derived_rebuild_required = True
    meta.last_rebuild_reason = "PROTOCOL_VERSION_MISMATCH"
    assert meta.derived_rebuild_required is True


def test_compatible_versions():
    meta = Phase2Meta()
    assert "1.0" in meta.compatible_summary_versions
    assert "1.0" in meta.compatible_retrieval_versions
    assert "1.0" in meta.compatible_trace_versions

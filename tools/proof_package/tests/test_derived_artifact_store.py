"""B-01~B-03: DerivedArtifactStore tests.

B-01: DerivedArtifactStoreEntry schema with TEMP.md §8.4 fields
B-02: stage_write → promote_staged flow
B-03: SchemaValidator field-level validation
"""
import pytest
from pathlib import Path
from novel_workflow.schemas.manifest import DerivedArtifactStoreEntry, DerivedArtifactEntry
from novel_workflow.validators.schema_validator import SchemaValidator
from novel_workflow.system_scripts.manifest_manager import ManifestManager


class TestDerivedArtifactStoreEntry:
    """B-01: Artifact type schema."""

    def test_entry_has_required_fields(self):
        entry = DerivedArtifactStoreEntry(
            artifact_id="art_001",
            artifact_type="chapter_summary",
            content_hash="sha256:abc123",
            trace_id="trc_001",
        )
        assert entry.artifact_id == "art_001"
        assert entry.artifact_type == "chapter_summary"
        assert entry.status == "staged"  # default
        assert entry.derived is True

    def test_entry_status_enum(self):
        entry = DerivedArtifactStoreEntry(
            artifact_id="art_002", artifact_type="graph",
        )
        assert entry.status == "staged"
        # Invalid status rejected at construction time
        with pytest.raises(Exception):
            DerivedArtifactStoreEntry(
                artifact_id="art_002b", artifact_type="graph",
                status="invalid_status",
            )

    def test_entry_source_hashes_coercion(self):
        entry = DerivedArtifactStoreEntry(
            artifact_id="art_003", artifact_type="governance",
            source_hashes=["file1.md", "file2.md"],
        )
        assert isinstance(entry.source_hashes, dict)

    def test_entry_generation_id(self):
        entry = DerivedArtifactStoreEntry(
            artifact_id="art_004", artifact_type="retrieval_trace",
            generation_id="gen_001",
        )
        assert entry.generation_id == "gen_001"


class TestSchemaValidatorFields:
    """B-03: Field-level schema validation."""

    def test_validate_derived_store_entry_valid(self):
        validator = SchemaValidator()
        errors = validator.validate_fields("derived_store_entry", {
            "schema_version": "1.0",
            "artifact_id": "art_001",
            "artifact_type": "chapter_summary",
            "status": "staged",
            "derived": True,
        })
        assert errors == []

    def test_validate_missing_required_field(self):
        validator = SchemaValidator()
        errors = validator.validate_fields("derived_store_entry", {
            "schema_version": "1.0",
            "artifact_type": "chapter_summary",
        })
        assert any("artifact_id" in e for e in errors)

    def test_validate_invalid_status(self):
        validator = SchemaValidator()
        errors = validator.validate_fields("derived_store_entry", {
            "schema_version": "1.0",
            "artifact_id": "art_001",
            "artifact_type": "chapter_summary",
            "status": "bogus",
        })
        assert any("INVALID_STATUS" in e for e in errors)

    def test_validate_missing_schema_version_raises(self):
        validator = SchemaValidator()
        with pytest.raises(ValueError, match="MISSING_SCHEMA_VERSION"):
            validator.validate_fields("derived_store_entry", {"artifact_id": "x"})

    def test_validate_governance_report(self):
        validator = SchemaValidator()
        errors = validator.validate_fields("governance_report", {
            "schema_version": "1.0",
            "chapter_id": "ch_001",
            "max_severity": "soft_warning",
            "recommended_action": "approve",
        })
        assert errors == []

    def test_validate_character_drift_finding(self):
        validator = SchemaValidator()
        errors = validator.validate_fields("character_drift_finding", {
            "schema_version": "1.0",
            "finding_id": "f_001",
            "character_id": "char_001",
            "chapter_id": "ch_001",
            "drift_type": "voice_drift",
            "severity": "soft_warning",
            "evidence": "test evidence",
        })
        assert errors == []

    def test_validate_unknown_type_no_error(self):
        validator = SchemaValidator()
        errors = validator.validate_fields("unknown_type", {"schema_version": "1.0"})
        assert errors == []  # No validator registered = no field errors


class TestStagedWriteFlow:
    """B-02: stage_write → promote_staged."""

    def test_stage_write(self, tmp_path):
        mgr = ManifestManager(tmp_path)
        entry = DerivedArtifactStoreEntry(
            artifact_id="art_stage_001",
            artifact_type="chapter_summary",
            content_hash="sha256:def456",
        )
        result = mgr.stage_write(entry)
        assert result.status == "staged"

    def test_stage_write_validates(self, tmp_path):
        mgr = ManifestManager(tmp_path)
        # Missing artifact_id should fail
        with pytest.raises(ValueError, match="validation failed"):
            mgr.stage_write(DerivedArtifactStoreEntry(
                artifact_id="", artifact_type="chapter_summary",
            ))

    def test_promote_staged(self, tmp_path):
        mgr = ManifestManager(tmp_path)
        entry = DerivedArtifactStoreEntry(
            artifact_id="art_promote_001",
            artifact_type="graph",
        )
        mgr.stage_write(entry)
        result = mgr.promote_staged("art_promote_001")
        assert result is True

    def test_promote_nonexistent(self, tmp_path):
        mgr = ManifestManager(tmp_path)
        result = mgr.promote_staged("nonexistent")
        assert result is False

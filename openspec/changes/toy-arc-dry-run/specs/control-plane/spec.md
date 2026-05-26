## ADDED Requirements

### Requirement: Schema validator rejects unknown or missing schema_version
The system SHALL reject any persistent JSON or Markdown frontmatter that lacks `schema_version` or has an unknown version.

#### Scenario: Missing schema_version
- **WHEN** a JSON artifact is submitted without `schema_version` field
- **THEN** validator returns error `MISSING_SCHEMA_VERSION` and the artifact is rejected

#### Scenario: Unknown schema_version
- **WHEN** a JSON artifact has `schema_version: "99.0"` which is not in the supported version list
- **THEN** validator returns error `UNKNOWN_SCHEMA_VERSION` and the artifact is rejected

#### Scenario: Valid schema_version
- **WHEN** a JSON artifact has `schema_version: "1.0"` which is in the supported version list
- **THEN** validator passes and continues to field-level validation

### Requirement: Gate record validator enforces author_input_evidence
The system SHALL reject any approved gate record that lacks `author_input_evidence` or has empty/whitespace-only evidence.

#### Scenario: Approved gate with empty evidence
- **WHEN** a gate record has `decision: "approved"` and `author_input_evidence: ""`
- **THEN** validator returns error `MISSING_GATE_EVIDENCE`

#### Scenario: Approved gate with auto-generated evidence
- **WHEN** a gate record has `decision: "approved"` and `author_input_evidence` matching the pattern `"auto_*"`
- **THEN** validator returns error `AUTO_GENERATED_GATE_EVIDENCE`

#### Scenario: Approved gate with valid evidence
- **WHEN** a gate record has `decision: "approved"` and `author_input_evidence: "Arc direction aligns with story goals"`
- **THEN** validator passes

#### Scenario: Rejected gate without evidence
- **WHEN** a gate record has `decision: "rejected"` and `author_input_evidence` is empty
- **THEN** validator passes (evidence not required for rejection)

### Requirement: Proposal validator enforces source citation
The system SHALL reject any `ledger_update_proposal` that lacks `source_layer`, `source_artifact`, or `evidence`.

#### Scenario: Proposal missing evidence
- **WHEN** a proposal has `source_layer` and `source_artifact` but no `evidence`
- **THEN** validator returns error `MISSING_EVIDENCE` with error category `schema_repairable`

#### Scenario: Proposal with evidence pointing to nonexistent artifact
- **WHEN** a proposal has `source_artifact: "arcs/arc_001/drafts/ch_999.md"` but that file does not exist
- **THEN** validator returns error `INVALID_SOURCE_ARTIFACT` with error category `semantic_invalid`

#### Scenario: Valid proposal
- **WHEN** a proposal has all required fields and `source_artifact` points to an existing file
- **THEN** validator passes

### Requirement: Proposal validator enforces operation enum per target_ledger
The system SHALL validate that `operation` field matches the allowed operations for the specified `target_ledger`.

#### Scenario: timeline with invalid operation
- **WHEN** a proposal has `target_ledger: "timeline"` and `operation: "delete_event"`
- **THEN** validator returns error `INVALID_OPERATION` (timeline only allows `append_event | correction`)

#### Scenario: foreshadowing with valid operation
- **WHEN** a proposal has `target_ledger: "foreshadowing"` and `operation: "introduce_foreshadow"`
- **THEN** operation validation passes

### Requirement: Emergency pause detector classifies pause type
The system SHALL classify each pause into `hard_pause`, `creative_review`, or `soft_warning`.

#### Scenario: Path traversal triggers hard_pause
- **WHEN** path safety guard detects `../` in a write path
- **THEN** pause type is `hard_pause`

#### Scenario: POV knowledge violation triggers creative_review
- **WHEN** a proposal suggests a character knows information outside their POV boundary
- **THEN** pause type is `creative_review`

#### Scenario: Weak hook triggers soft_warning
- **WHEN** reviewer reports no reader hook in a chapter
- **THEN** pause type is `soft_warning`

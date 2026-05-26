## ADDED Requirements

### Requirement: Fixture-based end-to-end test covers all DoD scenarios
The system SHALL provide pytest fixtures that simulate a 3-chapter toy arc and verify all 10 DoD items.

#### Scenario: Happy path end-to-end
- **WHEN** fixture initializes a toy project, creates direction gate, arc_start gate, 3 chapters with draft/review/proposal, arc_end gate, and atomic apply
- **THEN** all steps complete without error and canon/manuscript + ledgers are updated correctly

#### Scenario: DoD #1 - Agent write rejection
- **WHEN** fixture attempts to write to `canon/` using an Agent role
- **THEN** write is rejected with error `AGENT_WRITE_DENIED`

#### Scenario: DoD #2 - Gate evidence enforcement
- **WHEN** fixture creates a gate record with `decision: "approved"` and empty `author_input_evidence`
- **THEN** gate validator rejects it

#### Scenario: DoD #7 - Atomic apply rollback
- **WHEN** fixture triggers a failure mid-apply (between canonicalize and ledger_diff)
- **THEN** all pre-apply state is restored

#### Scenario: DoD #10 - Path traversal rejection
- **WHEN** fixture submits a write path with `../`
- **THEN** path safety guard rejects it

### Requirement: Dry run produces observable artifacts
The system SHALL generate all expected artifacts during dry run: gate records, drafts, reviews, proposals, arc_working_state, ledger_diff, canon_diff, apply_record, pause_report, progress.jsonl.

#### Scenario: All artifacts exist after dry run
- **WHEN** complete 3-chapter dry run finishes
- **THEN** all expected files exist in the toy_project directory with valid schema_version

### Requirement: progress.jsonl records all system events
The system SHALL log every significant system event to `workspace/progress.jsonl` with schema_version and `contains_narrative_fact: false`.

#### Scenario: Event logging
- **WHEN** a proposal is validated
- **THEN** a progress entry is written with `event_type`, `timestamp`, `artifact_path`, and `contains_narrative_fact: false`

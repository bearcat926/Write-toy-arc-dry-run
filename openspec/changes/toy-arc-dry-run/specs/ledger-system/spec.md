## ADDED Requirements

### Requirement: Ledger diff generator produces valid diff from merged proposals
The system SHALL generate a `ledger_diff.json` from validated proposals merged during an arc, with per-ledger merge strategies.

#### Scenario: Timeline append-only
- **WHEN** 3 chapters produce timeline proposals with `operation: "append_event"`
- **THEN** ledger_diff contains 3 appended events in order, no deletions or modifications

#### Scenario: Foreshadowing state machine
- **WHEN** ch_001 introduces a foreshadow and ch_003 pays it off
- **THEN** ledger_diff contains `introduce_foreshadow` followed by `pay_off_foreshadow` with valid state transitions

#### Scenario: Foreshadowing invalid transition rejected
- **WHEN** a proposal attempts `paid_off → introduced`
- **THEN** diff generator returns error `INVALID_FORESHADOW_TRANSITION`

### Requirement: Canonicalizer moves draft to canon/manuscript
The system SHALL move approved draft content from `arcs/arc_XXX/drafts/ch_YYY.md` to `canon/manuscript/ch_YYY.md` during atomic apply.

#### Scenario: Successful canonicalization
- **WHEN** arc_end gate is approved and atomic apply runs
- **THEN** `ch_001.md`, `ch_002.md`, `ch_003.md` appear in `canon/manuscript/` and drafts remain in arc directory

### Requirement: Atomic apply is all-or-nothing
The system SHALL apply canonicalize draft + ledger_diff + canon_diff as a single atomic operation.

#### Scenario: All succeed
- **WHEN** canonicalize, ledger_diff apply, and canon_diff apply all succeed
- **THEN** all changes are persisted and apply_record is written

#### Scenario: Partial failure triggers rollback
- **WHEN** canonicalize succeeds but ledger_diff apply fails
- **THEN** all changes are rolled back to pre-apply state using snapshot

### Requirement: Consumed ledger_diff cannot be reapplied
The system SHALL mark applied ledger_diff as consumed and reject duplicate apply attempts.

#### Scenario: Duplicate apply rejected
- **WHEN** the same `ledger_diff.json` (same target_artifact + same diff hash) is submitted for apply a second time
- **THEN** apply manager returns error `ALREADY_CONSUMED`

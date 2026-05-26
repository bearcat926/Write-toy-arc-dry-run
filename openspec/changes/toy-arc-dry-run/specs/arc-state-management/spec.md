## ADDED Requirements

### Requirement: arc_working_state initialized from canon and ledgers
The system SHALL initialize `arc_working_state.json` from current canon and ledger state when an arc starts.

#### Scenario: Fresh arc initialization
- **WHEN** arc_start gate is approved
- **THEN** `arc_working_state.json` is created with current canon facts and ledger snapshots, all entries having `status: "working_accepted"`

### Requirement: Valid proposals merged into arc_working_state by system script
The system SHALL merge validated proposals into `arc_working_state` after chapter review passes and proposal validation succeeds.

#### Scenario: Successful merge
- **WHEN** ch_001 passes review and its proposal validates
- **THEN** proposal entries are added to `arc_working_state` with `status: "working_accepted"`, `source_chapter: "ch_001"`, and `approval_scope: "arc_internal_only"`

#### Scenario: Audit failure blocks merge
- **WHEN** ch_001 review reports blocking issues but proposal validates
- **THEN** proposal is NOT merged into `arc_working_state`

### Requirement: arc_working_state acts as overlay, not override
The system SHALL treat `arc_working_state` as having higher recency but NOT higher authority than canon/ledgers.

#### Scenario: Overlay with conflict detection
- **WHEN** `arc_working_state` has `character_A knows secret_X` but canon says `character_A does not know secret_X`
- **THEN** system detects the conflict and triggers `creative_review` pause

#### Scenario: Overlay without conflict
- **WHEN** `arc_working_state` has a new fact `character_B arrived at location_Y` that does not contradict canon
- **THEN** the new fact is available as arc overlay for subsequent chapters

### Requirement: Rejected arc_working_state entries trigger dependency cascade
The system SHALL propagate rejection to downstream entries that depend on rejected entries.

#### Scenario: Cascade rejection
- **WHEN** `aws_001` (from ch_001) is marked `rejected` and `aws_002` (from ch_002) has `depends_on: ["aws_001"]`
- **THEN** `aws_002` is marked `invalidated_by_rejected_dependency`

#### Scenario: Independent entries survive
- **WHEN** `aws_001` is rejected but `aws_003` has no `depends_on` referencing `aws_001`
- **THEN** `aws_003` retains its current status

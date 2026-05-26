## ADDED Requirements

### Requirement: Path safety guard normalizes and validates all write paths
The system SHALL normalize every write path and validate against an allowlist before any file operation.

#### Scenario: Path traversal rejected
- **WHEN** a write path contains `../`
- **THEN** guard returns error `PATH_TRAVERSAL_REJECTED`

#### Scenario: Absolute path rejected
- **WHEN** a write path starts with `/` or `C:\`
- **THEN** guard returns error `ABSOLUTE_PATH_REJECTED`

#### Scenario: Symlink escape rejected
- **WHEN** a write path resolves via symlink to a location outside the workspace allowlist
- **THEN** guard returns error `SYMLINK_ESCAPE_REJECTED`

#### Scenario: Valid path passes
- **WHEN** a write path is `arcs/arc_001/drafts/ch_001.md` and that directory exists in the allowlist
- **THEN** guard passes and returns the normalized path

### Requirement: File protocol defines canonical project structure
The system SHALL enforce the project directory structure as defined in PLAN.md Section 11.

#### Scenario: canon/manuscript directory exists
- **WHEN** a project is initialized
- **THEN** `canon/manuscript/` directory is created for approved chapter text

#### Scenario: gates directory at project root
- **WHEN** a project is initialized
- **THEN** `gates/direction_gate.json` exists as a project-level gate (not arc-level)

#### Scenario: reports directory contains canon_diff.json location
- **WHEN** an arc is initialized
- **THEN** `arcs/arc_XXX/reports/` directory is created with space for `canon_diff.json`

### Requirement: Plugin write paths default deny
The system SHALL reject any plugin write request to paths not in the explicit plugin allowlist.

#### Scenario: Plugin attempts to write canon
- **WHEN** a plugin requests write to `canon/canon_state.json`
- **THEN** guard returns error `PLUGIN_WRITE_DENIED`

#### Scenario: Plugin writes to allowed path
- **WHEN** a plugin requests write to `inspiration/idea_001.md`
- **THEN** guard passes

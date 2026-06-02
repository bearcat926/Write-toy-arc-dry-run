## Purpose

Ensure Phase 2 baseline generation and Phase 3 entry verification share the
same machine-verifiable commit requirement.

## Requirements

### Requirement: Baseline Commit Must Be Concrete

The Phase 2 test baseline generator SHALL record a concrete git commit when no
explicit commit is provided.

#### Scenario: Default baseline generation resolves git HEAD

- **WHEN** the baseline generator is invoked without `--commit`
- **THEN** it resolves the repository `HEAD`
- **AND** the generated baseline records that commit instead of `unknown`

#### Scenario: Explicit commit remains supported

- **WHEN** the baseline generator is invoked with `--commit <value>`
- **THEN** it records the provided value without invoking git commit discovery

#### Scenario: Git commit cannot be resolved

- **WHEN** no explicit commit is provided
- **AND** git commit discovery fails
- **THEN** baseline generation fails instead of writing `Base Commit: unknown`

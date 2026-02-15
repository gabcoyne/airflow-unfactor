## ADDED Requirements

### Requirement: Lint workflow for code quality
The repository SHALL have a GitHub Actions workflow for linting.

#### Scenario: Ruff check passes
- **WHEN** PR is opened or push to main
- **THEN** ruff check runs on all Python files
- **AND** workflow fails if any linting errors

#### Scenario: Ruff format check
- **WHEN** PR is opened or push to main
- **THEN** ruff format --check runs
- **AND** workflow fails if files need formatting

### Requirement: Operator docs verification workflow
The repository SHALL verify generated operator docs match the registry.

#### Scenario: Docs in sync
- **WHEN** PR modifies provider_mappings.py or operator-coverage.md
- **THEN** regenerate operator-coverage.md
- **AND** verify no diff exists
- **AND** workflow passes

#### Scenario: Docs out of sync
- **WHEN** registry changes but docs not regenerated
- **THEN** workflow fails with actionable error message

### Requirement: Release workflow for PyPI publishing
The repository SHALL automate PyPI releases on version tags.

#### Scenario: Tag triggers release
- **WHEN** tag matching v* is pushed
- **THEN** build package with `python -m build`
- **AND** publish to PyPI using trusted publishing

#### Scenario: Release uses correct environment
- **WHEN** release workflow runs
- **THEN** uses 'release' environment for secrets isolation
- **AND** uses OIDC for PyPI authentication (no API tokens)

### Requirement: Type checking workflow (optional)
The repository MAY have a GitHub Actions workflow for type checking.

#### Scenario: Type check with pyright
- **WHEN** PR is opened or push to main
- **THEN** pyright runs on src/ directory
- **AND** workflow reports type errors but doesn't fail (informational)

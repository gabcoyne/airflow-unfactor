## ADDED Requirements

### Requirement: Generate coverage documentation from registry
The system SHALL generate operator coverage documentation from OPERATOR_MAPPINGS registry.

#### Scenario: Build time generation
- **WHEN** docs are built (CI or local)
- **THEN** docs/operator-coverage.md is generated from current registry

#### Scenario: Single source of truth
- **WHEN** operator is added to OPERATOR_MAPPINGS
- **THEN** it automatically appears in generated documentation

### Requirement: Categorize operators by provider
The coverage matrix SHALL group operators by provider for easy navigation.

#### Scenario: AWS operators grouped
- **WHEN** documentation is generated
- **THEN** AWS operators appear under "## AWS Operators" section

#### Scenario: GCP operators grouped
- **WHEN** documentation is generated
- **THEN** GCP operators appear under "## GCP Operators" section

#### Scenario: Database operators grouped
- **WHEN** documentation is generated
- **THEN** Database operators appear under "## Database Operators" section

### Requirement: Show conversion status
The coverage matrix SHALL show conversion status for each operator.

#### Scenario: Supported operators marked
- **WHEN** operator has full mapping in registry
- **THEN** shows "✅ Supported" with Prefect equivalent

#### Scenario: Partial support indicated
- **WHEN** operator mapping has notes about limitations
- **THEN** shows "⚠️ Partial" with limitation description

#### Scenario: Unknown operators listed
- **WHEN** operator is not in registry
- **THEN** not listed (unknown operators generate stubs at runtime)

### Requirement: Include package requirements
The coverage matrix SHALL show required pip packages for each operator.

#### Scenario: Prefect integration shown
- **WHEN** operator needs prefect-aws
- **THEN** documentation shows "Package: prefect-aws"

#### Scenario: Multiple packages shown
- **WHEN** operator needs multiple packages
- **THEN** documentation lists all required packages

### Requirement: CI validation
The CI pipeline SHALL verify generated docs match registry.

#### Scenario: Docs up to date
- **WHEN** CI runs and docs match registry
- **THEN** CI passes

#### Scenario: Docs out of date
- **WHEN** CI runs and docs don't match registry
- **THEN** CI fails with instruction to regenerate

### Requirement: Provide search/filter guidance
The coverage matrix SHALL include guidance for finding operators.

#### Scenario: Include search tips
- **WHEN** user views documentation
- **THEN** page includes Ctrl+F search guidance

#### Scenario: Link to unknown operator handling
- **WHEN** user doesn't find their operator
- **THEN** page links to custom operator documentation

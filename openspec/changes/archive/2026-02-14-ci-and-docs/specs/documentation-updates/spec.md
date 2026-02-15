## MODIFIED Requirements

### Requirement: Index page reflects current features
The docs/index.md SHALL accurately describe all available features.

#### Scenario: Validation tool mentioned
- **WHEN** user reads index page
- **THEN** validation tool is listed in features
- **AND** links to validation documentation

#### Scenario: Provider operators highlighted
- **WHEN** user reads index page
- **THEN** "35+ Provider Operators" mentioned
- **AND** lists major providers (AWS, GCP, Azure, Databricks, dbt)

#### Scenario: Metrics module mentioned
- **WHEN** user reads index page
- **THEN** conversion metrics feature described
- **AND** links to metrics documentation

#### Scenario: Enhanced runbooks mentioned
- **WHEN** user reads index page
- **THEN** runbook enhancements described
- **AND** mentions work pools, automations, Block setup

### Requirement: Operator mapping references generated docs
The docs/operator-mapping.md SHALL reference the generated coverage matrix.

#### Scenario: Links to generated docs
- **WHEN** user reads operator-mapping.md
- **THEN** includes link to operator-coverage.md
- **AND** explains it's auto-generated from registry

#### Scenario: Instructions for adding operators
- **WHEN** user wants to add new operator support
- **THEN** operator-mapping.md explains the process
- **AND** references scripts/generate_operator_docs.py

### Requirement: Troubleshooting covers validation issues
The docs/troubleshooting.md SHALL include validation-specific issues.

#### Scenario: Task count mismatch documented
- **WHEN** user encounters task count mismatch
- **THEN** troubleshooting explains DummyOperator exclusion
- **AND** provides guidance on reviewing skipped tasks

#### Scenario: Dependency mismatch documented
- **WHEN** user encounters dependency graph mismatch
- **THEN** troubleshooting explains isomorphism check
- **AND** suggests reviewing complex dependency patterns

#### Scenario: Data flow warnings documented
- **WHEN** user sees XCom data flow warnings
- **THEN** troubleshooting explains return/parameter conversion
- **AND** provides refactoring guidance

#### Scenario: Low confidence score documented
- **WHEN** user sees low confidence score
- **THEN** troubleshooting explains factors affecting score
- **AND** suggests manual review for complex DAGs

### Requirement: Navigation includes new sections
The documentation site navigation SHALL include tools and guides sections.

#### Scenario: Tools section visible
- **WHEN** user views documentation navigation
- **THEN** "Tools" section appears
- **AND** includes Validation and Metrics links

#### Scenario: Guides section visible
- **WHEN** user views documentation navigation
- **THEN** "Guides" section appears
- **AND** includes Enterprise Migration and Prefect Cloud links

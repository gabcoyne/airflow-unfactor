## ADDED Requirements

### Requirement: Define canonical response schema
The system SHALL define a JSON Schema for all MCP tool responses (analyze, convert, validate, explain).

#### Scenario: Schema file location
- **WHEN** schema is published
- **THEN** it exists at `schemas/conversion-output.json`

#### Scenario: Schema covers analyze response
- **WHEN** analyze tool returns
- **THEN** response matches schema with dag_id, operators, dependencies, complexity_score, etc.

#### Scenario: Schema covers convert response
- **WHEN** convert tool returns
- **THEN** response matches schema with flow_code, imports, warnings, mapping, runbook, etc.

### Requirement: Version the schema
The system SHALL include version information in the schema.

#### Scenario: Schema has version
- **WHEN** schema is read
- **THEN** it includes `$schema` and custom `version` field

#### Scenario: Version follows semver
- **WHEN** schema changes
- **THEN** version increments following semver (major for breaking, minor for additions)

### Requirement: Document all response fields
The system SHALL document every field in the response schema with descriptions.

#### Scenario: Field descriptions
- **WHEN** schema field is defined
- **THEN** it includes `description` explaining purpose and format

#### Scenario: Required vs optional fields
- **WHEN** schema is defined
- **THEN** `required` array lists mandatory fields, others are optional

### Requirement: Include validation examples
The system SHALL provide example valid responses for each tool.

#### Scenario: Analyze example
- **WHEN** schema documentation is read
- **THEN** includes example analyze response that validates against schema

#### Scenario: Convert example
- **WHEN** schema documentation is read
- **THEN** includes example convert response that validates against schema

### Requirement: Define external_context schema
The system SHALL define the schema for `external_context` field from external MCP enrichment.

#### Scenario: External context structure
- **WHEN** external_context is present
- **THEN** it follows structure: `{provider: {ok, tool, query, elapsed_ms, result|error}}`

#### Scenario: External context is optional
- **WHEN** include_external_context=false
- **THEN** external_context field is omitted (not null)

### Requirement: Define warning structure
The system SHALL define consistent structure for warnings array.

#### Scenario: Warning has message and category
- **WHEN** warning is emitted
- **THEN** it includes `message` (string) and `category` (enum: info, warning, error)

#### Scenario: Warning may have location
- **WHEN** warning relates to specific code
- **THEN** it may include `line` and `column` fields

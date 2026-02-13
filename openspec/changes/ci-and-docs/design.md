# CI/CD and Documentation Design

## GitHub Actions Architecture

### Workflow Structure

```
.github/workflows/
├── test.yml          # Existing - tests + docs build check
├── docs.yml          # Existing - deploy to GitHub Pages
├── lint.yml          # NEW - ruff linting
├── typecheck.yml     # NEW - type checking (optional)
├── operator-docs.yml # NEW - verify operator docs
└── release.yml       # NEW - PyPI publishing
```

### Workflow Dependencies

```
PR/Push to main:
  ├── test.yml (required)
  │   ├── pytest across Python 3.11-3.13
  │   └── docs build verification
  ├── lint.yml (required)
  │   └── ruff check + format
  └── operator-docs.yml (required)
      └── Verify docs/operator-coverage.md matches registry

Push to main only:
  └── docs.yml
      └── Deploy to GitHub Pages

Tag push (v*):
  └── release.yml
      └── Build and publish to PyPI
```

### Lint Workflow Design

```yaml
# .github/workflows/lint.yml
name: Lint

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv python install 3.11
      - run: uv pip install ruff
      - run: ruff check .
      - run: ruff format --check .
```

### Operator Docs Verification Design

```yaml
# .github/workflows/operator-docs.yml
name: Verify Operator Docs

on:
  push:
    branches: [main]
    paths:
      - 'src/airflow_unfactor/converters/provider_mappings.py'
      - 'docs/operator-coverage.md'
      - 'scripts/generate_operator_docs.py'
  pull_request:
    branches: [main]
    paths:
      - 'src/airflow_unfactor/converters/provider_mappings.py'
      - 'docs/operator-coverage.md'
      - 'scripts/generate_operator_docs.py'

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv python install 3.11
      - run: uv pip install -e .
      - name: Generate docs
        run: uv run python scripts/generate_operator_docs.py
      - name: Check for changes
        run: |
          if git diff --exit-code docs/operator-coverage.md; then
            echo "Operator docs are up to date"
          else
            echo "::error::Operator docs are out of sync. Run 'python scripts/generate_operator_docs.py'"
            exit 1
          fi
```

### Release Workflow Design

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    environment: release
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv python install 3.11
      - run: uv pip install build
      - run: python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

## Documentation Structure

### Updated Navigation

```
docs/
├── index.md              # UPDATE: Add validation, metrics, providers
├── getting-started.md    # Existing
├── examples.md           # Existing
├── operator-mapping.md   # UPDATE: Reference operator-coverage.md
├── operator-coverage.md  # Existing (generated)
│
├── tools/                # NEW section
│   ├── validate.md       # NEW: Validation tool guide
│   └── metrics.md        # NEW: Metrics module guide
│
├── conversion/           # Existing section
│   ├── dynamic-mapping.md
│   ├── taskgroups.md
│   ├── trigger-rules.md
│   ├── jinja-templates.md
│   ├── connections.md
│   └── variables.md
│
├── guides/               # NEW section
│   ├── enterprise-migration.md  # NEW: Large-scale patterns
│   └── prefect-cloud.md         # NEW: Cloud integration
│
├── playbooks.md          # Existing
├── convert-reference.md  # Existing
├── testing.md            # Existing
└── troubleshooting.md    # UPDATE: Add validation issues
```

### docs/tools/validate.md Content

```markdown
# Validation Tool

Verify that converted flows maintain behavioral equivalence with original DAGs.

## Overview
- Task count comparison (excludes DummyOperator/EmptyOperator)
- Dependency graph isomorphism check
- XCom to return/parameter data flow validation
- Confidence scoring based on complexity

## Usage
## Examples
## Understanding Results
## Troubleshooting
```

### docs/tools/metrics.md Content

```markdown
# Conversion Metrics

Track and analyze conversion operations for optimization and reporting.

## Enabling Metrics
## Recording Conversions
## Aggregate Statistics
## Exporting Data
## Integration Examples
```

### docs/guides/enterprise-migration.md Content

```markdown
# Enterprise Migration Guide

Patterns and strategies for migrating large DAG portfolios to Prefect.

## Assessment Phase
## Phased Migration Strategy
## Batch Conversion Workflow
## Validation at Scale
## Rollback Planning
## Monitoring Migration Progress
```

### docs/guides/prefect-cloud.md Content

```markdown
# Prefect Cloud Integration

Leverage Prefect Cloud features for production deployments.

## Work Pools and Workers
## Automations for Callbacks
## Concurrency Management
## Secrets and Blocks
## Observability and Alerting
```

## Index Page Updates

Add to the feature list in docs/index.md:

```markdown
## Features

- **Complete Migration** — Handles operators, TaskFlow, sensors, datasets, dynamic mapping, TaskGroups, trigger rules, and Jinja2 templates
- **Validation** — Verify converted flows maintain behavioral equivalence with original DAGs
- **35+ Provider Operators** — AWS, GCP, Azure, Databricks, dbt, and more
- **Conversion Metrics** — Track success rates, operator coverage, and warnings
- **Educational** — Comments explain *why* Prefect does it better
- **Test Generation** — Every migrated flow comes with pytest tests
- **Migration Runbooks** — DAG-specific guidance with work pool, automation, and Block setup
- **AI-Assisted** — Smart analysis with external MCP enrichment from Prefect and Astronomer docs
```

Add new navigation sections:

```markdown
### Tools
- [Validation](tools/validate.md) — Verify conversion correctness
- [Metrics](tools/metrics.md) — Track conversion statistics

### Guides
- [Enterprise Migration](guides/enterprise-migration.md) — Large-scale patterns
- [Prefect Cloud](guides/prefect-cloud.md) — Cloud-specific features
```

## Troubleshooting Updates

Add new section to docs/troubleshooting.md:

```markdown
## Validation Issues

### Task Count Mismatch
### Dependency Graph Mismatch
### Data Flow Warnings
### Low Confidence Scores
```

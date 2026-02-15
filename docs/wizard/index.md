---
layout: page
title: Migration Wizard
permalink: /wizard/
---

# Migration Wizard

The Migration Wizard provides a visual, step-by-step interface for migrating Airflow DAGs to Prefect flows.

## When to Use the Wizard

The wizard is ideal for:

- **Teams new to Prefect** who want guided migration
- **Exploring conversions** before committing to changes
- **Generating complete projects** with best practices baked in
- **Non-technical stakeholders** who need visibility into the migration

For CI/CD integration or scripted migrations, use the [MCP tools](../getting-started.md) directly.

## Features

### Visual DAG Analysis

See your DAG's structure at a glance:
- Operators detected with counts
- Task dependencies visualized
- Complexity score and conversion notes
- Warnings about patterns requiring attention

### Live Code Preview

Preview converted flows before export:
- Side-by-side DAG vs Flow comparison
- Educational comments explaining Prefect patterns
- Generated pytest tests included

### Validation

Verify your conversions maintain behavioral equivalence:
- Task count comparison
- Dependency preservation check
- Data flow pattern validation
- Confidence score (0-100)

### Project Generation

Generate a complete, production-ready project:
- Organized directory structure following PrefectHQ patterns
- prefect.yaml deployment configuration
- Dockerfile and docker-compose.yml (optional)
- GitHub Actions workflow (optional)
- Migration runbook with manual TODOs

### Export Options

Download your migrated project:
- Export as ZIP file
- Copy individual files
- Preview all generated files

## Quick Start

```bash
# Install with UI dependencies
pip install airflow-unfactor[ui]

# Start the wizard
airflow-unfactor --ui

# Open in your browser
open http://localhost:8765
```

## Wizard Steps

1. **Select DAGs** - Choose which DAG files to migrate
2. **Analyze** - Review detected patterns and complexity
3. **Configure** - Set conversion options
4. **Validate** - Verify conversion correctness
5. **Project Setup** - Configure project structure
6. **Deployment** - Set up work pools and schedules
7. **Export** - Download your new Prefect project

## Next Steps

- [Quickstart Guide](quickstart.md) - Detailed walkthrough
- [Getting Started](../getting-started.md) - MCP tool usage
- [Examples](../examples.md) - Real conversion examples

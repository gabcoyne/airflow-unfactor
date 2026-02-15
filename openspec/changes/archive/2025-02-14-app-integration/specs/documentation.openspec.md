# Spec: Documentation Consolidation

## Overview

Consolidate to a single documentation system (Jekyll) and add wizard documentation.

## Current State

Two documentation systems exist:
- `docs/` - Jekyll markdown (19 files)
- `docs-site/` - Next.js app (~complex build)

## Target State

Single Jekyll-based docs in `docs/`:
- Simple markdown files
- Standard GitHub Pages deployment
- Easy to contribute to

## New Documentation Structure

```
docs/
├── _config.yml              # Jekyll config (updated)
├── index.md                 # Home page (existing)
├── getting-started.md       # Quick start (existing, updated)
├── examples.md              # Examples (existing)
├── operator-mapping.md      # Operator reference (existing)
├── operator-coverage.md     # Coverage matrix (existing)
├── testing.md               # Test guide (existing)
├── playbooks.md             # Patterns (existing)
├── troubleshooting.md       # FAQ (existing)
├── convert-reference.md     # API reference (existing)
│
├── wizard/                  # NEW: Wizard documentation
│   ├── index.md             # Wizard overview
│   ├── quickstart.md        # Getting started with wizard
│   ├── steps.md             # Step-by-step guide
│   └── deployment.md        # Production deployment
│
├── configuration/           # NEW: Configuration docs
│   ├── index.md             # Config overview
│   ├── external-mcp.md      # External MCP setup
│   └── environment.md       # Environment variables
│
├── conversion/              # Existing conversion guides
│   ├── dynamic-mapping.md
│   ├── taskgroups.md
│   ├── trigger-rules.md
│   ├── jinja-templates.md
│   ├── connections.md
│   └── variables.md
│
├── guides/                  # Existing guides
│   ├── enterprise-migration.md
│   └── prefect-cloud.md
│
└── tools/                   # Existing tool docs
    ├── validate.md
    └── metrics.md
```

## New Documentation Files

### docs/wizard/index.md

```markdown
---
layout: page
title: Migration Wizard
permalink: /wizard/
---

# Migration Wizard

The Migration Wizard provides a guided, visual interface for migrating Airflow DAGs to Prefect flows.

## Features

- **Step-by-step guidance** through the migration process
- **Visual DAG analysis** with complexity scoring
- **Live code preview** of converted flows
- **Project export** as a ready-to-use ZIP file

## Quick Start

```bash
# Start the wizard
airflow-unfactor --ui

# Open in browser
open http://localhost:8765
```

## When to Use the Wizard

The wizard is ideal for:
- Teams new to Prefect wanting guided migration
- Exploring how DAGs will be converted before committing
- Generating complete project scaffolds with best practices

For programmatic migrations or CI/CD integration, use the [MCP tools](../getting-started.md) directly.

## Next Steps

- [Wizard Quickstart](quickstart.md) - Your first migration
- [Step-by-Step Guide](steps.md) - Detailed walkthrough
- [Production Deployment](deployment.md) - Deploy wizard in your org
```

### docs/wizard/quickstart.md

```markdown
---
layout: page
title: Wizard Quickstart
permalink: /wizard/quickstart/
---

# Wizard Quickstart

Migrate your first DAG using the visual wizard.

## Prerequisites

- Python 3.11+
- airflow-unfactor installed: `pip install airflow-unfactor[ui]`

## Start the Wizard

```bash
airflow-unfactor --ui
```

Open http://localhost:8765 in your browser.

## Step 1: Select DAGs

1. Click "Browse" or drag-and-drop your DAG directory
2. Select which DAGs to migrate
3. Click "Analyze"

## Step 2: Review Analysis

The wizard shows:
- Operators detected
- Dependencies
- Complexity score
- Conversion notes

Review any warnings before proceeding.

## Step 3: Configure Conversion

Choose options:
- **Include comments**: Add educational comments explaining Prefect patterns
- **Generate tests**: Create pytest tests for the converted flow
- **Migration runbook**: Generate step-by-step migration guide

## Step 4: Validate

The wizard validates that:
- Task counts match
- Dependencies are preserved
- Data flow patterns converted correctly

Review any issues flagged.

## Step 5: Configure Project

Set up your Prefect project:
- Project name
- Workspace
- Include Docker files
- Include GitHub Actions

## Step 6: Export

Download your project as a ZIP file containing:
- Converted flows
- Generated tests
- Deployment configurations
- Migration runbook
```

### docs/configuration/external-mcp.md

```markdown
---
layout: page
title: External MCP Configuration
permalink: /configuration/external-mcp/
---

# External MCP Configuration

airflow-unfactor can enrich conversions with context from external MCP servers.

## Supported External MCPs

### Prefect Documentation MCP

Provides current Prefect documentation and best practices.

### Astronomer Migration MCP

Provides Airflow 2→3 migration guidance relevant to your DAG patterns.

## Configuration

Create `mcp.external.json` in your working directory:

```json
{
  "prefect": {
    "enabled": true,
    "url": "https://mcp.prefect.io",
    "timeout_seconds": 10
  },
  "astronomer": {
    "enabled": true,
    "url": "https://mcp.astronomer.io",
    "timeout_seconds": 10
  }
}
```

## Environment Variables

Alternatively, use environment variables:

```bash
export AIRFLOW_UNFACTOR_PREFECT_MCP_URL="https://mcp.prefect.io"
export AIRFLOW_UNFACTOR_ASTRONOMER_MCP_URL="https://mcp.astronomer.io"
```

## Disabling External Context

To convert without external context:

```bash
# CLI
airflow-unfactor --no-external-context

# MCP tool call
{"include_external_context": false}
```

## Fallback Behavior

If external MCPs are unavailable:
- Conversion proceeds without enrichment
- A warning is included in the output
- No errors are raised

Set `fallback_mode` in config:
- `silent` (default): No warning
- `warn`: Include warning in output
- `error`: Fail if external MCP unavailable
```

## Files to Remove

After migrating any unique content:

```
docs-site/           # Entire directory
```

## _config.yml Updates

```yaml
title: airflow-unfactor
description: Convert Apache Airflow DAGs to Prefect flows
baseurl: "/airflow-unfactor"
url: "https://prefecthq.github.io"

theme: minima

plugins:
  - jekyll-seo-tag

header_pages:
  - index.md
  - getting-started.md
  - wizard/index.md      # NEW
  - examples.md
  - operator-mapping.md
  - testing.md

collections:
  wizard:
    output: true
    permalink: /wizard/:path/
  configuration:
    output: true
    permalink: /configuration/:path/
```

## README Updates

Add wizard section to README.md:

```markdown
## Migration Wizard

For a guided, visual migration experience:

```bash
# Install with UI support
pip install airflow-unfactor[ui]

# Start the wizard
airflow-unfactor --ui

# Open http://localhost:8765
```

The wizard provides:
- Step-by-step migration guidance
- Visual DAG analysis
- Live conversion preview
- Complete project export

See the [Wizard Documentation](https://prefecthq.github.io/airflow-unfactor/wizard/) for details.
```

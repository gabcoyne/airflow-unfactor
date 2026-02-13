# Migration Wizard MCP App

## Problem

The current airflow-unfactor UX is AI-assistant-centric: users must interact through Claude Desktop or Cursor, asking natural language questions and receiving JSON responses. This works well for developers familiar with AI coding assistants, but presents challenges:

1. **No visual feedback** — Users can't see conversion progress, warnings, or confidence scores in real-time
2. **Linear flow** — No easy way to go back and adjust settings after seeing results
3. **Hidden complexity** — Analysis results, validation issues, and configuration options are buried in JSON
4. **No project preview** — Users can't see what the final project structure will look like before committing
5. **Manual assembly** — Converting multiple DAGs requires coordinating multiple tool calls

## Solution

Build an MCP App that provides an interactive wizard for migrating Airflow DAGs to Prefect flows. The wizard guides users through a 7-step process with visual feedback, real-time validation, and preview of the generated project structure.

### Why MCP Apps?

MCP Apps are ideal for this use case because:

- **Context preservation** — The wizard lives inside the conversation, maintaining context
- **Multi-step workflows** — Built for wizards with navigation, state persistence, and step-by-step refinement
- **Bidirectional data flow** — App can call existing `analyze`, `convert`, `validate` tools and display results interactively
- **Security** — Runs in sandboxed iframe, can't access host cookies or storage
- **No separate deployment** — Ships with the MCP server, no additional infrastructure needed

### Target Output

The wizard generates project structures following the PrefectHQ/flows pattern:

```
deployments/
  <workspace>/
    prefect.yaml           # Sophisticated config with YAML anchors
    <flow-name>/
      flow.py              # Converted Prefect flow
      requirements.txt     # Dependencies
      Dockerfile           # Container config
      test_flow.py         # Generated tests
```

## User Journey

### Step 1: Select DAGs
- File browser to select DAG files or directories
- Complexity indicators (Simple/Medium/Complex) based on quick analysis
- Batch selection with "Select All" / "Deselect All"

### Step 2: Analysis
- Detailed breakdown of each DAG: operators, dependencies, features
- Warnings surfaced prominently (custom operators, Jinja templates, dynamic patterns)
- Complexity score with explanation

### Step 3: Conversion Configuration
- Toggle options: educational comments, tests, runbooks
- Output structure selection: flat, PrefectHQ/flows style, custom
- Per-DAG overrides if needed

### Step 4: Validation
- Real-time progress bar during conversion
- Side-by-side comparison of DAG and flow structure
- Confidence scores with breakdown
- Issue highlighting with suggested fixes

### Step 5: Project Setup
- Project name and workspace configuration
- Infrastructure options: Dockerfile, GitHub Actions, pre-commit
- Dependency management: pyproject.toml generation

### Step 6: Deployment Configuration
- Work pool selection/creation guidance
- Schedule configuration with cron builder
- Parameter defaults and concurrency settings
- prefect.yaml preview with syntax highlighting

### Step 7: Export
- Full project tree preview
- Download as ZIP
- Copy individual files to clipboard
- Direct deploy button (calls `prefect deploy`)

## Success Criteria

1. **Functional wizard** — All 7 steps implemented with navigation
2. **Tool integration** — Calls existing analyze/convert/validate tools
3. **PrefectHQ/flows output** — Generates compatible project structure
4. **shadcn components** — Consistent, accessible UI
5. **Works in Claude Desktop** — Renders correctly in the host

## Non-Goals

- Modifying existing MCP tools (wizard is a UI layer on top)
- Supporting hosts other than Claude Desktop initially
- Real-time collaboration features
- Persistent storage of migration projects

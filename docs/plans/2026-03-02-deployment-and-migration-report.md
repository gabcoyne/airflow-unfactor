# Deployment Generation + Migration Report Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add two MCP tools — `generate_deployment` (writes `prefect.yaml` from DAG metadata) and `generate_migration_report` (writes `MIGRATION.md` with conversion decisions, production checklist, and Prefect MCP server suggestion).

**Architecture:** Each tool is a standalone async function in `src/airflow_unfactor/tools/`, registered on the FastMCP server in `server.py`. Tools write files to disk and return JSON, following the same pattern as `scaffold`. TDD throughout: write failing tests first, implement to pass, commit per task.

**Tech Stack:** Python 3.11, FastMCP, PyYAML (already a dep via prefect), pytest, `tmp_path` fixtures

---

## Context: How the codebase is structured

- `src/airflow_unfactor/tools/` — one file per tool (read_dag, lookup, scaffold, validate, search_docs)
- `src/airflow_unfactor/server.py` — registers all tools via `@mcp.tool` decorators; also updates the `instructions` docstring
- `tests/test_scaffold.py` — reference test file; uses `asyncio.run()` + `tmp_path`, tests internals (`_write_*`) and the public function
- `tests/test_drift.py` — asserts tool names appear in README.md and docs-site pages; **must be updated** when adding new tools
- `tests/test_server.py` — smoke-tests tool registration

Run tests with: `uv run pytest tests/ -q`
Lint with: `uv run ruff check --fix`

---

## Task 1: `generate_deployment` — core YAML writer

**Files:**
- Create: `src/airflow_unfactor/tools/generate_deployment.py`
- Create: `tests/test_generate_deployment.py`

### Step 1: Write the failing tests

```python
# tests/test_generate_deployment.py
"""Tests for generate_deployment tool."""

import asyncio
import json
from pathlib import Path

import pytest

from airflow_unfactor.tools.generate_deployment import (
    generate_deployment,
    _flow_to_deployment_yaml,
    _build_prefect_yaml,
)


class TestFlowToDeploymentYaml:
    """Unit tests for the per-flow YAML block builder."""

    def test_minimal_flow(self):
        """flow_name and entrypoint only — no schedule, params, tags."""
        yaml = _flow_to_deployment_yaml(
            flow_name="my_flow",
            entrypoint="deployments/default/my-flow/flow.py:my_flow",
        )
        assert "name: my-flow" in yaml
        assert "entrypoint: deployments/default/my-flow/flow.py:my_flow" in yaml
        assert "schedules" not in yaml
        assert "parameters" not in yaml

    def test_cron_schedule(self):
        yaml = _flow_to_deployment_yaml(
            flow_name="etl",
            entrypoint="deployments/default/etl/flow.py:etl",
            schedule="0 6 * * *",
        )
        assert 'cron: "0 6 * * *"' in yaml

    def test_interval_schedule(self):
        yaml = _flow_to_deployment_yaml(
            flow_name="etl",
            entrypoint="deployments/default/etl/flow.py:etl",
            schedule="3600",
        )
        assert "interval: 3600" in yaml

    def test_parameters(self):
        yaml = _flow_to_deployment_yaml(
            flow_name="etl",
            entrypoint="deployments/default/etl/flow.py:etl",
            parameters={"date": "2024-01-01", "env": "prod"},
        )
        assert "parameters:" in yaml
        assert "date:" in yaml
        assert "env:" in yaml

    def test_tags(self):
        yaml = _flow_to_deployment_yaml(
            flow_name="etl",
            entrypoint="deployments/default/etl/flow.py:etl",
            tags=["etl", "daily"],
        )
        assert "tags:" in yaml
        assert "etl" in yaml

    def test_description(self):
        yaml = _flow_to_deployment_yaml(
            flow_name="etl",
            entrypoint="deployments/default/etl/flow.py:etl",
            description="Converted from etl_dag",
        )
        assert "description: Converted from etl_dag" in yaml

    def test_dataset_triggers_emit_comment(self):
        yaml = _flow_to_deployment_yaml(
            flow_name="etl",
            entrypoint="deployments/default/etl/flow.py:etl",
            dataset_triggers=["s3://bucket/path"],
        )
        assert "Automation" in yaml or "automation" in yaml
        assert "s3://bucket/path" in yaml


class TestBuildPrefectYaml:
    """Tests for full prefect.yaml document construction."""

    def test_single_flow_produces_valid_yaml(self):
        content = _build_prefect_yaml(
            project_name="my-project",
            flows=[
                {
                    "flow_name": "etl",
                    "entrypoint": "deployments/default/etl/flow.py:etl",
                }
            ],
        )
        assert "name: my-project" in content
        assert "prefect-version:" in content
        assert "definitions:" in content
        assert "work_pools:" in content
        assert "deployments:" in content
        assert "TODO" in content  # work pool stub

    def test_multiple_flows(self):
        content = _build_prefect_yaml(
            project_name="proj",
            flows=[
                {"flow_name": "flow_a", "entrypoint": "deployments/default/flow-a/flow.py:flow_a"},
                {"flow_name": "flow_b", "entrypoint": "deployments/default/flow-b/flow.py:flow_b"},
            ],
        )
        assert "name: flow-a" in content
        assert "name: flow-b" in content

    def test_yaml_anchors_present(self):
        content = _build_prefect_yaml(
            project_name="proj",
            flows=[{"flow_name": "f", "entrypoint": "deployments/default/f/flow.py:f"}],
        )
        assert "&default_pool" in content
        assert "*default_pool" in content

    def test_pull_step_commented_out(self):
        content = _build_prefect_yaml(
            project_name="proj",
            flows=[{"flow_name": "f", "entrypoint": "deployments/default/f/flow.py:f"}],
        )
        assert "# pull:" in content or "pull:" not in content


class TestGenerateDeploymentTool:
    """Integration tests for the full tool."""

    def test_writes_prefect_yaml(self, tmp_path):
        result_json = asyncio.run(
            generate_deployment(
                output_directory=str(tmp_path),
                flows=[
                    {
                        "flow_name": "etl",
                        "entrypoint": "deployments/default/etl/flow.py:etl",
                        "schedule": "0 6 * * *",
                    }
                ],
            )
        )
        result = json.loads(result_json)
        assert (tmp_path / "prefect.yaml").exists()
        assert result["created_file"].endswith("prefect.yaml")
        assert "etl" in result["deployment_names"]
        assert len(result["next_steps"]) > 0

    def test_next_steps_mention_work_pool(self, tmp_path):
        result_json = asyncio.run(
            generate_deployment(
                output_directory=str(tmp_path),
                flows=[{"flow_name": "f", "entrypoint": "deployments/default/f/flow.py:f"}],
            )
        )
        result = json.loads(result_json)
        combined = " ".join(result["next_steps"])
        assert "work pool" in combined.lower()

    def test_dataset_triggers_mentioned_in_next_steps(self, tmp_path):
        result_json = asyncio.run(
            generate_deployment(
                output_directory=str(tmp_path),
                flows=[
                    {
                        "flow_name": "f",
                        "entrypoint": "deployments/default/f/flow.py:f",
                        "dataset_triggers": ["s3://bucket/key"],
                    }
                ],
            )
        )
        result = json.loads(result_json)
        combined = " ".join(result["next_steps"])
        assert "automation" in combined.lower() or "Automation" in combined

    def test_flow_name_slugified(self, tmp_path):
        """flow_name with underscores → slug with hyphens in deployment name."""
        result_json = asyncio.run(
            generate_deployment(
                output_directory=str(tmp_path),
                flows=[{"flow_name": "my_etl_flow", "entrypoint": "f.py:my_etl_flow"}],
            )
        )
        content = (tmp_path / "prefect.yaml").read_text()
        assert "name: my-etl-flow" in content
```

### Step 2: Run to confirm all fail

```bash
uv run pytest tests/test_generate_deployment.py -q
```
Expected: `ImportError` — module doesn't exist yet.

### Step 3: Implement `generate_deployment.py`

```python
# src/airflow_unfactor/tools/generate_deployment.py
"""Generate prefect.yaml deployment configuration from DAG metadata."""

import json
from pathlib import Path
from typing import Any


def _slugify(name: str) -> str:
    """Convert snake_case or any name to kebab-case slug."""
    return name.replace("_", "-").lower()


def _flow_to_deployment_yaml(
    flow_name: str,
    entrypoint: str,
    schedule: str | None = None,
    parameters: dict[str, Any] | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    dataset_triggers: list[str] | None = None,
) -> str:
    """Build the YAML block for a single deployment entry."""
    slug = _slugify(flow_name)
    lines = [f"  - name: {slug}"]

    if description:
        lines.append(f"    description: {description}")

    lines.append(f"    entrypoint: {entrypoint}")

    if tags:
        lines.append(f"    tags: [{', '.join(tags)}]")

    if parameters:
        lines.append("    parameters:")
        for k, v in parameters.items():
            if isinstance(v, str):
                lines.append(f'      {k}: "{v}"')
            else:
                lines.append(f"      {k}: {v}")

    if schedule:
        schedule = schedule.strip()
        _PRESET_CRON = {
            "@daily": "0 0 * * *",
            "@hourly": "0 * * * *",
            "@weekly": "0 0 * * 0",
            "@monthly": "0 0 1 * *",
            "@yearly": "0 0 1 1 *",
        }
        if schedule in _PRESET_CRON:
            cron = _PRESET_CRON[schedule]
            lines.append(f'    schedules:\n      - cron: "{cron}"')
        elif schedule.isdigit():
            lines.append(f"    schedules:\n      - interval: {schedule}")
        else:
            lines.append(f'    schedules:\n      - cron: "{schedule}"')

    if dataset_triggers:
        lines.append("    # Dataset triggers require Prefect Automations (not representable in prefect.yaml).")
        lines.append("    # Create an Automation for each dataset trigger below:")
        for ds in dataset_triggers:
            lines.append(f"    #   - trigger: event on dataset '{ds}' → run this deployment")
        lines.append("    # See: https://docs.prefect.io/concepts/automations")

    lines.append("    work_pool: *default_pool")
    return "\n".join(lines)


def _build_prefect_yaml(
    project_name: str,
    flows: list[dict[str, Any]],
) -> str:
    """Build the full prefect.yaml document."""
    deployments = "\n".join(
        _flow_to_deployment_yaml(**{k: v for k, v in f.items()})
        for f in flows
    )

    return f"""# Prefect deployment configuration
# See: https://docs.prefect.io/concepts/deployments/

name: {project_name}
prefect-version: 3.0.0

# Configure your repository pull step:
# pull:
#   - prefect.deployments.steps.git_clone:
#       repository: https://github.com/org/{project_name}
#       branch: main

definitions:
  work_pools:
    default: &default_pool
      name: default  # TODO: set your work pool name (uv run prefect work-pool create <name>)
      job_variables:
        image: "{{{{ image }}}}"

  schedules:
    hourly: &hourly
      cron: "0 * * * *"
    daily: &daily
      cron: "0 0 * * *"

deployments:
{deployments}
"""


async def generate_deployment(
    output_directory: str,
    flows: list[dict[str, Any]],
    workspace: str = "default",
) -> str:
    """Write prefect.yaml deployment configuration from DAG metadata.

    Args:
        output_directory: Directory to write prefect.yaml into.
        flows: List of flow dicts. Each requires flow_name and entrypoint;
            all other fields (schedule, parameters, description, tags,
            dataset_triggers) are optional.
        workspace: Workspace name (default: "default").

    Returns:
        JSON with created_file, deployment_names, next_steps.
    """
    output_dir = Path(output_directory)
    output_dir.mkdir(parents=True, exist_ok=True)

    project_name = _slugify(output_dir.name)
    content = _build_prefect_yaml(project_name=project_name, flows=flows)

    prefect_yaml = output_dir / "prefect.yaml"
    prefect_yaml.write_text(content)

    deployment_names = [_slugify(f["flow_name"]) for f in flows]

    has_dataset_triggers = any(f.get("dataset_triggers") for f in flows)

    next_steps = [
        "Set up a work pool: uv run prefect work-pool create <name> --type process",
        "Update the work_pool name in prefect.yaml",
        "Configure the pull step in prefect.yaml with your git repository",
        "Deploy: uv run prefect deploy --all",
    ]
    if has_dataset_triggers:
        next_steps.append(
            "Create Automations for dataset triggers: https://docs.prefect.io/concepts/automations"
        )

    return json.dumps(
        {
            "created_file": str(prefect_yaml),
            "deployment_names": deployment_names,
            "next_steps": next_steps,
        },
        indent=2,
    )
```

### Step 4: Run tests

```bash
uv run pytest tests/test_generate_deployment.py -q
```
Expected: all pass.

### Step 5: Lint

```bash
uv run ruff check --fix src/airflow_unfactor/tools/generate_deployment.py
```

### Step 6: Commit

```bash
git add src/airflow_unfactor/tools/generate_deployment.py tests/test_generate_deployment.py
git commit -m "feat: add generate_deployment tool — writes prefect.yaml from DAG metadata"
```

---

## Task 2: `generate_migration_report` — MIGRATION.md writer

**Files:**
- Create: `src/airflow_unfactor/tools/generate_migration_report.py`
- Create: `tests/test_generate_migration_report.py`

### Step 1: Write the failing tests

```python
# tests/test_generate_migration_report.py
"""Tests for generate_migration_report tool."""

import asyncio
import json
from pathlib import Path

import pytest

from airflow_unfactor.tools.generate_migration_report import (
    generate_migration_report,
    _render_decisions_table,
    _render_checklist,
    PREFECT_DOC_LINKS,
)


class TestDocLinks:
    """The doc links map must cover core action types."""

    def test_core_action_types_have_links(self):
        for key in ["setup_work_pool", "configure_block", "migrate_connections", "create_automation"]:
            assert key in PREFECT_DOC_LINKS, f"Missing doc link for {key}"
            assert PREFECT_DOC_LINKS[key].startswith("http"), f"Bad URL for {key}"


class TestDecisionsTable:
    """Markdown table rendering for conversion decisions."""

    def test_table_has_headers(self):
        table = _render_decisions_table([
            {"component": "S3KeySensor", "outcome": "polling @task", "rationale": "short wait"},
        ])
        assert "Component" in table
        assert "Outcome" in table
        assert "Rationale" in table

    def test_decision_appears_in_table(self):
        table = _render_decisions_table([
            {"component": "S3KeySensor", "outcome": "polling @task", "rationale": "short wait"},
        ])
        assert "S3KeySensor" in table
        assert "polling @task" in table

    def test_manual_action_flagged(self):
        table = _render_decisions_table([
            {
                "component": "S3KeySensor",
                "outcome": "polling @task",
                "manual_action": "configure_s3_block",
            }
        ])
        assert "⚠" in table or "manual" in table.lower() or "action" in table.lower()

    def test_empty_decisions(self):
        table = _render_decisions_table([])
        assert isinstance(table, str)


class TestChecklist:
    """Markdown checklist rendering."""

    def test_checklist_items_are_checkboxes(self):
        checklist = _render_checklist(
            decisions=[{"component": "X", "outcome": "Y", "manual_action": "setup_work_pool"}],
            manual_actions=["migrate_connections"],
        )
        assert "- [ ]" in checklist

    def test_checklist_deduplicated(self):
        checklist = _render_checklist(
            decisions=[
                {"component": "A", "outcome": "x", "manual_action": "setup_work_pool"},
                {"component": "B", "outcome": "y", "manual_action": "setup_work_pool"},
            ],
            manual_actions=["setup_work_pool"],
        )
        assert checklist.count("work pool") == 1 or checklist.count("work_pool") == 1

    def test_known_action_has_link(self):
        checklist = _render_checklist(
            decisions=[],
            manual_actions=["setup_work_pool"],
        )
        assert "https://docs.prefect.io" in checklist

    def test_unknown_action_still_appears(self):
        checklist = _render_checklist(
            decisions=[],
            manual_actions=["some_custom_action"],
        )
        assert "some_custom_action" in checklist


class TestGenerateMigrationReport:
    """Integration tests for the full tool."""

    def test_writes_migration_md(self, tmp_path):
        result_json = asyncio.run(
            generate_migration_report(
                output_directory=str(tmp_path),
                dag_path="dags/etl_dag.py",
                flow_path="deployments/default/etl/flow.py",
                decisions=[
                    {"component": "S3KeySensor", "outcome": "polling @task",
                     "manual_action": "configure_s3_block"},
                ],
                manual_actions=["setup_work_pool"],
            )
        )
        result = json.loads(result_json)
        assert (tmp_path / "MIGRATION.md").exists()
        assert result["created_file"].endswith("MIGRATION.md")
        assert result["checklist_items_count"] >= 1

    def test_report_has_all_sections(self, tmp_path):
        asyncio.run(
            generate_migration_report(
                output_directory=str(tmp_path),
                dag_path="dags/etl_dag.py",
                flow_path="deployments/default/etl/flow.py",
                decisions=[],
                manual_actions=["setup_work_pool"],
            )
        )
        content = (tmp_path / "MIGRATION.md").read_text()
        assert "## Summary" in content
        assert "## Conversion Decisions" in content
        assert "## Before Production" in content
        assert "Prefect MCP" in content

    def test_mcp_suggestion_in_report(self, tmp_path):
        asyncio.run(
            generate_migration_report(
                output_directory=str(tmp_path),
                dag_path="dags/etl_dag.py",
                flow_path="deployments/default/etl/flow.py",
                decisions=[],
                manual_actions=[],
            )
        )
        content = (tmp_path / "MIGRATION.md").read_text()
        assert "https://docs.prefect.io/mcp" in content

    def test_mcp_prominent_when_claude_mcp_json_exists(self, tmp_path):
        """When .claude/mcp.json exists without Prefect, MCP note is prominent."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "mcp.json").write_text('{"mcpServers": {}}')

        asyncio.run(
            generate_migration_report(
                output_directory=str(tmp_path),
                dag_path="dags/etl_dag.py",
                flow_path="deployments/default/etl/flow.py",
                decisions=[],
                manual_actions=[],
            )
        )
        content = (tmp_path / "MIGRATION.md").read_text()
        # Prominent = appears before the checklist section or has a callout marker
        mcp_pos = content.find("https://docs.prefect.io/mcp")
        before_prod_pos = content.find("## Before Production")
        assert mcp_pos < before_prod_pos or "> " in content  # callout or early

    def test_dag_path_in_summary(self, tmp_path):
        asyncio.run(
            generate_migration_report(
                output_directory=str(tmp_path),
                dag_path="dags/my_dag.py",
                flow_path="deployments/default/my-flow/flow.py",
                decisions=[],
                manual_actions=[],
            )
        )
        content = (tmp_path / "MIGRATION.md").read_text()
        assert "my_dag.py" in content
        assert "my-flow/flow.py" in content
```

### Step 2: Run to confirm all fail

```bash
uv run pytest tests/test_generate_migration_report.py -q
```
Expected: `ImportError`.

### Step 3: Implement `generate_migration_report.py`

```python
# src/airflow_unfactor/tools/generate_migration_report.py
"""Generate MIGRATION.md — human-readable record of a DAG conversion."""

import json
from datetime import date
from pathlib import Path
from typing import Any

# Known manual action types → Prefect documentation URLs
PREFECT_DOC_LINKS: dict[str, str] = {
    "setup_work_pool": "https://docs.prefect.io/concepts/work-pools",
    "configure_block": "https://docs.prefect.io/concepts/blocks",
    "configure_s3_block": "https://prefecthq.github.io/prefect-aws/",
    "configure_gcs_block": "https://prefecthq.github.io/prefect-gcp/",
    "configure_snowflake_block": "https://prefecthq.github.io/prefect-snowflake/",
    "configure_sqlalchemy_block": "https://prefecthq.github.io/prefect-sqlalchemy/",
    "configure_azure_block": "https://prefecthq.github.io/prefect-azure/",
    "migrate_connections": "https://docs.prefect.io/concepts/blocks",
    "create_automation": "https://docs.prefect.io/concepts/automations",
    "configure_webhook": "https://docs.prefect.io/concepts/webhooks",
    "configure_kubernetes": "https://docs.prefect.io/concepts/infrastructure",
    "configure_pull_step": "https://docs.prefect.io/concepts/deployments/#the-pull-action",
    "configure_dbt_block": "https://prefecthq.github.io/prefect-dbt/",
    "configure_databricks_block": "https://prefecthq.github.io/prefect-databricks/",
}

_MCP_SNIPPET = """\
```json
{
  "mcpServers": {
    "prefect": {
      "type": "http",
      "url": "https://docs.prefect.io/mcp"
    }
  }
}
```"""

_MCP_SUGGESTION = f"""\
### Prefect MCP Server (Optional)

Add the Prefect docs MCP server to your Claude Code session for interactive documentation queries:

{_MCP_SNIPPET}

Add to `.claude/mcp.json` in your project or `~/.claude/mcp.json` globally.
"""


def _render_decisions_table(decisions: list[dict[str, Any]]) -> str:
    """Render conversion decisions as a Markdown table."""
    if not decisions:
        return "_No conversion decisions recorded._\n"

    rows = ["| Component | Airflow Pattern | Prefect Pattern | Rationale | Action Required |",
            "|-----------|-----------------|-----------------|-----------|-----------------|"]
    for d in decisions:
        component = d.get("component", "")
        outcome = d.get("outcome", "")
        rationale = d.get("rationale", "")
        action = d.get("manual_action", "")
        action_cell = f"⚠ `{action}`" if action else "—"
        rows.append(f"| {component} | | {outcome} | {rationale} | {action_cell} |")

    return "\n".join(rows) + "\n"


def _render_checklist(
    decisions: list[dict[str, Any]],
    manual_actions: list[str],
) -> str:
    """Render deduplicated before-production checklist with doc links."""
    # Collect all action types, preserving order, deduplicating
    seen: set[str] = set()
    ordered: list[str] = []
    for action in manual_actions:
        if action not in seen:
            seen.add(action)
            ordered.append(action)
    for d in decisions:
        action = d.get("manual_action", "")
        if action and action not in seen:
            seen.add(action)
            ordered.append(action)

    # Infrastructure-first ordering
    priority = ["setup_work_pool", "configure_pull_step", "configure_kubernetes"]
    blocks = [a for a in ordered if "block" in a or "connection" in a or "migrate" in a]
    automations = [a for a in ordered if "automation" in a or "webhook" in a]
    rest = [a for a in ordered if a not in priority and a not in blocks and a not in automations]

    final_order = (
        [a for a in priority if a in ordered]
        + [a for a in blocks if a not in priority]
        + [a for a in rest]
        + [a for a in automations]
    )

    if not final_order:
        return "_No manual actions required._\n"

    lines = []
    for action in final_order:
        url = PREFECT_DOC_LINKS.get(action)
        label = action.replace("_", " ").title()
        if url:
            lines.append(f"- [ ] {label}: [{url}]({url})")
        else:
            lines.append(f"- [ ] {label}")

    return "\n".join(lines) + "\n"


def _mcp_is_configured(output_directory: Path) -> bool:
    """Check whether the Prefect MCP server is already in .claude/mcp.json."""
    mcp_json = output_directory / ".claude" / "mcp.json"
    if not mcp_json.exists():
        return False
    try:
        data = json.loads(mcp_json.read_text())
        servers = data.get("mcpServers", {})
        return any("prefect" in k.lower() or "docs.prefect.io" in str(v)
                   for k, v in servers.items())
    except (json.JSONDecodeError, AttributeError):
        return False


def _mcp_json_exists(output_directory: Path) -> bool:
    return (output_directory / ".claude" / "mcp.json").exists()


async def generate_migration_report(
    output_directory: str,
    dag_path: str,
    flow_path: str,
    decisions: list[dict[str, Any]],
    manual_actions: list[str] | None = None,
) -> str:
    """Write MIGRATION.md — human-readable record of a DAG conversion.

    Args:
        output_directory: Directory to write MIGRATION.md into.
        dag_path: Path to the original Airflow DAG file.
        flow_path: Path to the generated Prefect flow file.
        decisions: List of conversion decision dicts. Each may have:
            component, outcome, rationale, manual_action.
        manual_actions: Top-level manual action types not tied to a component.

    Returns:
        JSON with created_file, checklist_items_count.
    """
    output_dir = Path(output_directory)
    output_dir.mkdir(parents=True, exist_ok=True)

    manual_actions = manual_actions or []
    today = date.today().isoformat()

    mcp_json_present = _mcp_json_exists(output_dir)
    mcp_configured = _mcp_is_configured(output_dir)
    mcp_prominent = mcp_json_present and not mcp_configured

    decisions_table = _render_decisions_table(decisions)
    checklist = _render_checklist(decisions, manual_actions)

    checklist_count = checklist.count("- [ ]")

    mcp_callout = ""
    if mcp_prominent:
        mcp_callout = f"""\
> **Tip:** The Prefect MCP server is not configured in `.claude/mcp.json`.
> Add it for interactive Prefect docs in your Claude Code session.
> See the [Prefect MCP Server](#prefect-mcp-server-optional) section below.

"""

    content = f"""\
# Migration Report

{mcp_callout}## Summary

| Field | Value |
|-------|-------|
| Original DAG | `{dag_path}` |
| Generated flow | `{flow_path}` |
| Conversion date | {today} |

---

## Conversion Decisions

{decisions_table}
---

## Before Production

{checklist}
---

{_MCP_SUGGESTION}
"""

    report_path = output_dir / "MIGRATION.md"
    report_path.write_text(content)

    return json.dumps(
        {
            "created_file": str(report_path),
            "checklist_items_count": checklist_count,
        },
        indent=2,
    )
```

### Step 4: Run tests

```bash
uv run pytest tests/test_generate_migration_report.py -q
```
Expected: all pass.

### Step 5: Lint

```bash
uv run ruff check --fix src/airflow_unfactor/tools/generate_migration_report.py
```

### Step 6: Commit

```bash
git add src/airflow_unfactor/tools/generate_migration_report.py tests/test_generate_migration_report.py
git commit -m "feat: add generate_migration_report tool — writes MIGRATION.md with checklist and MCP suggestion"
```

---

## Task 3: Register both tools on the MCP server

**Files:**
- Modify: `src/airflow_unfactor/server.py`

### Step 1: Write the failing test

```python
# Add to tests/test_server.py (or tests/test_drift.py if it checks tool names)
# Check that the new tools are registered:
def test_new_tools_registered(live_tool_names):
    assert "generate_deployment" in live_tool_names
    assert "generate_migration_report" in live_tool_names
```

Run: `uv run pytest tests/test_server.py -q`
Expected: FAIL — tools not registered yet.

### Step 2: Register in server.py

Add to the imports at the top of `server.py`:

```python
from airflow_unfactor.tools.generate_deployment import generate_deployment as _generate_deployment
from airflow_unfactor.tools.generate_migration_report import generate_migration_report as _generate_migration_report
```

Add two `@mcp.tool` functions after the existing `scaffold` registration:

```python
@mcp.tool
async def generate_deployment(
    output_directory: str,
    flows: list[dict],
    workspace: str = "default",
) -> str:
    """Write prefect.yaml deployment configuration from DAG metadata.

    Call after generating flow.py. Produces a complete prefect.yaml
    with YAML anchors, schedule config, parameter defaults, and TODO
    stubs for work pool and pull step configuration.

    Args:
        output_directory: Directory to write prefect.yaml into.
        flows: List of flow dicts. Each requires flow_name and entrypoint.
            Optional fields: schedule (cron/interval/None), parameters
            (dict of name→default), description, tags, dataset_triggers.
        workspace: Workspace name (default: "default").

    Returns:
        JSON with created_file, deployment_names, next_steps.
    """
    return await _generate_deployment(
        output_directory=output_directory,
        flows=flows,
        workspace=workspace,
    )


@mcp.tool
async def generate_migration_report(
    output_directory: str,
    dag_path: str,
    flow_path: str,
    decisions: list[dict],
    manual_actions: list[str] | None = None,
) -> str:
    """Write MIGRATION.md — human-readable record of a DAG conversion.

    Call as the final step after generate_deployment. Documents every
    conversion decision, produces a before-production checklist with
    Prefect doc links, and suggests adding the Prefect MCP server.

    Args:
        output_directory: Directory to write MIGRATION.md into.
        dag_path: Path to the original Airflow DAG file.
        flow_path: Path to the generated Prefect flow file.
        decisions: List of dicts, each with: component, outcome,
            rationale (optional), manual_action (optional).
        manual_actions: Top-level action types not tied to a specific
            component (e.g. "setup_work_pool", "migrate_connections").

    Returns:
        JSON with created_file, checklist_items_count.
    """
    return await _generate_migration_report(
        output_directory=output_directory,
        dag_path=dag_path,
        flow_path=flow_path,
        decisions=decisions,
        manual_actions=manual_actions,
    )
```

Also update the `instructions` string in `FastMCP(...)` to include steps 7 and 8:

```python
# In the instructions string, append after step 6 (scaffold):
"""
7. **generate_deployment** — Write prefect.yaml from DAG metadata
   (schedule, parameters, dataset triggers, tags)
8. **generate_migration_report** — Write MIGRATION.md with conversion
   decisions table, before-production checklist, and Prefect MCP server
   suggestion
"""
```

### Step 3: Run tests

```bash
uv run pytest tests/test_server.py -q
```
Expected: pass.

### Step 4: Commit

```bash
git add src/airflow_unfactor/server.py tests/test_server.py
git commit -m "feat: register generate_deployment and generate_migration_report on MCP server"
```

---

## Task 4: Update drift tests and README

**Files:**
- Modify: `tests/test_drift.py`
- Modify: `README.md`

The drift tests in `test_drift.py` assert that every registered tool name appears in README.md and docs-site MDX pages. New tools must be added to both.

### Step 1: Run drift tests to see current failures

```bash
uv run pytest tests/test_drift.py -q
```
Expected: failures mentioning `generate_deployment` and `generate_migration_report` missing from docs.

### Step 2: Add to README.md

Find the tools table in README.md (look for `| read_dag |`) and add two rows:

```markdown
| `generate_deployment` | Write `prefect.yaml` from DAG metadata (schedule, params, triggers) |
| `generate_migration_report` | Write `MIGRATION.md` with conversion decisions and production checklist |
```

Also update the workflow section to show the full 8-step sequence.

### Step 3: Add to docs-site

Find `docs-site/src/app/docs/mcp/page.mdx` and add the same two rows to its tool table.

### Step 4: Run drift tests

```bash
uv run pytest tests/test_drift.py -q
```
Expected: all pass.

### Step 5: Run full suite

```bash
uv run pytest tests/ -q
```
Expected: all pass.

### Step 6: Commit

```bash
git add README.md docs-site/src/app/docs/mcp/page.mdx tests/test_drift.py
git commit -m "docs: add generate_deployment and generate_migration_report to README and docs-site"
```

---

## Task 5: Push

```bash
git push
```

---

## Verification

After all tasks complete, the full test suite should show 185+ tests passing (164 existing + ~21 new). Spot-check manually:

```bash
# Verify generate_deployment produces valid YAML
uv run python -c "
import asyncio, json
from airflow_unfactor.tools.generate_deployment import generate_deployment
r = asyncio.run(generate_deployment('/tmp/test-deploy', [{'flow_name': 'etl', 'entrypoint': 'deployments/default/etl/flow.py:etl', 'schedule': '0 6 * * *'}]))
print(json.loads(r)['created_file'])
"
cat /tmp/test-deploy/prefect.yaml

# Verify generate_migration_report
uv run python -c "
import asyncio, json
from airflow_unfactor.tools.generate_migration_report import generate_migration_report
r = asyncio.run(generate_migration_report('/tmp/test-report', 'dags/etl.py', 'deployments/default/etl/flow.py', [{'component': 'S3KeySensor', 'outcome': 'polling @task', 'manual_action': 'configure_s3_block'}], ['setup_work_pool']))
print(json.loads(r))
"
cat /tmp/test-report/MIGRATION.md
```

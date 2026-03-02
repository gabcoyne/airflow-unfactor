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
    "migrate_connections": "https://docs.prefect.io/guides/migrate-from-airflow",
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

    rows = ["| Component | Outcome | Rationale | Action Required |",
            "|-----------|---------|-----------|-----------------|"]
    for d in decisions:
        component = d.get("component", "")
        outcome = d.get("outcome", "")
        rationale = d.get("rationale", "")
        action = d.get("manual_action", "")
        action_cell = f"⚠ `{action}`" if action else "—"
        rows.append(f"| {component} | {outcome} | {rationale} | {action_cell} |")

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
            lines.append(f"- [ ] {label} (`{action}`): [{url}]({url})")
        else:
            lines.append(f"- [ ] {label} (`{action}`)")

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
        mcp_callout = """\
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

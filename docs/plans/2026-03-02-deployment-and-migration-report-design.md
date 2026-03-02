# Design: Deployment Generation + Migration Report

**Date:** 2026-03-02
**Status:** Approved

---

## Problem

After converting an Airflow DAG to a Prefect flow, the user has `flow.py` but nothing else is runnable. They need a `prefect.yaml` to deploy and a human-readable record of what was converted, what decisions were made, and what still requires manual work before going to production.

The current `scaffold` tool produces a blank `prefect.yaml` skeleton. `validate` is a code-comparison tool for the LLM — it produces no human artifact. There is no migration report.

---

## Solution: Two New MCP Tools

The recommended conversion sequence becomes:

```
read_dag
  → lookup_concept (×N)
  → [LLM generates flow.py]
  → validate
  → generate_deployment
  → generate_migration_report
```

Both tools write files to `output_directory`. By the end, the migration produces:

```
deployments/default/my-flow/
├── flow.py                  # LLM-generated
├── MIGRATION.md             # generate_migration_report
prefect.yaml                 # generate_deployment
```

---

## Tool 1: `generate_deployment`

Writes a complete `prefect.yaml` to `output_directory`.

### Input

```python
generate_deployment(
    output_directory="/path/to/project",
    flows=[
        {
            "flow_name": "etl_pipeline",           # required
            "entrypoint": "deployments/default/etl-pipeline/flow.py:etl_pipeline",  # required
            "schedule": "0 6 * * *",               # optional: cron, interval seconds, or None
            "parameters": {"date": "2024-01-01"},  # optional: name → default value
            "description": "Converted from etl_dag",  # optional
            "tags": ["etl"],                       # optional
            "dataset_triggers": ["s3://bucket/path"],  # optional: needs Automations
        }
    ],
    workspace="default",  # optional
)
```

All flow fields except `flow_name` and `entrypoint` are optional. Multiple flows produce multiple deployment entries in a single `prefect.yaml`.

### Output

A `prefect.yaml` with:
- YAML anchors for the work pool definition and common schedule patterns
- Work pool name always a stub with `# TODO: set your work pool name`
- Real schedule block when cron/interval is provided; commented stub when absent
- Parameters block with defaults when provided
- Comment block for any `dataset_triggers` explaining that Automations are required (not representable in `prefect.yaml`) with a link to the Automations docs
- Commented `pull` step stub for git clone configuration

Returns `{ created_file, deployment_names, next_steps }`.

### Example output shape

```yaml
name: my-project
prefect-version: 3.0.0

# pull:
#   - prefect.deployments.steps.git_clone:
#       repository: https://github.com/org/my-project
#       branch: main

definitions:
  work_pools:
    default: &default_pool
      name: default  # TODO: set your work pool name
      job_variables:
        image: "{{ image }}"

  schedules:
    hourly: &hourly
      cron: "0 * * * *"
    daily: &daily
      cron: "0 0 * * *"

deployments:
  - name: etl-pipeline
    description: Converted from etl_dag
    entrypoint: deployments/default/etl-pipeline/flow.py:etl_pipeline
    tags: [etl]
    parameters:
      date: "2024-01-01"
    schedules:
      - cron: "0 6 * * *"
    work_pool: *default_pool
```

---

## Tool 2: `generate_migration_report`

Writes `MIGRATION.md` to `output_directory`.

### Input

```python
generate_migration_report(
    output_directory="/path/to/project",
    dag_path="dags/etl_dag.py",
    flow_path="deployments/default/etl-pipeline/flow.py",
    decisions=[
        {
            "component": "S3KeySensor",
            "outcome": "polling retries @task",
            "rationale": "Short wait expected; event notifications not configured",
            "manual_action": "configure_s3_block",  # maps to known action type
        },
        {
            "component": "DatasetOrTimeSchedule",
            "outcome": "cron schedule in prefect.yaml + Automation required",
            "rationale": "Cron half represented in deployment; dataset trigger needs Automation",
            "manual_action": "create_automation",
        },
    ],
    manual_actions=["setup_work_pool", "migrate_connections"],  # top-level actions
)
```

### Known manual action types → Prefect doc links

The tool maintains an internal map so links are automatic:

| Action type | Prefect doc |
|---|---|
| `setup_work_pool` | https://docs.prefect.io/concepts/work-pools |
| `configure_block` | https://docs.prefect.io/concepts/blocks |
| `configure_s3_block` | https://prefecthq.github.io/prefect-aws/ |
| `configure_gcs_block` | https://prefecthq.github.io/prefect-gcp/ |
| `configure_snowflake_block` | https://prefecthq.github.io/prefect-snowflake/ |
| `configure_sqlalchemy_block` | https://prefecthq.github.io/prefect-sqlalchemy/ |
| `migrate_connections` | https://docs.prefect.io/concepts/blocks |
| `create_automation` | https://docs.prefect.io/concepts/automations |
| `configure_webhook` | https://docs.prefect.io/concepts/webhooks |
| `configure_kubernetes` | https://docs.prefect.io/concepts/infrastructure |
| `configure_pull_step` | https://docs.prefect.io/concepts/deployments/#the-pull-action |

### Output: `MIGRATION.md` structure

1. **Summary** — DAG name, conversion date, original path, generated flow path, `prefect.yaml` path
2. **Conversion decisions** — table: Component | Airflow pattern | Prefect pattern | Rationale | Action required
3. **Before production checklist** — deduplicated list of every manual action, each linked to Prefect docs. Ordered: infrastructure first (work pool, pull step), then blocks/connections, then automations/webhooks.
4. **Prefect MCP server** — if `.claude/mcp.json` exists and Prefect MCP is not configured, this appears as a prominent note; otherwise as a suggestion. Never written automatically.

Returns `{ created_file, checklist_items_count }`.

### Example `MIGRATION.md` checklist section

```markdown
## Before Production

- [ ] Set up a work pool: [Work Pools docs](https://docs.prefect.io/concepts/work-pools)
- [ ] Configure the `pull` step in `prefect.yaml` with your git repository
- [ ] Create a `SqlAlchemyConnector` block for `postgres_default`: [prefect-sqlalchemy](https://prefecthq.github.io/prefect-sqlalchemy/)
- [ ] Create an Automation for the dataset trigger on `snowflake://sales_reports_table`: [Automations docs](https://docs.prefect.io/concepts/automations)

### Optional: Prefect MCP Server

Add the Prefect docs MCP server to your Claude Code session for interactive documentation:

\`\`\`json
{
  "mcpServers": {
    "prefect": {
      "type": "http",
      "url": "https://docs.prefect.io/mcp"
    }
  }
}
\`\`\`
```

---

## What Does Not Change

- `scaffold` — unchanged; still creates directory structure
- `validate` — unchanged; still LLM-facing code comparison tool
- `read_dag`, `lookup_concept`, `search_prefect_docs` — unchanged

---

## Testing

Each tool gets a test module following existing patterns:

- `tests/test_generate_deployment.py` — parametrized over schedule types (cron, interval, None), multi-flow, dataset triggers present/absent, YAML validity
- `tests/test_generate_migration_report.py` — decisions table rendering, checklist deduplication, MCP server suggestion present/absent based on `.claude/mcp.json` state, all known action types produce valid links

Drift tests in `test_drift.py` updated to assert `generate_deployment` and `generate_migration_report` appear in README and docs-site tool table.

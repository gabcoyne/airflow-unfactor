# Phase 3: P2 Knowledge Expansion - Research

**Researched:** 2026-02-26
**Domain:** Airflow→Prefect knowledge expansion: Azure operators, dbt Cloud, Jinja macros, depends_on_past, deferrable operators, schedule translation
**Confidence:** HIGH for prefect-dbt / schedule / Jinja patterns; MEDIUM for prefect-azure ADF (no native ADF module); HIGH for depends_on_past / deferrable operator patterns

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Intent-First Approach (applies to ALL entries)**
- Every knowledge entry must include an explicit "what this achieves" section before the mapping
- Frame translations as: "This Airflow concept achieves X. In Prefect, the equivalent concept is Y, achieved via Z."
- Focus on the problem being solved, not mechanical syntax porting
- For concepts with no equivalent, explain the paradigm shift — why the concept doesn't map, not just that it doesn't
- Phase 1 models were mixed on this (Kubernetes was intent-first, HTTP was mechanical). Phase 3 sets the standard.

**Knowledge Entry Depth**
- Each Colin model: mapping + code example + credential/block setup
- One .md per operator in colin/models/operators/ (same structure as Phase 1)
- Stick to requirements scope only — no extra Azure operators beyond WasbOperator and AzureDataFactoryRunPipelineOperator

**"No Equivalent" Concepts**
- Tone: Honest and opinionated — "No direct equivalent. Here's what we recommend instead..."
- Include both conceptual explanation AND code snippet for workarounds
- depends_on_past and deferrable operators: standalone concept entries (not inline notes on other operators)
- Output format: structured differently from normal mappings — use `equivalent: none` with a `workaround` section so the LLM knows this isn't a drop-in replacement

**Schedule Translation in Scaffold**
- Cron strings pass through directly to Prefect's cron schedule
- timedelta intervals convert to Prefect's native IntervalSchedule (not cron equivalents)
- Scaffold accepts schedule as a parameter (LLM extracts it from DAG and passes it in)
- No schedule (None/@once): omit schedule section from prefect.yaml entirely — no comments, no placeholders

**Jinja Macro Scope**
- Cover the 5 required macros (ds_add, dag_run.conf, next_ds, prev_ds, run_id) plus ~5 common extras (ds, ts, execution_date, params, var.value)
- Live in a dedicated Jinja/template variables section in patterns.md
- Intent-first: explain what each macro achieves in Airflow, then show how Prefect handles that same need
- For macros with no Prefect equivalent concept (e.g., prev_ds assumes sequential runs): explain the paradigm shift, don't just say "not applicable"

### Claude's Discretion
- Exact list of "common extras" beyond the 5 required Jinja macros
- How to structure the "intent/what this achieves" section in Colin model format
- Whether lookup_concept needs query normalization for Jinja syntax (stripping {{ }})

### Deferred Ideas (OUT OF SCOPE)
- Review and update Phase 1 knowledge entries (Kubernetes, Databricks, Spark, HTTP, SSH) for intent-first consistency — separate work, not Phase 3 scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| KNOW-07 | Colin model for Azure operators (AzureDataFactoryRunPipelineOperator, WasbOperator) → prefect-azure | AzureDataFactoryRunPipelineOperator has no prefect-azure module; must use `azure-mgmt-datafactory` SDK directly. WasbOperator maps to `AzureBlobStorageCredentials` + `blob_storage_*` tasks from `prefect-azure`. Two separate entries with different packages. |
| KNOW-08 | Colin model for DbtCloudRunJobOperator → prefect-dbt DbtCloudCredentials + tasks | `trigger_dbt_cloud_job_run_and_wait_for_completion` from `prefect_dbt.cloud.jobs` is the primary pattern; `DbtCloudCredentials` block stores API key + account_id; verified from official Prefect docs. |
| KNOW-09 | Extended Jinja macro patterns for ds_add, dag_run.conf, next_ds, prev_ds, run_id | `runtime.flow_run.scheduled_start_time` is the Prefect equivalent for date macros; `dag_run.conf` becomes flow parameters; basic jinja-ds-to-runtime pattern already exists in patterns.md and needs significant expansion. |
| KNOW-10 | depends_on_past concept entry with explicit "no direct equivalent" workarounds | No Prefect equivalent exists. Workaround: query Prefect API for last flow run state + conditional early return. Must use `equivalent: none` with `workaround` section. |
| KNOW-11 | Deferrable operator / async sensor migration gotchas | No direct Prefect equivalent to deferrable operator mechanism. Pattern maps to `@task(retries=N, retry_delay_seconds=M)` for reschedule mode, or polling loops for poke mode. Intent-first: explain what resource efficiency problem deferrable operators solve, then show Prefect's approach. |
| KNOW-12 | Schedule translation in scaffold tool: schedule_interval/cron → prefect.yaml schedule config | scaffold_project function needs a `schedule_interval` parameter. Cron strings → `cron:` key in prefect.yaml schedules section; timedelta → `interval:` in seconds; None/@once → omit schedules section entirely. Verified from official Prefect deployment schedule docs. |
</phase_requirements>

## Summary

Phase 3 expands the Colin knowledge base with six requirements across three categories: new operator models (Azure + dbt), new concept entries (Jinja macros, depends_on_past, deferrable operators), and a scaffold tool enhancement (schedule-awareness).

The most important finding is that `prefect-azure` has **no Azure Data Factory module**. `AzureDataFactoryRunPipelineOperator` does not map to any prefect-azure class; the correct pattern is to use the `azure-mgmt-datafactory` SDK's `PipelineRunClient` directly inside a `@task`, with `AzureContainerInstanceCredentials` or service principal credentials from `prefect_azure.credentials`. This is an ARCHITECTURE SHIFT entry similar to KubernetesPodOperator — the paradigm is different enough to warrant an explicit warning against mechanical porting.

The `WasbOperator` → `prefect-azure` mapping is clean: `AzureBlobStorageCredentials` + `blob_storage_download`/`blob_storage_upload` tasks from `prefect_azure.blob_storage`. The dbt Cloud mapping via `trigger_dbt_cloud_job_run_and_wait_for_completion` is well-documented. Schedule translation in the scaffold tool is a focused code change to `scaffold.py` that adds a `schedule_interval` parameter and generates real schedule YAML instead of the current commented-out example.

**Primary recommendation:** Author each Colin model in `colin/models/operators/azure.md` and `colin/models/operators/dbt.md` following the Kubernetes model (intent-first, `## intent` section first), expand Jinja patterns in `colin/models/patterns.md`, add depends_on_past and deferrable operator entries to `colin/models/concepts.md`, and modify `scaffold_project()` to accept and emit schedule configuration.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `prefect-azure` | `>=0.4` | AzureBlobStorageCredentials block + blob_storage tasks | Official Prefect Azure integration |
| `prefect-dbt` | current | DbtCloudCredentials + trigger_dbt_cloud_job_run_and_wait_for_completion | Official Prefect dbt integration |
| `azure-mgmt-datafactory` | latest | Direct ADF pipeline trigger (no prefect-azure ADF module exists) | Only option for ADF; service principal auth |
| `azure-identity` | latest | DefaultAzureCredential / ClientSecretCredential for ADF | Microsoft-recommended auth library |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `prefect.runtime` | built-in prefect | `runtime.flow_run.scheduled_start_time` for Jinja date macros | All date/execution-time macro translations |
| `prefect.variables` | built-in prefect | Airflow Variable.get equivalents | Variable macro translations |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `azure-mgmt-datafactory` directly | `prefect-azure` ADF module | No prefect-azure ADF module exists — azure-mgmt-datafactory is the only option |
| `trigger_dbt_cloud_job_run_and_wait_for_completion` | `DbtCloudJob.trigger()` block pattern | Block pattern is also valid; task function is simpler for migration |

**Installation:**
```bash
# Azure (blob storage)
uv pip install "prefect-azure[blob_storage]"

# Azure (ADF — no prefect-azure module, use SDK directly)
uv pip install azure-mgmt-datafactory azure-identity

# dbt Cloud
uv pip install "prefect-dbt[cloud]"
```

## Architecture Patterns

### Recommended Colin Model Structure

Each new Colin model follows the same `{% section %}` template established in Phase 1. The Phase 3 requirement is to add an `## intent` section before `## prefect_pattern`. This is the "what this achieves" requirement from CONTEXT.md.

```
{% section OperatorName %}
## operator
OperatorName

## module
airflow.providers.<provider>.operators.<module>

## intent
[What problem this Airflow concept solves — 2-3 sentences from the user's perspective]

## source_context
[What the operator does mechanically]

## prefect_pattern
[How Prefect addresses the same need]

## prefect_package
[package name or "none"]

## prefect_import
[import statements]

## example
### before
```python
[Airflow code]
```
### after
```python
[Prefect code]
```

## notes
[Important gotchas, migration steps, warnings]

## related_concepts
[list]
{% endsection %}
```

### Pattern 1: AzureBlobStorage mapping (KNOW-07 — WasbOperator)

**What:** WasbOperator performs blob read/write operations against Azure Blob Storage using the `wasb://` protocol. In Prefect, this becomes `AzureBlobStorageCredentials` + `blob_storage_download`/`blob_storage_upload` tasks.

**When to use:** Any DAG using `WasbOperator`, `WasbDeleteOperator`, `WasbHook`, or `wasb_conn_id`.

**Example:**
```python
# Source: https://docs.prefect.io/integrations/prefect-azure/api-ref/prefect_azure-blob_storage
from prefect import flow, task
from prefect_azure import AzureBlobStorageCredentials
from prefect_azure.blob_storage import blob_storage_download

@task
def download_blob(container: str, blob: str) -> bytes:
    credentials = AzureBlobStorageCredentials.load("my-azure-credentials")
    return blob_storage_download(
        container=container,
        blob=blob,
        blob_storage_credentials=credentials,
    )
```

Credential setup:
```python
# Create and save block (run once)
from prefect_azure import AzureBlobStorageCredentials
creds = AzureBlobStorageCredentials(connection_string="DefaultEndpointsProtocol=https;...")
creds.save("my-azure-credentials")
```

### Pattern 2: AzureDataFactory mapping (KNOW-07 — AzureDataFactoryRunPipelineOperator)

**What:** `AzureDataFactoryRunPipelineOperator` triggers an ADF pipeline run and polls for completion. Prefect has no `prefect-azure` ADF module — this is an ARCHITECTURE SHIFT. The correct pattern is the `azure-mgmt-datafactory` SDK inside a `@task`.

```python
# Source: azure-mgmt-datafactory SDK (no prefect-azure equivalent)
from prefect import task
from azure.identity import ClientSecretCredential
from azure.mgmt.datafactory import DataFactoryManagementClient
from prefect.blocks.system import Secret

@task(retries=3, retry_delay_seconds=30)
def run_adf_pipeline(
    subscription_id: str,
    resource_group: str,
    factory_name: str,
    pipeline_name: str,
    parameters: dict | None = None,
) -> str:
    tenant_id = Secret.load("adf-tenant-id").get()
    client_id = Secret.load("adf-client-id").get()
    client_secret = Secret.load("adf-client-secret").get()

    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )
    adf_client = DataFactoryManagementClient(credential, subscription_id)
    run_response = adf_client.pipelines.create_run(
        resource_group,
        factory_name,
        pipeline_name,
        parameters=parameters or {},
    )
    return run_response.run_id
```

### Pattern 3: dbt Cloud mapping (KNOW-08)

**What:** `DbtCloudRunJobOperator` triggers a dbt Cloud job and waits for completion. In Prefect, `trigger_dbt_cloud_job_run_and_wait_for_completion` from `prefect_dbt.cloud.jobs` handles this end-to-end.

```python
# Source: https://docs.prefect.io/integrations/prefect-dbt/api-ref/prefect_dbt-cloud-jobs
from prefect import flow
from prefect_dbt.cloud import DbtCloudCredentials
from prefect_dbt.cloud.jobs import trigger_dbt_cloud_job_run_and_wait_for_completion

@flow
def run_dbt_job(job_id: int):
    credentials = DbtCloudCredentials.load("my-dbt-credentials")
    result = trigger_dbt_cloud_job_run_and_wait_for_completion(
        dbt_cloud_credentials=credentials,
        job_id=job_id,
        retry_filtered_models_attempts=3,
    )
    return result
```

Credential block setup:
```python
from prefect_dbt.cloud import DbtCloudCredentials
creds = DbtCloudCredentials(api_key="my_api_key", account_id=123456789)
creds.save("my-dbt-credentials")
```

### Pattern 4: Jinja macro expansion (KNOW-09)

The existing `jinja-ds-to-runtime` and `jinja-params-to-flow-params` entries in `patterns.md` need expansion to cover the full macro set. The new patterns belong in a dedicated `{% section jinja-template-variables %}` in `patterns.md`.

Key mappings (all verified via existing patterns.md + Prefect runtime docs):

| Airflow Jinja | Prefect Equivalent | Notes |
|--------------|-------------------|-------|
| `{{ ds }}` | `runtime.flow_run.scheduled_start_time.strftime("%Y-%m-%d")` | Already exists in jinja-ds-to-runtime |
| `{{ ts }}` | `runtime.flow_run.scheduled_start_time.isoformat()` | ISO 8601 timestamp |
| `{{ execution_date }}` | `runtime.flow_run.scheduled_start_time` | datetime object |
| `{{ next_ds }}` | compute from scheduled_start_time + interval | No direct concept; requires knowing interval |
| `{{ prev_ds }}` | compute from scheduled_start_time - interval | Paradigm shift: Prefect doesn't inherently know "previous" run |
| `{{ run_id }}` | `runtime.flow_run.name` or `str(runtime.flow_run.id)` | Different format but same purpose |
| `{{ dag_run.conf }}` | flow function parameters | `dag_run.conf` → typed flow params |
| `{{ macros.ds_add(ds, N) }}` | `(date + timedelta(days=N)).strftime("%Y-%m-%d")` | Pure Python date arithmetic |
| `{{ params.x }}` | flow function parameter `x` | Already exists in jinja-params-to-flow-params |
| `{{ var.value.x }}` | `Variable.get("x")` from `prefect.variables` | Prefect Variable API |

**Paradigm shift for `prev_ds`/`next_ds`:** These imply knowledge of the previous scheduled interval, which Airflow derives from the DAG's schedule. In Prefect, the flow doesn't own its schedule — the deployment does. If the interval matters, pass it as a flow parameter or compute it from the deployment's schedule. This is the same shift as `depends_on_past`.

### Pattern 5: depends_on_past (KNOW-10 — "no equivalent")

**What this achieves in Airflow:** Prevents a task from running if its previous DAG run instance failed. Enforces sequential data integrity across scheduled runs.

**In Prefect:** No direct equivalent exists. Prefect flows are stateless by default — each run is independent. The workaround is to query the Prefect API for the previous flow run's state at the start of the flow.

```python
from prefect import flow, get_client
from prefect.client.schemas.filters import DeploymentFilter, FlowRunFilter
from prefect.client.schemas.sorting import FlowRunSort

@flow
def my_flow():
    # Simulate depends_on_past: fail if previous run failed
    with get_client(sync_client=True) as client:
        runs = client.read_flow_runs(
            deployment_filter=DeploymentFilter(name={"like_": "my-flow/default"}),
            sort=FlowRunSort.START_TIME_DESC,
            limit=2,
        )
    if len(runs) >= 2 and not runs[1].state.is_completed():
        raise Exception(
            f"Previous run {runs[1].id} did not complete successfully. "
            "Skipping this run to maintain data integrity."
        )
    # ... rest of flow
```

Colin entry format: `equivalent: none` + `workaround:` section. This is not a drop-in replacement.

### Pattern 6: Deferrable operators (KNOW-11 — "no equivalent")

**What this achieves in Airflow:** A deferrable operator suspends itself and frees the worker slot while waiting for an external event, handing off to a Trigger component. This avoids wasting worker resources on long-running waits.

**In Prefect:** No direct Trigger/deferrable mechanism exists. Prefect's equivalent patterns depend on the wait duration:

- **Short waits (< 5 min):** `@task(retries=N, retry_delay_seconds=M)` — worker holds the task slot but retries on failure
- **Long waits (reschedule-mode equivalent):** Use Prefect Automations — emit an event when the external condition is met, trigger the flow from that event
- **Polling loops:** `@task` with explicit loop + `time.sleep()` (same resource overhead as Airflow poke mode)

The honest answer: Prefect 3.x does not have Airflow-style deferrable operators. If resource efficiency during long waits is critical, use Automations + event-driven deployment triggers.

### Pattern 7: Schedule translation in scaffold (KNOW-12)

**Current state:** `scaffold_project()` generates a `prefect.yaml` with commented-out schedule examples. The `_write_prefect_yaml()` function has no `schedule_interval` parameter.

**Required change:** Add `schedule_interval` parameter to `scaffold_project()` and pass it to `_write_prefect_yaml()`. Generate real schedule YAML based on type:

```python
def _schedule_yaml(schedule_interval) -> str:
    """Convert Airflow schedule_interval to prefect.yaml schedule config."""
    if schedule_interval is None or schedule_interval == "@once":
        return ""  # omit entirely
    if isinstance(schedule_interval, str):
        # Cron string — pass through
        return f"    schedules:\n      - cron: \"{schedule_interval}\"\n"
    if hasattr(schedule_interval, "total_seconds"):
        # timedelta → interval in seconds
        seconds = int(schedule_interval.total_seconds())
        return f"    schedules:\n      - interval: {seconds}\n"
    return ""  # unknown type — omit
```

In `prefect.yaml`, the schedule lives under the deployment entry:
```yaml
# Source: https://docs.prefect.io/v3/how-to-guides/deployments/create-schedules
deployments:
  - name: my-flow
    entrypoint: deployments/default/my-flow/flow.py:my_flow
    schedules:
      - cron: "0 6 * * *"
```

Note: Prefect 3 uses `schedules:` (plural) under each deployment, not a top-level `schedule:` key. The scaffold receives the schedule as a parameter; the LLM extracts it from the DAG source using `read_dag`.

### Anti-Patterns to Avoid

- **ADF via prefect-azure**: Do not try to use `prefect_azure.credentials.AzureContainerInstanceCredentials` for ADF — these are for Container Instances, not Data Factory. Use `azure-mgmt-datafactory` SDK directly.
- **Jinja macro in @task body**: Do not use `{{ ds }}` syntax inside `@task` — it is rendered by Airflow's template engine, not Python. Always replace with `runtime.flow_run.scheduled_start_time`.
- **depends_on_past via XCom**: Do not simulate `depends_on_past` by passing state via Prefect Variables or XCom equivalents. Query the Prefect API directly.
- **Deferrable operator wrapper**: Do not wrap or call Airflow's deferrable operator classes in Prefect tasks. They depend on the Airflow Triggerer component.
- **Schedule on @flow**: Do not put schedule in the `@flow` decorator. In Prefect, schedules live in deployment config (`prefect.yaml`), not in flow code.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ADF pipeline run + poll | Custom requests to ADF REST API | `azure-mgmt-datafactory` SDK | SDK handles auth token refresh, pagination, error types |
| dbt Cloud job poll | Custom HTTP polling loop | `trigger_dbt_cloud_job_run_and_wait_for_completion` | Handles status polling, retry filtered models, error mapping |
| Blob storage upload/download | Custom `azure-storage-blob` calls | `prefect-azure` `blob_storage_*` tasks | Block-based credential management, Prefect observability |
| Jinja date math | Custom date arithmetic | Standard Python `datetime` + `timedelta` | `macros.ds_add(ds, N)` is just `(date + timedelta(days=N)).strftime(...)` |

**Key insight:** For ADF, the absence of a `prefect-azure` ADF module is intentional — the Prefect team has not built one. Do not attempt to replicate it with custom HTTP; the `azure-mgmt-datafactory` SDK is the correct solution.

## Common Pitfalls

### Pitfall 1: prefect-azure has no ADF module
**What goes wrong:** Developer assumes `prefect-azure` covers all Azure services including Data Factory.
**Why it happens:** Every other provider (AWS, GCP, Databricks) has a dedicated prefect-* package covering the main services. Azure is incomplete.
**How to avoid:** The Colin model must explicitly state "No prefect-azure ADF module exists" and show the `azure-mgmt-datafactory` pattern.
**Warning signs:** Any attempt to `from prefect_azure import DataFactory*` will fail at import.

### Pitfall 2: `AzureBlobStorageCredentials` vs `AzureBlobCredentials`
**What goes wrong:** Two similar class names exist — `AzureBlobStorageCredentials` (for blob_storage tasks) and `AzureBlobCredentials` (older, for AzureBlobStorage block used in flow code storage).
**Why it happens:** prefect-azure has layered blob storage abstractions for different use cases.
**How to avoid:** For WasbOperator migration, use `AzureBlobStorageCredentials` from `prefect_azure` with `blob_storage_download`/`blob_storage_upload`. Don't use `AzureBlobCredentials`.

### Pitfall 3: dbt trigger vs wait-for-completion
**What goes wrong:** Using `trigger_dbt_cloud_job_run` (fire-and-forget) instead of `trigger_dbt_cloud_job_run_and_wait_for_completion`.
**Why it happens:** The non-waiting version looks simpler.
**How to avoid:** `DbtCloudRunJobOperator` always waits for completion (`wait_for_termination=True` by default). The Prefect equivalent that matches this behavior is `trigger_dbt_cloud_job_run_and_wait_for_completion`.

### Pitfall 4: Jinja `{{ prev_ds }}` treated as simple translation
**What goes wrong:** Translating `{{ prev_ds }}` as `scheduled_start_time - timedelta(days=1)` — this is only correct if the schedule interval is daily.
**Why it happens:** `prev_ds` looks like a simple date offset.
**How to avoid:** In the Colin model, explain that `prev_ds` assumes the DAG schedule interval. The correct Prefect pattern is to receive the previous date as a flow parameter (LLM extracts it from context) rather than computing it from the schedule.

### Pitfall 5: schedule in `prefect.yaml` at wrong YAML level
**What goes wrong:** Placing `schedules:` at the top level of `prefect.yaml` instead of under the deployment entry.
**Why it happens:** Confusion between Prefect 2 and Prefect 3 YAML schemas; Prefect 2 had top-level `schedule:`.
**How to avoid:** In Prefect 3, schedules live under `deployments[*].schedules`, not at the root. Use `schedules:` (plural) per the verified API ref.

### Pitfall 6: depends_on_past lookup returns `not_found`
**What goes wrong:** `lookup_concept("depends_on_past")` returns `not_found` with no useful guidance.
**Why it happens:** It is not in the current knowledge base.
**How to avoid:** The Colin model for `depends_on_past` must use `equivalent: none` with a `workaround` section so the lookup tool returns actionable content even for unmappable concepts.

## Code Examples

Verified patterns from official sources:

### AzureBlobStorageCredentials block setup
```python
# Source: https://docs.prefect.io/integrations/prefect-azure/api-ref/prefect_azure-blob_storage
from prefect_azure import AzureBlobStorageCredentials

# Connection string method
creds = AzureBlobStorageCredentials(
    connection_string="DefaultEndpointsProtocol=https;AccountName=myaccount;..."
)
creds.save("my-azure-blob-credentials")

# Service principal method
creds = AzureBlobStorageCredentials(
    account_url="https://myaccount.blob.core.windows.net/",
    tenant_id="your-tenant-id",
    client_id="your-client-id",
    client_secret="your-client-secret",
)
creds.save("my-azure-spn-credentials")
```

### dbt Cloud credentials block setup
```python
# Source: https://docs.prefect.io/integrations/prefect-dbt/api-ref/prefect_dbt-cloud-credentials
from prefect_dbt.cloud import DbtCloudCredentials

creds = DbtCloudCredentials(api_key="my_api_key", account_id=123456789)
creds.save("my-dbt-credentials")
```

### prefect.yaml schedule formats
```yaml
# Source: https://docs.prefect.io/v3/how-to-guides/deployments/create-schedules
deployments:
  - name: my-flow
    entrypoint: flows/my_flow.py:my_flow
    schedules:
      - cron: "0 6 * * *"         # cron string
      # OR
      - interval: 3600             # timedelta(hours=1) → 3600 seconds
      # OR
      # (omit schedules: entirely for None/@once)
```

### scaffold_project signature change
```python
async def scaffold_project(
    output_directory: str,
    project_name: str | None = None,
    include_docker: bool = True,
    include_github_actions: bool = True,
    schedule_interval: str | timedelta | None = None,  # NEW
) -> str:
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `prefect.yaml` top-level `schedule:` (Prefect 2) | `deployments[*].schedules:` (plural, Prefect 3) | Prefect 3.0 | Scaffold must use Prefect 3 schema |
| `DbtCloudRunJobOperator` waits by default | `trigger_dbt_cloud_job_run_and_wait_for_completion` equivalent | prefect-dbt current | Always use the `_and_wait_for_completion` variant to match default behavior |

**Deprecated/outdated:**
- `DbtCloudJob.trigger()` block pattern: still valid but more verbose than the task function; use `trigger_dbt_cloud_job_run_and_wait_for_completion` for direct migration
- `AzureBlobCredentials`: older class for flow code storage blocks; do NOT use for WasbOperator migration — use `AzureBlobStorageCredentials`

## Open Questions

1. **ADF polling in scaffold**
   - What we know: `AzureDataFactoryRunPipelineOperator` polls for pipeline completion using `azure_data_factory_conn_id`
   - What's unclear: Whether the Colin model should show a polling loop or just fire-and-forget + note about polling
   - Recommendation: Show a complete pattern with `PipelineRunClient.get_pipeline_run()` polling loop wrapped in the @task, with `@task(retries=3)` as a lightweight safety net

2. **Jinja `{{ var.value.x }}` normalization**
   - What we know: `var.value.x` in Airflow reads from Airflow Variables; Prefect has `Variable.get("x")`
   - What's unclear: Whether `lookup_concept` should strip `var.value.` prefix from queries
   - Recommendation (Claude's discretion): Yes — add query normalization in `knowledge.py` to strip common Jinja wrappers (`{{ }}`, `macros.`, `var.value.`) before lookup; this is a low-risk improvement with clear user benefit

3. **WasbDeleteOperator coverage**
   - What we know: KNOW-07 only mentions WasbOperator explicitly; WasbDeleteOperator is a common companion
   - What's unclear: Whether to include WasbDeleteOperator in the same Colin model file
   - Recommendation: Include `WasbDeleteOperator` as a second `{% section %}` in `azure.md` since it follows the same credential pattern and adds minimal scope

## Sources

### Primary (HIGH confidence)
- `https://docs.prefect.io/integrations/prefect-azure/api-ref/prefect_azure-blob_storage` — AzureBlobStorageCredentials, blob_storage_download, blob_storage_upload
- `https://docs.prefect.io/integrations/prefect-azure/index` — prefect-azure module list; confirmed no ADF module
- `https://docs.prefect.io/integrations/prefect-dbt/api-ref/prefect_dbt-cloud-jobs` — trigger_dbt_cloud_job_run_and_wait_for_completion, DbtCloudJob signatures
- `https://docs.prefect.io/integrations/prefect-dbt/api-ref/prefect_dbt-cloud-credentials` — DbtCloudCredentials block attributes and usage
- `https://docs.prefect.io/v3/how-to-guides/deployments/create-schedules` — prefect.yaml schedules section format (Prefect 3)
- `https://docs.prefect.io/v3/concepts/schedules` — Cron, Interval, RRule schedule types
- Existing `/Users/gcoyne/src/prefect/airflow-unfactor/colin/models/patterns.md` — existing jinja-ds-to-runtime and jinja-params-to-flow-params patterns
- Existing `/Users/gcoyne/src/prefect/airflow-unfactor/colin/models/concepts.md` — schedule-cron section confirms cron passthrough pattern

### Secondary (MEDIUM confidence)
- `https://docs.prefect.io/integrations/prefect-azure/api-ref/prefect_azure-credentials` — credential class list; AzureDataFactory not present (verified from multiple pages)
- `https://reference.prefect.io/prefect_azure/` — full module structure; no data_factory module
- Airflow docs for `AzureDataFactoryRunPipelineOperator` — confirmed operator behavior, parameters (pipeline_name, wait_for_termination, azure_data_factory_conn_id)
- Airflow docs for `WasbOperator`/`WasbHook` — confirmed wasb_conn_id, blob operations

### Tertiary (LOW confidence)
- None — all critical claims verified against official sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified against official Prefect docs; ADF gap confirmed from multiple sources
- Architecture: HIGH — Colin model format confirmed from Phase 1 code; schedule YAML format verified from Prefect 3 docs
- Pitfalls: HIGH — ADF module absence confirmed; credential class naming verified; schedule YAML level confirmed from docs

**Research date:** 2026-02-26
**Valid until:** 2026-08-26 (stable Prefect 3 docs; prefect-azure/dbt APIs tend not to change frequently)

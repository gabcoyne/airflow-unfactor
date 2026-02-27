---
name: dbt Provider Operator Mappings
colin:
  output:
    format: json
---

{% section DbtCloudRunJobOperator %}
## operator
DbtCloudRunJobOperator

## module
airflow.providers.dbt.cloud.operators.dbt

## intent
Triggers a dbt Cloud job and waits for it to complete. Used in DAGs that orchestrate dbt transformations as part of an ELT pipeline — for example, running a dbt Cloud job after raw data loads into the warehouse, before downstream reporting or analytics tasks execute. The operator handles the trigger-then-poll lifecycle and surfaces job logs on failure.

## source_context
Operator uses `dbt_cloud_conn_id`, `job_id`, `account_id` (optional, defaults to connection value), `trigger_reason` (string label for the triggered run), and `wait_for_termination` (True by default). It calls the dbt Cloud API to trigger a job run, then polls until the run reaches a terminal state, raising `AirflowException` on failure. The `account_id` in Airflow is stored in the dbt Cloud connection alongside the API token.

## prefect_pattern
`trigger_dbt_cloud_job_run_and_wait_for_completion` from `prefect_dbt.cloud.jobs` with a `DbtCloudCredentials` block. The credentials block stores the dbt Cloud API key and account ID — load it by name in your flow. The function handles the full trigger-then-poll lifecycle, matching `DbtCloudRunJobOperator`'s default `wait_for_termination=True` behavior.

## prefect_package
prefect-dbt[cloud]

## prefect_import
from prefect import flow
from prefect_dbt.cloud import DbtCloudCredentials
from prefect_dbt.cloud.jobs import trigger_dbt_cloud_job_run_and_wait_for_completion

## example
### before
```python
from airflow.providers.dbt.cloud.operators.dbt import DbtCloudRunJobOperator

run_dbt_job = DbtCloudRunJobOperator(
    task_id="run_dbt_transformations",
    dbt_cloud_conn_id="dbt_cloud_default",
    job_id=12345,
    trigger_reason="Triggered by Airflow DAG daily_elt",
    wait_for_termination=True,
)
```
### after
```python
from prefect import flow, task
from prefect_dbt.cloud import DbtCloudCredentials
from prefect_dbt.cloud.jobs import trigger_dbt_cloud_job_run_and_wait_for_completion

@flow
def run_dbt_transformations(job_id: int = 12345):
    credentials = DbtCloudCredentials.load("my-dbt-credentials")
    result = trigger_dbt_cloud_job_run_and_wait_for_completion(
        dbt_cloud_credentials=credentials,
        job_id=job_id,
        trigger_reason="Triggered by Prefect flow daily_elt",
        retry_filtered_models_attempts=3,
    )
    return result
```

## notes
- Use `trigger_dbt_cloud_job_run_and_wait_for_completion` NOT the fire-and-forget `trigger_dbt_cloud_job_run` — `DbtCloudRunJobOperator` waits by default (`wait_for_termination=True`), so use the function that matches that behavior
- Install: `uv pip install "prefect-dbt[cloud]"`
- Credential block setup (run once before deploying):
  ```python
  from prefect_dbt.cloud import DbtCloudCredentials
  creds = DbtCloudCredentials(api_key="dbt_api_key_here", account_id=123456789)
  creds.save("my-dbt-credentials")
  ```
- The `account_id` lives in the `DbtCloudCredentials` block — you do not need to pass it separately to the task function (it is read from the block)
- `retry_filtered_models_attempts` re-runs only the failed models, not the full job — set to 0 to disable, or 1-3 for typical usage
- If the dbt Cloud job fails, `trigger_dbt_cloud_job_run_and_wait_for_completion` raises an exception with job run details — no need to add your own polling error handling
- For Cosmos/dbt Core (running dbt CLI commands, not dbt Cloud): that pattern is separate — use `DbtCoreOperation` from `prefect_dbt.core` or the `prefect-dbt` Cosmos integration; `DbtCloudRunJobOperator` specifically maps to the Cloud API approach

## related_concepts
- prefect-dbt-cloud
- dbt-cloud-credentials
- trigger-and-wait-pattern
{% endsection %}

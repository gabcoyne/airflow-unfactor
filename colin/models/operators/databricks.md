---
name: Databricks Provider Operator Mappings
colin:
  output:
    format: json
---

{% section DatabricksSubmitRunOperator %}
## operator
DatabricksSubmitRunOperator

## module
airflow.providers.databricks.operators.databricks

## source_context
Submits a new Databricks job run via the Runs Submit API. Takes a JSON payload defining cluster config, notebook/jar/python task, and libraries. Uses databricks_conn_id for workspace auth. Polls for completion.

## prefect_pattern
prefect-databricks jobs_runs_submit task

## prefect_package
prefect-databricks

## prefect_import
from prefect_databricks import DatabricksCredentials; from prefect_databricks.jobs import jobs_runs_submit

## example
### before
```python
from airflow.providers.databricks.operators.databricks import DatabricksSubmitRunOperator

submit_run = DatabricksSubmitRunOperator(
    task_id="run_notebook",
    databricks_conn_id="databricks_default",
    json={
        "new_cluster": {"spark_version": "13.3.x-scala2.12", "num_workers": 2},
        "notebook_task": {"notebook_path": "/Users/me/my_notebook"},
    },
)
```
### after
```python
from prefect import task
from prefect_databricks import DatabricksCredentials
from prefect_databricks.jobs import jobs_runs_submit

@task
def run_notebook(notebook_path: str):
    credentials = DatabricksCredentials.load("databricks-default")
    run = jobs_runs_submit(
        databricks_credentials=credentials,
        json={
            "new_cluster": {"spark_version": "13.3.x-scala2.12", "num_workers": 2},
            "notebook_task": {"notebook_path": notebook_path},
        },
    )
    return run
```

## notes
- databricks_conn_id → create a DatabricksCredentials block, load with DatabricksCredentials.load("block-name")
- The JSON payload structure is identical between Airflow and Prefect — pass it through directly
- prefect-databricks handles polling for run completion automatically
- Do NOT use raw requests calls to the Databricks REST API; the package handles auth, polling, and error translation
- For notebook params with Jinja templates like {{ ds }}: replace with explicit Python parameters passed to the @task

## related_concepts
- connection-to-block
- databricks-credentials
{% endsection %}

{% section DatabricksRunNowOperator %}
## operator
DatabricksRunNowOperator

## module
airflow.providers.databricks.operators.databricks

## source_context
Triggers an existing Databricks job by job_id via the Run Now API. Takes job_id and optional notebook_params, jar_params, or python_params. Uses databricks_conn_id for auth. Polls for completion.

## prefect_pattern
prefect-databricks jobs_run_now task

## prefect_package
prefect-databricks

## prefect_import
from prefect_databricks import DatabricksCredentials; from prefect_databricks.jobs import jobs_run_now

## example
### before
```python
from airflow.providers.databricks.operators.databricks import DatabricksRunNowOperator

run_job = DatabricksRunNowOperator(
    task_id="trigger_job",
    databricks_conn_id="databricks_default",
    job_id=12345,
    notebook_params={"date": "{{ ds }}"},
)
```
### after
```python
from prefect import task
from prefect_databricks import DatabricksCredentials
from prefect_databricks.jobs import jobs_run_now

@task
def trigger_databricks_job(job_id: int, date: str):
    credentials = DatabricksCredentials.load("databricks-default")
    run = jobs_run_now(
        databricks_credentials=credentials,
        job_id=job_id,
        notebook_params={"date": date},
    )
    return run
```

## notes
- Same credential migration as DatabricksSubmitRunOperator: databricks_conn_id → DatabricksCredentials block
- job_id is a direct parameter mapping — no transformation needed
- notebook_params with {{ ds }} → replace with explicit date parameter passed to the @task
- Do NOT hardcode conn_id strings; always load credentials from a block
- prefect-databricks handles polling for run completion automatically

## related_concepts
- connection-to-block
- databricks-credentials
{% endsection %}

---
name: Spark Provider Operator Mappings
colin:
  output:
    format: json
---

{% section SparkSubmitOperator %}
## operator
SparkSubmitOperator

## module
airflow.providers.apache.spark.operators.spark_submit

## source_context
Submits a Spark application using spark-submit CLI. Takes application path, conf dict, deploy_mode, executor_memory, driver_memory, and other spark-submit flags. Uses conn_id for Spark cluster connection.

## prefect_pattern
Option 1 (self-managed Spark): ShellOperation with spark-submit CLI. Option 2 (managed Spark via Databricks): DatabricksSubmitRun with spark_python_task. Option 3 (managed Spark via GCP): Dataproc job submission.

## prefect_package
prefect-shell (Option 1), prefect-databricks (Option 2), prefect-gcp (Option 3)

## prefect_import
from prefect_shell import ShellOperation

## example
### before
```python
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

spark_job = SparkSubmitOperator(
    task_id="run_spark",
    application="/opt/spark/jobs/etl.py",
    conn_id="spark_default",
    conf={"spark.sql.shuffle.partitions": "200"},
    deploy_mode="cluster",
    executor_memory="4g",
)
```
### after
```python
# Option 1: Self-managed Spark cluster — spark-submit via ShellOperation
from prefect import task
from prefect_shell import ShellOperation

@task
def run_spark_job(application: str):
    result = ShellOperation(
        commands=[
            f"spark-submit "
            f"--conf spark.sql.shuffle.partitions=200 "
            f"--deploy-mode cluster "
            f"--executor-memory 4g "
            f"{application}"
        ],
        stream_output=True,
    ).run()
    return result

# Option 2: Managed Spark via Databricks (preferred if available)
from prefect import task
from prefect_databricks import DatabricksCredentials
from prefect_databricks.jobs import jobs_runs_submit

@task
def run_spark_on_databricks(script_path: str):
    credentials = DatabricksCredentials.load("databricks-default")
    run = jobs_runs_submit(
        databricks_credentials=credentials,
        json={
            "new_cluster": {"spark_version": "13.3.x-scala2.12", "num_workers": 4},
            "spark_python_task": {"python_file": script_path},
        },
    )
    return run
```

## notes
- THREE execution paths — choose based on infrastructure:
  1. Self-managed Spark cluster: Use ShellOperation with spark-submit (requires spark-submit on PATH)
  2. Databricks-managed Spark: Use prefect-databricks DatabricksSubmitRun with spark_python_task
  3. GCP Dataproc: Use prefect-gcp DataprocSubmitJob
- ShellOperation with stream_output=True preserves Spark logs in Prefect's log view
- Do NOT use subprocess.run or os.system — ShellOperation integrates with Prefect logging and observability
- spark_conn_id → for self-managed: configure Spark master URL as environment variable or Secret block
- For conf dict: pass as spark-submit --conf flags in the command string (e.g., --conf key=value)
- executor_memory, driver_memory, num_executors → map directly to spark-submit flags

## related_concepts
- shell-operation-pattern
- managed-spark-alternative
{% endsection %}

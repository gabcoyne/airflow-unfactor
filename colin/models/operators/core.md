---
name: Core Airflow Operator Mappings
colin:
  output:
    format: json
---

{% section PythonOperator %}
## operator
PythonOperator

## module
airflow.operators.python

## source_context
Executes an arbitrary Python callable. The `execute()` method calls `self.python_callable` with `op_args` and `op_kwargs`. Supports templates in args.

## prefect_pattern
@task decorated function

## prefect_package
prefect

## prefect_import
from prefect import task

## example
### before
```python
def extract_data(source, limit=100):
    return fetch(source, limit)

task = PythonOperator(
    task_id="extract",
    python_callable=extract_data,
    op_kwargs={"source": "api", "limit": 500},
)
```
### after
```python
@task
def extract(source: str, limit: int = 100):
    return fetch(source, limit)
```

## notes
- The python_callable becomes the decorated function body
- op_args become positional function parameters
- op_kwargs become keyword function parameters
- provide_context=True is not needed; use Prefect runtime context instead

## related_concepts
- operator-to-task
- xcom-to-return-values
{% endsection %}

{% section BashOperator %}
## operator
BashOperator

## module
airflow.operators.bash

## source_context
Executes a bash command via subprocess. The `execute()` method runs `bash_command` in a subprocess and captures output. Supports Jinja templating in the command string.

## prefect_pattern
ShellOperation.run() or subprocess

## prefect_package
prefect-shell

## prefect_import
from prefect_shell import ShellOperation

## example
### before
```python
task = BashOperator(
    task_id="dump_db",
    bash_command="pg_dump mydb > /tmp/backup.sql",
    env={"PGPASSWORD": "{{ var.value.db_password }}"},
)
```
### after
```python
from prefect_shell import ShellOperation

@task
def dump_db():
    ShellOperation(commands=["pg_dump mydb > /tmp/backup.sql"]).run()
```

## notes
- bash_command becomes the commands list
- env vars can be passed to ShellOperation
- For simple commands, subprocess.run() is also fine
- Jinja templates in commands must be replaced with Python string formatting

## related_concepts
- operator-to-task
- jinja-ds-to-runtime
{% endsection %}

{% section PythonVirtualenvOperator %}
## operator
PythonVirtualenvOperator

## module
airflow.operators.python

## source_context
Creates a temporary virtualenv, installs requirements, serializes the callable and args, runs in the venv, and deserializes the result.

## prefect_pattern
Subprocess with venv or Docker task

## prefect_package
prefect

## prefect_import
from prefect import task

## example
### before
```python
task = PythonVirtualenvOperator(
    task_id="ml_train",
    python_callable=train_model,
    requirements=["scikit-learn==1.3.0"],
)
```
### after
```python
@task
def ml_train():
    import subprocess
    subprocess.run(["pip", "install", "scikit-learn==1.3.0"], check=True)
    train_model()
```

## notes
- Consider using a Docker-based work pool for isolated environments
- Requirements can be baked into a Dockerfile for the deployment
- For simple cases, install packages at task runtime
{% endsection %}

{% section EmptyOperator %}
## operator
EmptyOperator

## module
airflow.operators.empty

## source_context
No-op operator used as a dependency anchor point. The `execute()` method does nothing.

## prefect_pattern
Remove entirely or use a pass-through task

## prefect_package
prefect

## prefect_import
from prefect import task

## example
### before
```python
start = EmptyOperator(task_id="start")
end = EmptyOperator(task_id="end")
start >> [task_a, task_b] >> end
```
### after
```python
@flow
def pipeline():
    # No need for start/end markers
    a = task_a()
    b = task_b()
```

## notes
- Usually safe to remove entirely
- If used as join point, the flow function's control flow handles this naturally
- DummyOperator is an alias for EmptyOperator
{% endsection %}

{% section BranchPythonOperator %}
## operator
BranchPythonOperator

## module
airflow.operators.python

## source_context
Executes a Python callable that returns the task_id(s) of the branch(es) to follow. All other downstream tasks are skipped.

## prefect_pattern
Python if/else in the flow function

## prefect_package
prefect

## prefect_import
from prefect import flow

## example
### before
```python
def choose_branch(**context):
    if context['params']['env'] == 'prod':
        return 'deploy_prod'
    return 'deploy_staging'

branch = BranchPythonOperator(task_id="branch", python_callable=choose_branch)
branch >> [deploy_prod, deploy_staging]
```
### after
```python
@flow
def pipeline(env: str = "staging"):
    if env == "prod":
        deploy_prod()
    else:
        deploy_staging()
```

## notes
- No skip semantics needed; just don't call the unused branch
- The branching callable's logic becomes regular Python control flow

## related_concepts
- branch-to-conditional
{% endsection %}

{% section ShortCircuitOperator %}
## operator
ShortCircuitOperator

## module
airflow.operators.python

## source_context
Evaluates a callable; if it returns False, all downstream tasks are skipped.

## prefect_pattern
Early return from flow function

## prefect_package
prefect

## prefect_import
from prefect import flow

## example
### before
```python
check = ShortCircuitOperator(
    task_id="check_data",
    python_callable=has_new_data,
)
check >> process >> load
```
### after
```python
@flow
def pipeline():
    if not has_new_data():
        return
    data = process()
    load(data)
```

## notes
- Replace with early return or conditional in flow function
- No skip propagation needed

## related_concepts
- short-circuit-to-early-return
{% endsection %}

{% section TriggerDagRunOperator %}
## operator
TriggerDagRunOperator

## module
airflow.operators.trigger_dagrun

## source_context
Triggers a run of another DAG, optionally passing a conf dict and waiting for completion.

## prefect_pattern
run_deployment() or subflow call

## prefect_package
prefect

## prefect_import
from prefect.deployments import run_deployment

## example
### before
```python
trigger = TriggerDagRunOperator(
    task_id="trigger_etl",
    trigger_dag_id="downstream_etl",
    conf={"date": "{{ ds }}"},
    wait_for_completion=True,
)
```
### after
```python
from prefect.deployments import run_deployment

@task
def trigger_etl(date: str):
    run_deployment(
        name="downstream-etl/default",
        parameters={"date": date},
        timeout=3600,
    )
```

## notes
- If target is in same codebase, call as subflow instead
- conf dict maps to deployment parameters
- wait_for_completion maps to timeout parameter

## related_concepts
- trigger-dag-to-run-deployment
{% endsection %}

{% section EmailOperator %}
## operator
EmailOperator

## module
airflow.operators.email

## source_context
Sends an email using the configured SMTP connection. Supports HTML body and attachments.

## prefect_pattern
email_send_message from prefect-email

## prefect_package
prefect-email

## prefect_import
from prefect_email import email_send_message, EmailServerCredentials

## example
### before
```python
email = EmailOperator(
    task_id="send_report",
    to="team@company.com",
    subject="Daily Report",
    html_content="<h1>Report</h1>",
)
```
### after
```python
from prefect_email import email_send_message, EmailServerCredentials

@task
def send_report():
    creds = EmailServerCredentials.load("email-default")
    email_send_message(
        email_server_credentials=creds,
        subject="Daily Report",
        msg="<h1>Report</h1>",
        email_to="team@company.com",
    )
```
{% endsection %}

{% section LatestOnlyOperator %}
## operator
LatestOnlyOperator

## module
airflow.operators.latest_only

## source_context
Skips downstream tasks if the DAG run is not for the most recent schedule interval.

## prefect_pattern
No direct equivalent — Prefect does not backfill by default

## prefect_package
prefect

## prefect_import
from prefect import flow

## example
### before
```python
latest_only = LatestOnlyOperator(task_id="latest_only")
latest_only >> deploy_task
```
### after
```python
# Not needed — Prefect deployments run from creation time
# If backfill is enabled, check runtime context:
from prefect import runtime

@task
def deploy():
    # Only deploy if this is the latest run
    ...
```

## notes
- Usually safe to remove entirely
- Prefect doesn't have backfill-by-default behavior
{% endsection %}

{% section ExternalTaskSensor %}
## operator
ExternalTaskSensor

## module
airflow.sensors.external_task

## source_context
Waits for a task in another DAG to complete. Polls the Airflow metadata database for task instance state.

## prefect_pattern
Event-driven automation or run_deployment with wait

## prefect_package
prefect

## prefect_import
from prefect.events import emit_event

## example
### before
```python
wait = ExternalTaskSensor(
    task_id="wait_for_upstream",
    external_dag_id="upstream_dag",
    external_task_id="final_task",
    poke_interval=60,
    timeout=3600,
)
```
### after
```python
# Option 1: Call upstream as subflow
# Option 2: Event-driven
from prefect.events import emit_event

# In upstream flow:
emit_event(event="upstream.complete", resource={"prefect.resource.id": "upstream-dag"})

# In downstream: create automation triggered by "upstream.complete" event
```

## notes
- Prefer direct subflow calls when both flows are in the same codebase
- For cross-deployment dependencies, use events and automations
- Polling approach: use a task with retries that checks deployment status

## related_concepts
- sensor-to-polling
- trigger-dag-to-run-deployment
{% endsection %}

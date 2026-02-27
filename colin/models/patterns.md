---
name: Airflow to Prefect Pattern Translations
colin:
  output:
    format: json
---

{% section taskgroup-to-subflow %}
## id
taskgroup-to-subflow

## airflow_pattern
TaskGroup — groups tasks visually and logically in the DAG UI.

## prefect_pattern
Subflow — a nested `@flow` function that contains related tasks.

## rules
- Replace `with TaskGroup("group_name") as group:` with a `@flow`-decorated function
- Tasks inside the group become `@task` calls within the subflow
- TaskGroup prefix behavior (e.g., `group.task_id`) is not needed in Prefect
- Nested TaskGroups become nested subflows

## example
### before
```python
with TaskGroup("transform") as transform_group:
    clean = PythonOperator(task_id="clean", ...)
    validate = PythonOperator(task_id="validate", ...)
    clean >> validate
```
### after
```python
@flow
def transform():
    cleaned = clean()
    validate(cleaned)
```
{% endsection %}

{% section trigger-rule-to-state %}
## id
trigger-rule-to-state

## airflow_pattern
trigger_rule — controls when a task runs based on upstream task states (all_success, all_failed, one_success, etc.).

## prefect_pattern
State inspection with `return_state=True` — check upstream task states explicitly in Python.

## rules
- `all_success` (default): no change needed, Prefect tasks fail on upstream failure by default
- `all_failed`: use `return_state=True` on upstream tasks, check `state.is_failed()`
- `one_success`: run tasks concurrently, check results with `any()`
- `all_done`: use `return_state=True` to always get a result regardless of state
- `none_failed`: check `not state.is_failed()` for each upstream
- Complex trigger rules: use explicit Python if/else with state inspection

## example
### before
```python
cleanup = PythonOperator(
    task_id="cleanup",
    trigger_rule="all_done",
    python_callable=cleanup_fn,
)
```
### after
```python
@task
def cleanup():
    cleanup_fn()

@flow
def pipeline():
    result = process.submit(return_state=True)
    # cleanup runs regardless of process state
    cleanup()
```
{% endsection %}

{% section jinja-ds-to-runtime %}
## id
jinja-ds-to-runtime

## airflow_pattern
`{{ ds }}`, `{{ ds_nodash }}`, `{{ execution_date }}` — Jinja template variables for execution date.

## prefect_pattern
`runtime.flow_run.scheduled_start_time` — access scheduled time from Prefect runtime context.

## rules
- `{{ ds }}` → `runtime.flow_run.scheduled_start_time.strftime("%Y-%m-%d")`
- `{{ ds_nodash }}` → `runtime.flow_run.scheduled_start_time.strftime("%Y%m%d")`
- `{{ execution_date }}` → `runtime.flow_run.scheduled_start_time`
- `{{ next_ds }}` → compute from scheduled_start_time + interval
- `{{ prev_ds }}` → compute from scheduled_start_time - interval
- Import: `from prefect import runtime`

## example
### before
```python
BashOperator(
    task_id="export",
    bash_command="dump_db --date {{ ds }}",
)
```
### after
```python
from prefect import task, runtime

@task
def export():
    ds = runtime.flow_run.scheduled_start_time.strftime("%Y-%m-%d")
    subprocess.run(["dump_db", "--date", ds])
```
{% endsection %}

{% section jinja-params-to-flow-params %}
## id
jinja-params-to-flow-params

## airflow_pattern
`{{ params.x }}` — Jinja template variable for DAG params.

## prefect_pattern
Flow function parameters with type annotations.

## rules
- `{{ params.x }}` → flow function parameter `x`
- DAG `params={"x": "default"}` → function default `def flow(x: str = "default")`
- Params are passed at deployment trigger time or via `flow.serve()` API

## example
### before
```python
dag = DAG("pipeline", params={"env": "prod", "limit": 1000})
task = BashOperator(
    bash_command="run --env {{ params.env }} --limit {{ params.limit }}",
)
```
### after
```python
@flow
def pipeline(env: str = "prod", limit: int = 1000):
    run(env=env, limit=limit)
```
{% endsection %}

{% section dynamic-mapping %}
## id
dynamic-mapping

## airflow_pattern
`.expand()` — dynamic task mapping that creates task instances at runtime based on input.

## prefect_pattern
`.map()` — maps a task over an iterable, creating concurrent task runs.

## rules
- `task.expand(arg=values)` → `task.map(values)`
- `task.expand(arg1=v1, arg2=v2)` → `task.map(v1, v2)` (parallel iteration)
- `partial(fixed=val).expand(varying=list)` → use `functools.partial` or pass fixed args
- Mapped task results are a list that can be passed to downstream tasks
- Use `.submit()` for concurrent execution with futures

## example
### before
```python
process = PythonOperator.partial(task_id="process", python_callable=process_fn)
process.expand(op_args=[[1], [2], [3]])
```
### after
```python
@task
def process(item):
    return process_fn(item)

@flow
def pipeline():
    results = process.map([1, 2, 3])
```
{% endsection %}

{% section branch-to-conditional %}
## id
branch-to-conditional

## airflow_pattern
BranchPythonOperator — conditionally selects which downstream task(s) to execute.

## prefect_pattern
Python if/else — use standard control flow in the flow function.

## rules
- Replace BranchPythonOperator with a plain Python function that returns the branch decision
- Use if/else in the flow to call the appropriate tasks
- No need for skip semantics — just don't call the unused branch
- For complex branching: use a task that returns a decision value

## example
### before
```python
def choose_branch(**context):
    if context['params']['env'] == 'prod':
        return 'deploy_prod'
    return 'deploy_staging'

branch = BranchPythonOperator(task_id="branch", python_callable=choose_branch)
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
{% endsection %}

{% section short-circuit-to-early-return %}
## id
short-circuit-to-early-return

## airflow_pattern
ShortCircuitOperator — skips all downstream tasks if condition is False.

## prefect_pattern
Early return from the flow function.

## rules
- Replace ShortCircuitOperator with a conditional check + `return` in the flow
- If condition is False, return early from the flow
- No skip semantics needed — the flow simply ends

## example
### before
```python
check = ShortCircuitOperator(
    task_id="check_data",
    python_callable=lambda: has_new_data(),
)
check >> process >> load
```
### after
```python
@flow
def pipeline():
    if not has_new_data():
        return  # short-circuit
    data = process()
    load(data)
```
{% endsection %}

{% section trigger-dag-to-run-deployment %}
## id
trigger-dag-to-run-deployment

## airflow_pattern
TriggerDagRunOperator — triggers another DAG run, optionally passing configuration.

## prefect_pattern
`run_deployment()` — triggers a deployed flow, or call a subflow directly.

## rules
- If the target DAG is in the same codebase: call it as a subflow
- If the target DAG is a separate deployment: use `run_deployment()`
- `conf` parameter → deployment parameters
- `wait_for_completion=True` → `run_deployment(..., timeout=N)`

## example
### before
```python
trigger = TriggerDagRunOperator(
    task_id="trigger_downstream",
    trigger_dag_id="downstream_pipeline",
    conf={"date": "{{ ds }}"},
    wait_for_completion=True,
)
```
### after
```python
from prefect.deployments import run_deployment

@task
def trigger_downstream(date: str):
    run_deployment(
        name="downstream-pipeline/default",
        parameters={"date": date},
        timeout=3600,
    )
```
{% endsection %}

{% section default-args-to-task-defaults %}
## id
default-args-to-task-defaults

## airflow_pattern
`default_args` — dict of default parameters applied to all operators in a DAG.

## prefect_pattern
Shared `@task` decorator defaults or a custom task decorator.

## rules
- `retries` → `@task(retries=N)` on each task, or create a custom decorator
- `retry_delay` → `@task(retry_delay_seconds=N)`
- `email_on_failure` → use `on_failure` hooks or automations
- `owner` → use tags or flow metadata
- `depends_on_past` → no direct equivalent; use state inspection if needed
- Create a reusable task decorator for shared defaults

## example
### before
```python
default_args = {
    "owner": "data-team",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": True,
}
dag = DAG("pipeline", default_args=default_args)
```
### after
```python
from functools import partial
from prefect import task

# Shared defaults via partial
etl_task = partial(task, retries=3, retry_delay_seconds=300)

@etl_task
def extract(): ...

@etl_task
def transform(): ...
```
{% endsection %}

{% section callbacks-to-hooks %}
## id
callbacks-to-hooks

## airflow_pattern
`on_success_callback`, `on_failure_callback`, `sla_miss_callback` — functions called on state changes.

## prefect_pattern
State change hooks and automations.

## rules
- `on_failure_callback` → `@flow(on_failure=[handler])` or `@task(on_failure=[handler])`
- `on_success_callback` → `@flow(on_completion=[handler])` (check state)
- `sla_miss_callback` → Prefect automations with SLA-type triggers
- Hook signature: `def hook(flow, flow_run, state)` for flows, `def hook(task, task_run, state)` for tasks
- For complex alerting: use Prefect automations (UI/API configured)

## example
### before
```python
def notify_failure(context):
    send_alert(f"Task {context['task_instance'].task_id} failed")

dag = DAG("pipeline", on_failure_callback=notify_failure)
```
### after
```python
def notify_failure(flow, flow_run, state):
    send_alert(f"Flow {flow_run.name} failed: {state.message}")

@flow(on_failure=[notify_failure])
def pipeline():
    ...
```
{% endsection %}

{% section jinja-template-variables %}
## id
jinja-template-variables

## airflow_pattern
Jinja2 template variables rendered by Airflow's template engine at task execution time. Operators accept template fields where `{{ variable }}` syntax is evaluated before the operator runs.

## prefect_pattern
Pure Python via `prefect.runtime` module, flow parameters, and `prefect.variables`. No template engine — write Python directly. Import `from prefect import runtime` and access the runtime context as a regular object.

## rules
- `{{ ds }}` → `runtime.flow_run.scheduled_start_time.strftime("%Y-%m-%d")`
  - Intent: the logical execution date as a date string. In Airflow this is the start of the schedule interval; in Prefect use `scheduled_start_time`.
- `{{ ts }}` → `runtime.flow_run.scheduled_start_time.isoformat()`
  - Intent: the full ISO 8601 timestamp of the scheduled run.
- `{{ execution_date }}` → `runtime.flow_run.scheduled_start_time`
  - Intent: a datetime object for the scheduled run time. In Prefect this is a `datetime` with timezone.
- `{{ ds_nodash }}` → `runtime.flow_run.scheduled_start_time.strftime("%Y%m%d")`
  - Intent: date string without separators, useful for file paths and partition keys.
- `{{ run_id }}` → `runtime.flow_run.name` or `str(runtime.flow_run.id)`
  - Intent: a unique identifier for this specific run. `flow_run.name` is human-readable; `flow_run.id` is the UUID.
- `{{ dag_run.conf }}` → flow function parameters (typed)
  - Intent: runtime configuration passed when triggering the DAG/flow. In Prefect, pass as typed flow parameters rather than an untyped dict.
- `{{ params.x }}` → flow function parameter `x`
  - Intent: a DAG-level parameter with a default value. Becomes a typed function parameter.
- `{{ var.value.x }}` → `Variable.get("x")` from `prefect.variables`
  - Intent: a globally stored configuration value. Import `from prefect.variables import Variable`.
- `{{ macros.ds_add(ds, N) }}` → `(datetime.strptime(ds, "%Y-%m-%d") + timedelta(days=N)).strftime("%Y-%m-%d")`
  - Intent: add N days to a date string. Use `from datetime import datetime, timedelta` directly.
- `{{ macros.ds_format(ds, input_format, output_format) }}` → `datetime.strptime(ds, input_format).strftime(output_format)`
  - Intent: reformat a date string. Pure Python datetime.
- `{{ macros.datetime }}` → `from datetime import datetime`
  - Intent: access to Python's datetime class. Use it directly in your code.
- `{{ macros.timedelta }}` → `from datetime import timedelta`
  - Intent: access to Python's timedelta class. Use it directly in your code.
- `{{ task_instance.task_id }}` → `runtime.task_run.task_name` (within a `@task`)
  - Intent: the name of the currently running task. Access from `prefect.runtime` inside a `@task`.
- `{{ next_ds }}` and `{{ prev_ds }}` — PARADIGM SHIFT: Prefect flows don't own their schedule — the deployment does. There is no built-in `next_ds` or `prev_ds`. If the interval matters, pass it as a flow parameter: `def my_flow(scheduled_date: datetime, interval_days: int = 1)`. Compute next/prev from `scheduled_start_time` and the interval parameter.

## example
### before
```python
def process(**context):
    ds = context["ds"]                          # "2024-01-15"
    ds_nodash = context["ds_nodash"]            # "20240115"
    run_id = context["run_id"]                  # "scheduled__2024-01-15T00:00:00+00:00"
    env = context["params"]["env"]              # "prod"
    api_key = Variable.get("api_key")           # Airflow Variable
    next_date = macros.ds_add(ds, 7)            # "2024-01-22"

BashOperator(
    task_id="export",
    bash_command="dump --date {{ ds }} --env {{ params.env }}",
)
```
### after
```python
from datetime import datetime, timedelta
from prefect import flow, task, runtime
from prefect.variables import Variable

@task
def process(env: str, api_key: str):
    ds = runtime.flow_run.scheduled_start_time.strftime("%Y-%m-%d")
    ds_nodash = runtime.flow_run.scheduled_start_time.strftime("%Y%m%d")
    run_id = runtime.flow_run.name
    next_date = (datetime.strptime(ds, "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d")
    # Use ds, ds_nodash, run_id, next_date as plain Python strings
    subprocess.run(["dump", "--date", ds, "--env", env])

@flow
def my_flow(env: str = "prod"):
    api_key = Variable.get("api_key")
    process(env=env, api_key=api_key)
```
{% endsection %}

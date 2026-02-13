---
layout: page
title: Trigger Rules
permalink: /conversion/trigger-rules/
---

# Trigger Rules

Convert Airflow's `trigger_rule` parameter to Prefect state-based patterns.

## What We Detect

| Trigger Rule | Description |
|--------------|-------------|
| `all_success` | Run if all upstreams succeeded (default) |
| `all_done` | Run after all upstreams complete, regardless of state |
| `all_failed` | Run only if all upstreams failed |
| `one_failed` | Run if any upstream failed |
| `one_success` | Run if any upstream succeeded |
| `none_failed` | Run if no upstreams failed |
| `none_failed_min_one_success` | No failures and at least one success |

## What We Generate

### all_success (Default)

```python
# Airflow
task_a >> task_b  # task_b has trigger_rule="all_success" by default

# Prefect (converted) - No special handling needed
@flow
def my_flow():
    a_result = task_a()
    b_result = task_b(a_result)  # Runs only if task_a succeeds
```

### all_done

```python
# Airflow
cleanup = CleanupOperator(task_id="cleanup", trigger_rule="all_done")
task_a >> cleanup
task_b >> cleanup

# Prefect (converted)
from prefect.states import State

@task
def cleanup(upstream_states: list[State]):
    """Runs regardless of upstream success/failure."""
    failed = [s for s in upstream_states if s.is_failed()]
    print(f"Cleaning up. {len(failed)} upstream tasks failed.")
    # cleanup logic here

@flow
def my_flow():
    # Capture states instead of results
    state_a = task_a(return_state=True)
    state_b = task_b(return_state=True)

    # Pass states to all_done task
    cleanup([state_a, state_b])
```

### one_failed

```python
# Airflow
alert = AlertOperator(task_id="alert", trigger_rule="one_failed")
task_a >> alert
task_b >> alert

# Prefect (converted)
@task
def alert_on_failure(upstream_states: list[State]):
    """Runs if ANY upstream failed."""
    if any(s.is_failed() for s in upstream_states):
        send_alert("At least one task failed!")
        return "alert sent"
    return "no failures"

@flow
def my_flow():
    state_a = task_a(return_state=True)
    state_b = task_b(return_state=True)
    alert_on_failure([state_a, state_b])
```

### all_failed

```python
# Airflow
fallback = FallbackOperator(task_id="fallback", trigger_rule="all_failed")

# Prefect (converted)
@task
def fallback_handler(upstream_states: list[State]):
    """Runs only if ALL upstreams failed."""
    if all(s.is_failed() for s in upstream_states):
        return run_fallback_logic()
    return None  # Skip if any succeeded

@flow
def my_flow():
    state_a = task_a(return_state=True)
    state_b = task_b(return_state=True)
    fallback_handler([state_a, state_b])
```

### none_failed

```python
# Airflow
proceed = NextOperator(task_id="proceed", trigger_rule="none_failed")

# Prefect (converted)
@task
def proceed_if_no_failures(upstream_states: list[State]):
    """Runs if no upstreams failed (success or skipped OK)."""
    if not any(s.is_failed() for s in upstream_states):
        return do_next_step()
    raise Exception("Cannot proceed - upstream failures detected")
```

## Known Deltas

| Airflow Feature | Prefect Behavior | Notes |
|-----------------|------------------|-------|
| Declarative rules | Imperative state checks | More explicit, more flexible |
| `trigger_rule` on sensor | Use state hooks | Sensors become polling tasks |
| Skipped state propagation | Manual handling | Check for `None` returns |
| `none_skipped` | Check result is not None | No native skip state |

## Manual Follow-up

1. **Review state handling logic** — Generated code uses explicit state checks. Verify the logic matches your intent.

2. **Consider using hooks** — For simple cases, `@flow.on_failure` or `@task.on_failure` hooks may be cleaner.

3. **Test failure scenarios** — Run tests with intentional failures to verify trigger rule behavior.

## Alternative: State Change Hooks

For notification-style trigger rules, Prefect hooks are often cleaner:

```python
def notify_on_failure(flow, flow_run, state):
    send_slack(f"Flow {flow.name} failed!")

def notify_on_success(flow, flow_run, state):
    send_slack(f"Flow {flow.name} completed!")

@flow(on_failure=[notify_on_failure], on_completion=[notify_on_success])
def my_flow():
    # No need for trigger_rule tasks
    task_a()
    task_b()
```

## Alternative: Automations

For complex trigger logic, Prefect Automations provide declarative, UI-configurable reactions:

```yaml
# Create via Prefect UI or API
automation:
  name: "Alert on any task failure"
  trigger:
    match:
      prefect.resource.id: "prefect.flow-run.*"
    expect:
      - "prefect.flow-run.Failed"
  actions:
    - type: send-notification
      block_document_id: slack-webhook-id
```

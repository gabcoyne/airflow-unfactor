---
title: Prefect Cloud Integration
---

# Prefect Cloud Integration

Leverage Prefect Cloud features for production deployments of migrated flows.

## Work Pools and Workers

Migrated runbooks include work pool recommendations. Choose based on your needs:

### Process Work Pool

Best for: Local development, simple flows, quick iteration.

```bash
# Create the work pool
prefect work-pool create "my-flow-pool" --type process

# Start a worker
prefect worker start --pool "my-flow-pool"
```

### Docker Work Pool

Best for: Production deployments, isolated environments, reproducible builds.

```bash
# Create the work pool
prefect work-pool create "my-flow-pool" --type docker

# Start a worker
prefect worker start --pool "my-flow-pool"
```

Configure in `prefect.yaml`:
```yaml
deployments:
  - name: my-etl
    work_pool:
      name: "my-flow-pool"
    build:
      - prefect_docker.deployments.steps.build_docker_image:
          image_name: "my-registry/my-flow"
          dockerfile: "Dockerfile"
```

### Kubernetes Work Pool

Best for: Kubernetes clusters, auto-scaling, cloud-native deployments.

```bash
# Create the work pool
prefect work-pool create "my-flow-pool" --type kubernetes

# Deploy workers via Helm
helm install prefect-worker prefect/prefect-worker \
  --set worker.config.workPool="my-flow-pool"
```

## Automations for Callbacks

Replace Airflow callbacks with Prefect Automations for robust alerting.

### Failure Notifications (on_failure_callback)

```python
from prefect.automations import Automation
from prefect.events.schemas.automations import EventTrigger
from prefect.events.actions import SendNotification

failure_automation = Automation(
    name="my-flow-failure-alert",
    description="Alert on flow failures",
    trigger=EventTrigger(
        match={"prefect.resource.id": "prefect.flow-run.*"},
        expect=["prefect.flow-run.Failed"],
        posture="Reactive",
        threshold=1,
    ),
    actions=[
        SendNotification(
            block_document_id="your-slack-webhook-block-id",
            subject="Flow Failed",
            body="{{ flow_run.name }} has failed. Check logs for details.",
        )
    ],
)
```

**Via Prefect UI:**
1. Navigate to Automations → Create Automation
2. Trigger: Flow run enters "Failed" state
3. Action: Send notification (Slack, Email, PagerDuty, etc.)

### Success Notifications (on_success_callback)

```python
success_automation = Automation(
    name="my-flow-success-alert",
    description="Notify on successful completion",
    trigger=EventTrigger(
        match={"prefect.resource.id": "prefect.flow-run.*"},
        expect=["prefect.flow-run.Completed"],
        posture="Reactive",
        threshold=1,
    ),
    actions=[
        SendNotification(
            block_document_id="your-slack-webhook-block-id",
            subject="Flow Completed",
            body="{{ flow_run.name }} completed successfully.",
        )
    ],
)
```

### SLA Monitoring (sla_miss_callback)

```python
from datetime import timedelta

sla_automation = Automation(
    name="my-flow-sla-monitor",
    description="Alert when flow exceeds expected duration",
    trigger=EventTrigger(
        match={"prefect.resource.id": "prefect.flow-run.*"},
        expect=["prefect.flow-run.Running"],
        posture="Proactive",
        threshold=1,
        within=timedelta(hours=2),  # SLA threshold
    ),
    actions=[
        SendNotification(
            block_document_id="your-slack-webhook-block-id",
            subject="SLA Breach Warning",
            body="Flow has been running longer than expected.",
        )
    ],
)
```

## Concurrency Management

Replace Airflow's `pool` and `pool_slots` with Prefect concurrency controls.

### Work Pool Concurrency

Limit concurrent flow runs in a work pool:

```bash
prefect work-pool update my-pool --concurrency-limit 5
```

### Global Concurrency Limits

For cross-flow resource management:

```bash
# Create a concurrency limit
prefect concurrency-limit create "database-connections" 10
```

Use in your flow:

```python
from prefect import flow
from prefect.concurrency.sync import concurrency

@flow
def my_flow():
    with concurrency("database-connections", occupy=1):
        # Database operations here
        pass
```

### Task Concurrency

Limit concurrent task executions:

```python
from prefect import flow, task
from prefect.task_runners import ConcurrentTaskRunner

@task
def process_item(item):
    return transform(item)

@flow(task_runner=ConcurrentTaskRunner(max_workers=3))
def my_flow():
    items = get_items()
    results = process_item.map(items)
    return results
```

## Secrets and Blocks

Replace Airflow connections with Prefect Blocks.

### Database Connections

```python
from prefect_sqlalchemy import SqlAlchemyConnector, ConnectionComponents

# Create the block
db_block = SqlAlchemyConnector(
    connection_info=ConnectionComponents(
        driver="postgresql+psycopg2",
        host="your-host",
        port=5432,
        database="your-db",
        username="your-user",
        password="your-password",  # Or use Secret block
    )
)
db_block.save("postgres-prod")

# Use in your flow
@task
def query_database():
    connector = SqlAlchemyConnector.load("postgres-prod")
    with connector.get_connection() as conn:
        return conn.execute("SELECT * FROM users").fetchall()
```

### Cloud Provider Credentials

**AWS:**
```python
from prefect_aws import AwsCredentials

aws_creds = AwsCredentials(
    aws_access_key_id="your-key-id",
    aws_secret_access_key="your-secret-key",
    region_name="us-east-1",
)
aws_creds.save("aws-prod")
```

**GCP:**
```python
from prefect_gcp import GcpCredentials

gcp_creds = GcpCredentials(
    service_account_file="/path/to/service-account.json",
)
gcp_creds.save("gcp-prod")
```

### Secret Values

For sensitive values that shouldn't be in code:

```python
from prefect.blocks.system import Secret

# Create via UI or API
api_key = Secret(value="your-secret-api-key")
api_key.save("api-key")

# Use in flow
@task
def call_api():
    api_key = Secret.load("api-key")
    return requests.get(url, headers={"Authorization": api_key.get()})
```

## Observability and Alerting

### Flow Run Logs

All flow/task logs are automatically captured:

```python
from prefect import flow, task, get_run_logger

@task
def my_task():
    logger = get_run_logger()
    logger.info("Processing started")
    logger.warning("Something to watch")
    logger.error("Something went wrong")
```

View logs in Prefect Cloud UI or via CLI:

```bash
prefect flow-run logs <flow-run-id>
```

### Custom Metrics

Emit custom metrics with artifacts:

```python
from prefect import flow, task
from prefect.artifacts import create_markdown_artifact

@task
def process_data():
    results = {"processed": 1000, "errors": 5}

    create_markdown_artifact(
        key="processing-summary",
        markdown=f"""
        # Processing Summary

        - Processed: {results['processed']}
        - Errors: {results['errors']}
        - Error rate: {results['errors']/results['processed']:.2%}
        """,
    )

    return results
```

### Dashboard Integration

Prefect Cloud provides built-in dashboards. For external tools:

```python
# Send metrics to Datadog, Prometheus, etc.
from prefect import flow
import datadog

@flow
def my_flow():
    result = do_work()

    # Report to Datadog
    datadog.statsd.gauge("prefect.flow.items_processed", result["count"])
    datadog.statsd.increment("prefect.flow.runs", tags=["status:success"])
```

## Deployment Configuration

### prefect.yaml

Full deployment configuration:

```yaml
name: my-migrated-flows

deployments:
  - name: etl-daily
    entrypoint: "flows/etl.py:etl_flow"
    work_pool:
      name: "production-pool"
    schedules:
      - cron: "0 2 * * *"
        timezone: "UTC"
    parameters:
      batch_size: 1000
    tags: ["production", "etl"]

  - name: ml-training
    entrypoint: "flows/ml.py:training_flow"
    work_pool:
      name: "gpu-pool"
    schedules:
      - cron: "0 0 * * 0"  # Weekly
        timezone: "UTC"
    tags: ["production", "ml"]
```

### Deploy All

```bash
# Deploy all deployments
prefect deploy --all

# Deploy specific deployment
prefect deploy --name "etl-daily"
```

## Best Practices

1. **Use work pools** — Match pool type to execution environment
2. **Configure automations** — Don't rely on polling for alerts
3. **Use Blocks for secrets** — Never hardcode credentials
4. **Set concurrency limits** — Protect shared resources
5. **Tag deployments** — Enable filtering and organization
6. **Monitor with artifacts** — Create visibility into flow execution
7. **Use prefect.yaml** — Version control your deployment config

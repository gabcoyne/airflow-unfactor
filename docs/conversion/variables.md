---
layout: page
title: Variables & Secrets
permalink: /conversion/variables/
---

# Variables to Config

Convert Airflow Variables to Prefect Variables, Secrets, or flow parameters.

## What We Detect

| Pattern | Description |
|---------|-------------|
| `Variable.get("name")` | Read variable |
| `Variable.get("name", default_var="x")` | Read with default |
| `Variable.set("name", value)` | Write variable |
| `models.Variable.get("name")` | Alternative import |

## Migration Strategy

We analyze variable names to recommend the appropriate Prefect equivalent:

| Variable Name Pattern | Recommendation | Reason |
|----------------------|----------------|--------|
| Contains `key`, `password`, `secret`, `token` | Prefect Secret | Sensitive data |
| Contains `credential`, `auth`, `private` | Prefect Secret | Sensitive data |
| Has default value, read-only | Flow parameter | Deployment-time config |
| Dynamic read/write | Prefect Variable | Runtime state |
| Simple config | Environment variable | Infrastructure config |

## What We Generate

### Sensitive Variables → Secrets

```python
# Airflow
api_key = Variable.get("api_key")
db_password = Variable.get("database_password")

# Prefect (converted)
from prefect.blocks.system import Secret

@task
def call_api():
    # Create Secret block first (see setup instructions)
    api_key = Secret.load("api-key").get()
    # Use api_key...
```

### Config Variables → Flow Parameters

```python
# Airflow
max_retries = Variable.get("max_retries", default_var="3")
environment = Variable.get("environment", default_var="prod")

# Prefect (converted)
@flow
def my_flow(
    max_retries: int = 3,
    environment: str = "prod"
):
    # Parameters set at deployment time or per-run
    process(retries=max_retries, env=environment)
```

### Dynamic Variables → Prefect Variables

```python
# Airflow
last_processed = Variable.get("last_processed_id")
Variable.set("last_processed_id", new_id)

# Prefect (converted)
from prefect.variables import Variable

@task
def process_incremental():
    # Read current state
    last_id = Variable.get("last_processed_id", default="0")

    # Process new records
    new_id = process_since(int(last_id))

    # Update state for next run
    Variable.set("last_processed_id", str(new_id))
    return new_id
```

## Setup Instructions

### Secrets (Prefect UI)

1. Navigate to **Blocks** → **Add Block**
2. Select **Secret**
3. Enter the secret value
4. Name it (e.g., `api-key`)
5. Save

### Secrets (CLI)

```bash
# Create via Python
python -c "
from prefect.blocks.system import Secret
Secret(value='your-secret-value').save('api-key')
"
```

### Variables (Prefect UI)

1. Navigate to **Variables**
2. Click **Add Variable**
3. Enter name and value
4. Save

### Variables (CLI)

```bash
# Create variable
prefect variable set last_processed_id "0"

# Read variable
prefect variable get last_processed_id
```

### Flow Parameters (Deployment)

```yaml
# prefect.yaml
deployments:
  - name: my-flow
    parameters:
      max_retries: 5
      environment: "staging"
```

Or via CLI:
```bash
prefect deployment run my-flow/main --param max_retries=5 --param environment=staging
```

## Complete Mapping

| Airflow Pattern | Prefect Equivalent | When to Use |
|----------------|-------------------|-------------|
| `Variable.get("secret_key")` | `Secret.load("x").get()` | Sensitive data |
| `Variable.get("config", "default")` | Flow parameter | Static config |
| `Variable.get/set("state")` | `Variable.get/set()` | Runtime state |
| `Variable.get("setting")` | `os.environ["SETTING"]` | Infrastructure config |

## Known Deltas

| Airflow Feature | Prefect Behavior | Notes |
|-----------------|------------------|-------|
| JSON serialization | String values | Serialize/deserialize manually |
| Variable masking | Secret blocks | Use Secret for sensitive data |
| Variable history | No built-in history | Use external audit if needed |
| Bulk import/export | API or CLI | `prefect variable ls` |

## Manual Follow-up

1. **Audit variable sensitivity** — Review generated recommendations. Err on the side of using Secrets.

2. **Create Secrets before running** — Flows fail if Secrets don't exist.

3. **Consider migration order** — Create all Variables/Secrets before deploying migrated flows.

4. **Update Variable.set patterns** — If your DAG writes variables, the Prefect pattern is async-friendly but similar.

## Example: Configuration-Driven ETL

```python
from prefect import flow, task
from prefect.blocks.system import Secret
from prefect.variables import Variable

@task
def extract(source_table: str):
    # Use Secret for database credentials
    db_url = Secret.load("source-db-url").get()
    return query_table(db_url, source_table)

@task
def transform(data, multiplier: float):
    return [row * multiplier for row in data]

@task
def load(data, destination: str):
    # Track progress with Variable
    last_count = int(Variable.get("rows_loaded", default="0"))
    new_count = last_count + len(data)
    Variable.set("rows_loaded", str(new_count))
    return write_to(destination, data)

@flow
def configurable_etl(
    source_table: str = "orders",      # Flow parameter
    destination: str = "warehouse",     # Flow parameter
    multiplier: float = 1.0            # Flow parameter
):
    raw = extract(source_table)
    transformed = transform(raw, multiplier)
    load(transformed, destination)
```

## Security Considerations

1. **Never log secrets** — Prefect masks Secret values in logs
2. **Use Prefect Cloud** — Secrets encrypted at rest
3. **Rotate regularly** — Update Secret blocks when rotating credentials
4. **Least privilege** — Service accounts should only access needed secrets

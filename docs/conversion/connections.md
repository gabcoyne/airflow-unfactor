---
layout: page
title: Connections & Blocks
permalink: /conversion/connections/
---

# Connections to Blocks

Convert Airflow Connections to Prefect Blocks for type-safe credential management.

## What We Detect

| Pattern | Description |
|---------|-------------|
| `PostgresHook(postgres_conn_id="x")` | Hook instantiation |
| `BaseHook.get_connection("x")` | Direct connection access |
| `SomeOperator(conn_id="x")` | Operator connection parameter |
| `*_conn_id` parameters | Any connection ID reference |

## What We Generate

### Database Connections

```python
# Airflow
from airflow.providers.postgres.hooks.postgres import PostgresHook

def extract_data(ti):
    hook = PostgresHook(postgres_conn_id="my_postgres")
    return hook.get_records("SELECT * FROM users")

# Prefect (converted)
from prefect_sqlalchemy import SqlAlchemyConnector

@task
def extract_data():
    """Query database using Prefect Block."""
    # Block must be created first (see setup instructions below)
    connector = SqlAlchemyConnector.load("my-postgres")
    return connector.fetch_all("SELECT * FROM users")
```

### Cloud Connections

```python
# Airflow - AWS
from airflow.providers.amazon.aws.hooks.s3 import S3Hook

hook = S3Hook(aws_conn_id="aws_default")
data = hook.read_key("data.json", "my-bucket")

# Prefect (converted)
from prefect_aws import S3Bucket

@task
def read_from_s3():
    s3 = S3Bucket.load("my-s3-bucket")
    return s3.read_path("data.json")
```

```python
# Airflow - GCP
from airflow.providers.google.cloud.hooks.bigquery import BigQueryHook

hook = BigQueryHook(gcp_conn_id="google_cloud_default")

# Prefect (converted)
from prefect_gcp import GcpCredentials, BigQueryWarehouse

@task
def query_bigquery():
    gcp = GcpCredentials.load("my-gcp-creds")
    bq = BigQueryWarehouse(gcp_credentials=gcp)
    return bq.fetch_all("SELECT * FROM dataset.table")
```

## Connection Type Mapping

| Airflow Type | Prefect Block | Package |
|--------------|---------------|---------|
| `postgres` | `SqlAlchemyConnector` | `prefect-sqlalchemy` |
| `mysql` | `SqlAlchemyConnector` | `prefect-sqlalchemy` |
| `snowflake` | `SnowflakeConnector` | `prefect-snowflake` |
| `aws` / `s3` | `AwsCredentials`, `S3Bucket` | `prefect-aws` |
| `google_cloud` | `GcpCredentials` | `prefect-gcp` |
| `bigquery` | `BigQueryWarehouse` | `prefect-gcp` |
| `azure` | `AzureBlobStorageCredentials` | `prefect-azure` |
| `slack` | `SlackWebhook` | `prefect-slack` |
| `http` | `httpx` directly | (stdlib) |
| `ssh` / `sftp` | `paramiko` directly | `paramiko` |

## Setup Instructions

### Via Prefect UI

1. Navigate to **Blocks** in Prefect UI
2. Click **Add Block**
3. Select block type (e.g., `SqlAlchemyConnector`)
4. Fill in connection details
5. Name it (e.g., `my-postgres`)
6. Save

### Via CLI

```bash
# Install integration package
pip install prefect-sqlalchemy

# Register block types
prefect block register -m prefect_sqlalchemy

# Create block via Python
python -c "
from prefect_sqlalchemy import SqlAlchemyConnector, ConnectionComponents

connector = SqlAlchemyConnector(
    connection_info=ConnectionComponents(
        driver='postgresql+psycopg2',
        host='localhost',
        port=5432,
        database='mydb',
        username='user',
        password='secret'  # Use environment variable in production
    )
)
connector.save('my-postgres', overwrite=True)
"
```

### Via Environment Variables

For simpler cases, use environment variables:

```python
import os
from sqlalchemy import create_engine

@task
def query_db():
    url = os.environ["DATABASE_URL"]  # Set in deployment
    engine = create_engine(url)
    # ...
```

## Known Deltas

| Airflow Feature | Prefect Behavior | Notes |
|-----------------|------------------|-------|
| Connection extras JSON | Block fields | Typed, validated fields |
| Connection URI | Block with components | More structured |
| UI connection test | Block test methods | `connector.fetch_one("SELECT 1")` |
| Connection secrets in DB | Encrypted in Prefect Cloud | Or use secret managers |

## Manual Follow-up

1. **Create Blocks before running** — Generated code assumes Blocks exist. Create them via UI or CLI.

2. **Review credential storage** — Don't hardcode secrets. Use Prefect Cloud encryption or external secret managers.

3. **Test connectivity** — After creating Blocks, test with simple queries before full runs.

4. **Update error handling** — Prefect Blocks raise different exceptions than Airflow Hooks.

## Example: Multi-Database ETL

```python
from prefect import flow, task
from prefect_sqlalchemy import SqlAlchemyConnector
from prefect_snowflake import SnowflakeConnector

@task
def extract_from_postgres():
    pg = SqlAlchemyConnector.load("source-postgres")
    return pg.fetch_all("SELECT * FROM orders WHERE date = CURRENT_DATE")

@task
def load_to_snowflake(data: list):
    sf = SnowflakeConnector.load("target-snowflake")
    sf.execute_many(
        "INSERT INTO orders (id, amount, date) VALUES (%(id)s, %(amount)s, %(date)s)",
        data
    )

@flow(name="postgres_to_snowflake")
def postgres_to_snowflake():
    data = extract_from_postgres()
    load_to_snowflake(data)
```

## Security Best Practices

1. **Use Prefect Cloud** — Credentials encrypted at rest
2. **Rotate credentials** — Update Blocks when rotating passwords
3. **Least privilege** — Create service accounts with minimal permissions
4. **Audit access** — Prefect Cloud logs Block usage

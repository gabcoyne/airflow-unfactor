---
name: Airflow Sensor to Prefect Mappings
colin:
  output:
    format: json
---

{% section FileSensor %}
## operator
FileSensor

## module
airflow.sensors.filesystem

## source_context
Polls for file existence at a given path. Supports glob patterns via `fs_conn_id`.

## prefect_pattern
Polling task with retries

## prefect_package
prefect

## prefect_import
from prefect import task

## example
### before
```python
wait = FileSensor(
    task_id="wait_for_file",
    filepath="/data/input.csv",
    poke_interval=60,
    timeout=3600,
)
```
### after
```python
from pathlib import Path

@task(retries=60, retry_delay_seconds=60)
def wait_for_file(filepath: str) -> str:
    if not Path(filepath).exists():
        raise FileNotFoundError(f"{filepath} not yet available")
    return filepath
```

## notes
- poke_interval maps to retry_delay_seconds
- timeout / poke_interval gives approximate retries count
- For glob patterns, use Path.glob() in the task
{% endsection %}

{% section S3KeySensor %}
## operator
S3KeySensor

## module
airflow.providers.amazon.aws.sensors.s3

## source_context
Polls for the existence of a key (object) in an S3 bucket. Uses boto3 `head_object` to check.

## prefect_pattern
S3Bucket check with retries

## prefect_package
prefect-aws

## prefect_import
from prefect_aws import S3Bucket

## example
### before
```python
wait = S3KeySensor(
    task_id="wait_for_s3",
    bucket_key="s3://my-bucket/data/output.parquet",
    aws_conn_id="aws_default",
    poke_interval=300,
    timeout=7200,
)
```
### after
```python
from prefect_aws import S3Bucket

@task(retries=24, retry_delay_seconds=300)
def wait_for_s3(key: str) -> str:
    bucket = S3Bucket.load("my-bucket")
    objects = bucket.list_objects(folder=key.rsplit("/", 1)[0])
    if not any(key in str(o) for o in objects):
        raise FileNotFoundError(f"S3 key {key} not yet available")
    return key
```

## notes
- wildcard_match in S3KeySensor: use prefix listing in Prefect
- For event-driven: use S3 event notifications → Prefect automation
{% endsection %}

{% section HttpSensor %}
## operator
HttpSensor

## module
airflow.providers.http.sensors.http

## source_context
Makes HTTP requests and checks the response. Default checks for 2xx status. Custom `response_check` callable for complex checks.

## prefect_pattern
HTTP polling task with retries

## prefect_package
prefect

## prefect_import
from prefect import task

## example
### before
```python
wait = HttpSensor(
    task_id="wait_for_api",
    http_conn_id="api",
    endpoint="status",
    response_check=lambda r: r.json()["ready"],
    poke_interval=30,
    timeout=600,
)
```
### after
```python
import httpx

@task(retries=20, retry_delay_seconds=30)
def wait_for_api(url: str) -> bool:
    resp = httpx.get(f"{url}/status")
    if not resp.json().get("ready"):
        raise Exception("API not ready")
    return True
```

## notes
- response_check callable becomes the conditional in the task
- http_conn_id credentials: store in a Secret block
{% endsection %}

{% section SqlSensor %}
## operator
SqlSensor

## module
airflow.sensors.sql

## source_context
Executes a SQL query and checks if it returns a truthy value. Pokes until the query returns non-empty/non-zero.

## prefect_pattern
SQL polling task with retries

## prefect_package
prefect-sqlalchemy

## prefect_import
from prefect_sqlalchemy import SqlAlchemyConnector

## example
### before
```python
wait = SqlSensor(
    task_id="wait_for_data",
    conn_id="postgres_default",
    sql="SELECT COUNT(*) FROM staging WHERE date = '{{ ds }}'",
    poke_interval=120,
    timeout=3600,
)
```
### after
```python
from prefect_sqlalchemy import SqlAlchemyConnector

@task(retries=30, retry_delay_seconds=120)
def wait_for_data(date: str) -> bool:
    connector = SqlAlchemyConnector.load("postgres-default")
    with connector.get_connection() as conn:
        result = conn.execute(
            text("SELECT COUNT(*) FROM staging WHERE date = :d"),
            {"d": date}
        ).scalar()
    if not result:
        raise Exception(f"No data for {date} yet")
    return True
```

## notes
- Jinja templates in SQL must be replaced with parameterized queries
- conn_id maps to the block name
{% endsection %}

{% section DateTimeSensor %}
## operator
DateTimeSensor

## module
airflow.sensors.date_time

## source_context
Waits until a specific datetime is reached. Uses `target_time` parameter.

## prefect_pattern
time.sleep or scheduled deployment

## prefect_package
prefect

## prefect_import
from prefect import task

## example
### before
```python
wait = DateTimeSensor(
    task_id="wait_until_noon",
    target_time="{{ execution_date.replace(hour=12) }}",
)
```
### after
```python
from datetime import datetime
import time

@task
def wait_until(target: datetime):
    now = datetime.now(target.tzinfo)
    if now < target:
        time.sleep((target - now).total_seconds())
```

## notes
- Consider using deployment schedules instead of sleep-based waiting
- For long waits, prefer scheduled deployment triggers
{% endsection %}

{% section GCSObjectExistenceSensor %}
## operator
GCSObjectExistenceSensor

## module
airflow.providers.google.cloud.sensors.gcs

## source_context
Polls Google Cloud Storage for the existence of an object. Uses `google.cloud.storage` client.

## prefect_pattern
GCS check with retries

## prefect_package
prefect-gcp

## prefect_import
from prefect_gcp import GcsBucket

## example
### before
```python
wait = GCSObjectExistenceSensor(
    task_id="wait_for_gcs",
    bucket="my-bucket",
    object="data/output.parquet",
    poke_interval=300,
)
```
### after
```python
from prefect_gcp import GcsBucket

@task(retries=24, retry_delay_seconds=300)
def wait_for_gcs(blob_name: str) -> str:
    bucket = GcsBucket.load("my-gcs-bucket")
    blobs = bucket.list_blobs(folder=blob_name.rsplit("/", 1)[0])
    if not any(blob_name in b for b in blobs):
        raise FileNotFoundError(f"GCS object {blob_name} not found")
    return blob_name
```
{% endsection %}

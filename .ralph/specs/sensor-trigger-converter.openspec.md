# OpenSpec: Sensor to Trigger Converter

## Overview
Convert Airflow Sensors to Prefect trigger suggestions and polling patterns.

## Requirements

### R1: Sensor Detection
Detect common sensors:
- `ExternalTaskSensor` → Event trigger or flow dependency
- `S3KeySensor` → S3 event trigger or polling task
- `HttpSensor` → Webhook or polling task
- `FileSensor` → Filesystem watch or polling
- `SqlSensor` → Polling task with query
- `PythonSensor` → Direct conversion to polling task

### R2: Conversion Strategy
| Airflow Sensor | Prefect Approach |
|----------------|------------------|
| ExternalTaskSensor | Event automation / flow.wait_for() |
| S3KeySensor | S3 event trigger (via SNS/SQS) or polling |
| HttpSensor | Webhook trigger or polling task |
| FileSensor | Watchdog or polling task |
| SqlSensor | Polling task with backoff |
| PythonSensor | @task with while loop + sleep |

### R3: Generated Patterns

**Polling Task (default):**
```python
import time
from prefect import task

@task(retries=60, retry_delay_seconds=60)
def wait_for_s3_key(bucket: str, key: str) -> bool:
    """Poll for S3 key existence."""
    import boto3
    s3 = boto3.client("s3")
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except s3.exceptions.ClientError:
        raise Exception(f"Key {key} not found, retrying...")
```

**Event-Driven (suggested):**
```yaml
# prefect.yaml deployment
triggers:
  - match: {"s3.bucket": "my-bucket", "s3.key": "data/*"}
    expect: ["s3.object.created"]
```

### R4: Output
- `polling_code`: Converted sensor as polling task
- `event_suggestion`: Recommended event-driven alternative
- `warnings`: Sensor-specific caveats

## Implementation Location
`src/airflow_unfactor/converters/sensors.py`

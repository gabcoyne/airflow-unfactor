---
name: HTTP Provider Operator Mappings
colin:
  output:
    format: json
---

{% section SimpleHttpOperator %}
## operator
SimpleHttpOperator

## module
airflow.providers.http.operators.http

## source_context
Calls an HTTP endpoint. Uses the requests library internally, takes http_conn_id for base URL and auth, supports response_check callable and log_response flag. Supports GET, POST, PUT, DELETE methods.

## prefect_pattern
httpx (or requests) inside @task — no dedicated Prefect HTTP package exists

## prefect_package
none (use httpx directly)

## prefect_import
import httpx

## example
### before
```python
import json
from airflow.providers.http.operators.http import SimpleHttpOperator

call_api = SimpleHttpOperator(
    task_id="call_api",
    http_conn_id="my_api",
    endpoint="/v1/process",
    method="POST",
    data=json.dumps({"key": "value"}),
    headers={"Content-Type": "application/json"},
    response_check=lambda response: response.status_code == 200,
    log_response=True,
)
```
### after
```python
import httpx
from prefect import task
from prefect.logging import get_run_logger
from prefect.blocks.system import Secret

@task(retries=3)
def call_api(endpoint: str, payload: dict) -> dict:
    logger = get_run_logger()
    base_url = Secret.load("my-api-base-url").get()  # replaces http_conn_id
    response = httpx.post(
        f"{base_url}{endpoint}",
        json=payload,
        headers={"Content-Type": "application/json"},
    )
    logger.info(response.text)   # replaces log_response=True
    response.raise_for_status()  # replaces response_check
    return response.json()
```

## notes
- There is NO prefect-http package; use httpx or requests directly inside @task
- http_conn_id → store base URL and credentials in a Secret block or environment variable
- response_check callable → implement as a conditional assertion or raise_for_status() inside the @task body
- log_response=True → use get_run_logger() to log response content
- httpx is preferred over requests for new Prefect code (async support, better timeout control)
- Use @task(retries=N) for retry behavior instead of custom retry loops
- Before running: create a Secret block for the base URL (and token if auth required)

## related_concepts
- connection-to-secret-block
- no-package-pattern
{% endsection %}

{% section HttpOperator %}
## operator
HttpOperator

## module
airflow.providers.http.operators.http

## source_context
The newer name in Airflow 2.x for SimpleHttpOperator. Identical behavior and parameters — calls an HTTP endpoint with http_conn_id, endpoint, method, data, headers, response_check, and log_response.

## prefect_pattern
httpx (or requests) inside @task — same pattern as SimpleHttpOperator

## prefect_package
none (use httpx directly)

## prefect_import
import httpx

## example
### before
```python
from airflow.providers.http.operators.http import HttpOperator

call_api = HttpOperator(
    task_id="call_api",
    http_conn_id="my_api",
    endpoint="/v1/data",
    method="GET",
    log_response=True,
)
```
### after
```python
import httpx
from prefect import task
from prefect.logging import get_run_logger
from prefect.blocks.system import Secret

@task(retries=3)
def call_api(endpoint: str) -> dict:
    logger = get_run_logger()
    base_url = Secret.load("my-api-base-url").get()
    response = httpx.get(f"{base_url}{endpoint}")
    logger.info(response.text)
    response.raise_for_status()
    return response.json()
```

## notes
- HttpOperator is the same class as SimpleHttpOperator (renamed in Airflow 2.x); apply the same translation
- There is NO prefect-http package; use httpx or requests directly inside @task
- See SimpleHttpOperator notes for full credential migration and retry guidance

## related_concepts
- connection-to-secret-block
- no-package-pattern
{% endsection %}

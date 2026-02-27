"""HTTP fixture DAG — SimpleHttpOperator with downstream processing task."""

from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.http.operators.http import SimpleHttpOperator

with DAG(
    dag_id="http_api_ingestion",
    start_date=datetime(2024, 1, 1),
    schedule_interval="@hourly",
    catchup=False,
) as dag:
    fetch_data = SimpleHttpOperator(
        task_id="fetch_api_data",
        http_conn_id="external_api_default",
        endpoint="/v1/events",
        method="GET",
        headers={"Authorization": "Bearer {{ var.value.api_token }}", "Accept": "application/json"},
        response_check=lambda response: response.status_code == 200,
        do_xcom_push=True,
    )

    process_response = PythonOperator(
        task_id="process_response",
        python_callable=lambda **ctx: print(ctx["ti"].xcom_pull(task_ids="fetch_api_data")),
    )

    fetch_data >> process_response

"""dbt Cloud fixture DAG — DbtCloudRunJobOperator with downstream notification task."""

from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.dbt.cloud.operators.dbt import DbtCloudRunJobOperator

with DAG(
    dag_id="dbt_cloud_daily_run",
    start_date=datetime(2024, 1, 1),
    schedule_interval="@daily",
    catchup=False,
) as dag:
    run_dbt_job = DbtCloudRunJobOperator(
        task_id="run_dbt_production",
        dbt_cloud_conn_id="dbt_cloud_default",
        job_id=12345,
        account_id=67890,
        trigger_reason="Triggered by Airflow DAG: dbt_cloud_daily_run",
        wait_for_termination=True,
    )

    notify_analytics = PythonOperator(
        task_id="notify_analytics_team",
        python_callable=lambda: print("dbt Cloud job finished, models refreshed"),
    )

    run_dbt_job >> notify_analytics

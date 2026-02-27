"""Databricks fixture DAG — DatabricksSubmitRunOperator with downstream PythonOperator."""

from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.databricks.operators.databricks import DatabricksSubmitRunOperator

with DAG(
    dag_id="databricks_notebook_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule_interval="@weekly",
    catchup=False,
) as dag:
    run_notebook = DatabricksSubmitRunOperator(
        task_id="run_feature_engineering",
        databricks_conn_id="databricks_default",
        json={
            "existing_cluster_id": "0123-456789-abc123",
            "notebook_task": {
                "notebook_path": "/Repos/data-team/feature_engineering",
                "base_parameters": {
                    "input_date": "{{ ds }}",
                    "output_table": "prod.features",
                },
            },
        },
    )

    notify = PythonOperator(
        task_id="notify_success",
        python_callable=lambda: print("Databricks job complete"),
    )

    run_notebook >> notify

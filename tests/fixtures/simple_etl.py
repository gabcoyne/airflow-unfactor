from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator


def extract_fn():
    return {"users": [1, 2, 3]}


def transform_fn(ti):
    data = ti.xcom_pull(task_ids="extract_data")
    return {"users": [u * 2 for u in data["users"]]}


def load_fn(ti):
    data = ti.xcom_pull(task_ids="transform_data")
    print(f"Loading {len(data['users'])} users")


with DAG(
    dag_id="simple_etl",
    start_date=datetime(2024, 1, 1),
    schedule_interval="@daily",
    catchup=False,
) as dag:
    extract = PythonOperator(
        task_id="extract_data",
        python_callable=extract_fn,
    )
    transform = PythonOperator(
        task_id="transform_data",
        python_callable=transform_fn,
    )
    load = PythonOperator(
        task_id="load_data",
        python_callable=load_fn,
    )

    extract >> transform >> load

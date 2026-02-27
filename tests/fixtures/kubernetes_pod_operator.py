"""Kubernetes fixture DAG — two KubernetesPodOperator tasks."""

from datetime import datetime

from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator

with DAG(
    dag_id="kubernetes_etl",
    start_date=datetime(2024, 1, 1),
    schedule_interval="@daily",
    catchup=False,
) as dag:
    extract = KubernetesPodOperator(
        task_id="extract_data",
        namespace="data-pipelines",
        image="myregistry/extractor:latest",
        cmds=["python", "extract.py"],
        env_vars={"DB_HOST": "postgres.internal", "DB_PORT": "5432"},
        get_logs=True,
    )

    transform = KubernetesPodOperator(
        task_id="transform_data",
        namespace="data-pipelines",
        image="myregistry/transformer:latest",
        cmds=["python", "transform.py"],
        env_vars={"INPUT_PATH": "/data/raw", "OUTPUT_PATH": "/data/processed"},
        get_logs=True,
    )

    extract >> transform

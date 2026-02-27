"""Azure fixture DAG — AzureDataFactoryRunPipelineOperator with downstream task."""

from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.microsoft.azure.operators.data_factory import (
    AzureDataFactoryRunPipelineOperator,
)

with DAG(
    dag_id="azure_adf_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule_interval="@daily",
    catchup=False,
) as dag:
    run_pipeline = AzureDataFactoryRunPipelineOperator(
        task_id="run_adf_pipeline",
        azure_data_factory_conn_id="azure_data_factory_default",
        resource_group_name="myResourceGroup",
        factory_name="myDataFactory",
        pipeline_name="CopyFromBlobToSQL",
        parameters={"inputContainer": "raw-data", "outputSchema": "dbo"},
        wait_for_termination=True,
    )

    record_completion = PythonOperator(
        task_id="record_completion",
        python_callable=lambda: print("ADF pipeline completed"),
    )

    run_pipeline >> record_completion

"""SSH fixture DAG — SSHOperator with downstream status check task."""

from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.ssh.operators.ssh import SSHOperator

with DAG(
    dag_id="ssh_remote_command",
    start_date=datetime(2024, 1, 1),
    schedule_interval="@daily",
    catchup=False,
) as dag:
    run_remote_script = SSHOperator(
        task_id="run_etl_on_remote",
        ssh_conn_id="remote_server_ssh",
        command="/opt/scripts/run_etl.sh --date {{ ds }} --env production",
        conn_timeout=30,
        cmd_timeout=600,
    )

    check_output = PythonOperator(
        task_id="verify_output_files",
        python_callable=lambda: print("Verifying remote ETL output files exist"),
    )

    run_remote_script >> check_output

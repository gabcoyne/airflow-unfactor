#!/usr/bin/env python
"""Example: Basic DAG conversion using airflow-unfactor.

This script demonstrates programmatic conversion without the MCP server.
"""

from airflow_unfactor.analysis.parser import parse_dag
from airflow_unfactor.analysis.version import detect_airflow_version
from airflow_unfactor.converters.base import convert_dag_to_flow

# Example Airflow DAG
AIRFLOW_DAG = '''
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

def extract():
    return {"users": [1, 2, 3], "products": [10, 20, 30]}

def transform(**context):
    ti = context["ti"]
    data = ti.xcom_pull(task_ids="extract")
    return {
        "user_count": len(data["users"]),
        "product_count": len(data["products"]),
    }

def load(**context):
    ti = context["ti"]
    metrics = ti.xcom_pull(task_ids="transform")
    print(f"Loaded metrics: {metrics}")

with DAG(
    dag_id="etl_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
) as dag:
    t1 = PythonOperator(task_id="extract", python_callable=extract)
    t2 = PythonOperator(task_id="transform", python_callable=transform)
    t3 = PythonOperator(task_id="load", python_callable=load)
    
    t1 >> t2 >> t3
'''


def main():
    print("=" * 60)
    print("airflow-unfactor: Basic Conversion Example")
    print("=" * 60)
    print()
    
    # Step 1: Detect Airflow version
    print("Step 1: Detecting Airflow version...")
    version = detect_airflow_version(AIRFLOW_DAG)
    print(f"  Detected: {version}")
    print()
    
    # Step 2: Parse the DAG
    print("Step 2: Parsing DAG structure...")
    analysis = parse_dag(AIRFLOW_DAG)
    print(f"  DAG ID: {analysis['dag_id']}")
    print(f"  Operators: {len(analysis['operators'])}")
    print(f"  Tasks: {analysis['task_ids']}")
    print(f"  Notes: {analysis['notes']}")
    print()
    
    # Step 3: Convert to Prefect flow
    print("Step 3: Converting to Prefect flow...")
    result = convert_dag_to_flow(analysis, AIRFLOW_DAG)
    print()
    print("Converted Flow Code:")
    print("-" * 40)
    print(result["flow_code"])
    print("-" * 40)
    print()
    
    if result.get("warnings"):
        print("Warnings:")
        for warning in result["warnings"]:
            print(f"  ⚠️  {warning}")
    
    print()
    print("\u2728 Conversion complete!")


if __name__ == "__main__":
    main()

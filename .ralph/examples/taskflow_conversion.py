#!/usr/bin/env python
"""Example: TaskFlow API conversion using airflow-unfactor.

Demonstrates conversion of modern Airflow 2.x TaskFlow DAGs.
"""

from airflow_unfactor.analysis.version import detect_airflow_version
from airflow_unfactor.converters.taskflow import (
    extract_taskflow_info,
    convert_taskflow_to_prefect,
)

# Modern TaskFlow DAG
TASKFLOW_DAG = '''
from airflow.decorators import dag, task
from datetime import datetime

@dag(
    dag_id="taskflow_etl",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["etl", "example"],
)
def taskflow_etl():
    """ETL pipeline using TaskFlow API."""
    
    @task
    def extract():
        """Extract data from source."""
        return {
            "users": ["alice", "bob", "charlie"],
            "orders": [100, 200, 150],
        }
    
    @task
    def transform(data: dict):
        """Transform the extracted data."""
        return {
            "total_users": len(data["users"]),
            "total_revenue": sum(data["orders"]),
            "avg_order": sum(data["orders"]) / len(data["orders"]),
        }
    
    @task
    def load(metrics: dict):
        """Load metrics to destination."""
        print(f"Loading metrics: {metrics}")
        return True
    
    raw_data = extract()
    metrics = transform(raw_data)
    load(metrics)

taskflow_etl()
'''


def main():
    print("=" * 60)
    print("airflow-unfactor: TaskFlow Conversion Example")
    print("=" * 60)
    print()
    
    # Detect version
    version = detect_airflow_version(TASKFLOW_DAG)
    print(f"Detected: {version}")
    print()
    
    # Extract TaskFlow info
    print("Extracting TaskFlow patterns...")
    dags, tasks = extract_taskflow_info(TASKFLOW_DAG)
    
    for dag in dags:
        print(f"  DAG: {dag.name} (function: {dag.function_name})")
        for task in dag.tasks:
            print(f"    Task: {task.name} (bash={task.is_bash})")
    print()
    
    # Convert
    print("Converting to Prefect...")
    result = convert_taskflow_to_prefect(TASKFLOW_DAG)
    
    print()
    print("Converted Code:")
    print("-" * 40)
    print(result["flow_code"])
    print("-" * 40)
    
    if result["warnings"]:
        print()
        print("Warnings:")
        for w in result["warnings"]:
            print(f"  ⚠️  {w}")
    
    print()
    print("Task Mapping:")
    for airflow_name, prefect_name in result["mapping"].items():
        print(f"  {airflow_name} \u2192 {prefect_name}")


if __name__ == "__main__":
    main()

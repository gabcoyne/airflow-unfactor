"""Prefect flow converted from Airflow DAG: complex_dag_structure_rainbow

✨ Converted by airflow-unfactor

Key differences from Airflow:
- Tasks are regular Python functions with @task decorator
- Data passes directly between tasks (no XCom database)
- Dependencies are implicit via function calls
- Retries and logging are built into decorators
"""

from prefect import flow, task

# ✨ Prefect Advantage: Simple Task Definition
# No need for PythonOperator wrapper — just decorate your function.
# The @task decorator handles retries, logging, and state management.

# ✨ Prefect Advantage: Flow as Function
# No DAG class, no context managers, no >> operators.
# Just call tasks in order — Prefect tracks dependencies automatically.

@flow(name="complex_dag_structure_rainbow")
def complex_dag_structure_rainbow():
    """Main flow - converted from Airflow DAG."""
    pass


if __name__ == "__main__":
    complex_dag_structure_rainbow()
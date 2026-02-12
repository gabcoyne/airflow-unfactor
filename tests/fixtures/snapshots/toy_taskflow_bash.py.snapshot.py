"""Prefect flow converted from Airflow DAG: toy_taskflow_bash

✨ Converted by airflow-unfactor

Key differences from Airflow:
- Tasks are regular Python functions with @task decorator
- Data passes directly between tasks (no XCom database)
- Dependencies are implicit via function calls
- Retries and logging are built into decorators
"""

from prefect import flow, task

# ✨ Prefect Advantage: Flow as Function
# No DAG class, no context managers, no >> operators.
# Just call tasks in order — Prefect tracks dependencies automatically.

@flow(name="toy_taskflow_bash")
def toy_taskflow_bash():
    """Main flow - converted from Airflow DAG."""
    pass


if __name__ == "__main__":
    toy_taskflow_bash()
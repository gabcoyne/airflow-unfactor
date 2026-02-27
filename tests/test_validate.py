"""Tests for validate tool."""

import asyncio
import json
from pathlib import Path

import pytest

from airflow_unfactor.tools.validate import validate_conversion

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestValidateConversion:
    """Tests for validate_conversion function."""

    def test_valid_pair_by_path(self, tmp_path):
        """Both files valid Python — syntax_valid true, sources returned."""
        dag = tmp_path / "dag.py"
        dag.write_text("from airflow import DAG\ndag = DAG('test')\n")

        flow = tmp_path / "flow.py"
        flow.write_text("from prefect import flow\n\n@flow\ndef test(): pass\n")

        result = json.loads(asyncio.run(validate_conversion(str(dag), str(flow))))

        assert result["syntax_valid"] is True
        assert result["syntax_errors"] is None
        assert "from airflow import DAG" in result["original_source"]
        assert "@flow" in result["converted_source"]
        assert "comparison_guidance" in result

    def test_syntax_error_in_flow(self, tmp_path):
        """Syntax error in generated flow is reported."""
        dag = tmp_path / "dag.py"
        dag.write_text("x = 1\n")

        flow = tmp_path / "flow.py"
        flow.write_text("def broken(\n")

        result = json.loads(asyncio.run(validate_conversion(str(dag), str(flow))))

        assert result["syntax_valid"] is False
        assert result["syntax_errors"] is not None
        assert len(result["syntax_errors"]) == 1
        assert "line" in result["syntax_errors"][0]
        assert "message" in result["syntax_errors"][0]

    def test_inline_content(self):
        """Inline content (not paths) is accepted."""
        dag_code = "from airflow import DAG\ndag = DAG('test')"
        flow_code = "from prefect import flow\n\n@flow\ndef my_flow(): pass"

        result = json.loads(asyncio.run(validate_conversion(dag_code, flow_code)))

        assert result["syntax_valid"] is True
        assert result["original_source"] == dag_code
        assert result["converted_source"] == flow_code

    def test_comparison_guidance_content(self, tmp_path):
        """Comparison guidance includes key checklist items."""
        dag = tmp_path / "dag.py"
        dag.write_text("x = 1\n")
        flow = tmp_path / "flow.py"
        flow.write_text("y = 2\n")

        result = json.loads(asyncio.run(validate_conversion(str(dag), str(flow))))

        guidance = result["comparison_guidance"]
        assert "tasks" in guidance.lower() or "task" in guidance.lower()
        assert "dependencies" in guidance.lower() or "dependency" in guidance.lower()
        assert "XCom" in guidance or "xcom" in guidance.lower()
        assert "connections" in guidance.lower() or "Connections" in guidance


class TestPhase4Validation:
    """VALD-01 + VALD-02: operator-specific guidance and production-style fixture DAGs."""

    @pytest.mark.parametrize(
        "fixture_name,expected_fragment",
        [
            ("kubernetes_pod_operator.py", "Kubernetes"),
            ("databricks_submit_run.py", "prefect-databricks"),
            ("azure_data_factory.py", "prefect-azure"),
            ("dbt_cloud_run_job.py", "prefect-dbt"),
            ("http_operator.py", "httpx"),
            ("ssh_operator.py", "Secret block"),
        ],
    )
    def test_operator_specific_guidance(self, fixture_name, expected_fragment):
        """validate_conversion returns operator-specific checklist items."""
        dag_source = (FIXTURES_DIR / fixture_name).read_text()
        flow_stub = "from prefect import flow\n\n@flow\ndef stub(): pass"
        result = json.loads(asyncio.run(validate_conversion(dag_source, flow_stub)))
        guidance = result["comparison_guidance"]
        assert expected_fragment in guidance, (
            f"Expected '{expected_fragment}' in guidance for {fixture_name};\n"
            f"Got: {guidance}"
        )

    def test_base_guidance_unchanged_for_plain_dag(self):
        """Plain DAG without new operators returns only base guidance."""
        dag_source = (
            "from airflow import DAG\n"
            "from airflow.operators.python import PythonOperator\n"
            "dag = DAG('simple')"
        )
        flow_stub = "from prefect import flow\n\n@flow\ndef stub(): pass"
        result = json.loads(asyncio.run(validate_conversion(dag_source, flow_stub)))
        guidance = result["comparison_guidance"]
        assert "Kubernetes" not in guidance
        assert "Databricks" not in guidance
        assert "Azure" not in guidance
        assert "dbt Cloud" not in guidance
        assert "httpx" not in guidance
        assert "Secret block" not in guidance
        # Base items still present
        assert "tasks" in guidance.lower()
        assert "dependencies" in guidance.lower()

    def test_multiple_operator_types_in_one_dag(self):
        """DAG with multiple new operator types gets all relevant guidance."""
        dag_source = (
            "from airflow import DAG\n"
            "from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator\n"
            "from airflow.providers.http.operators.http import SimpleHttpOperator\n"
        )
        flow_stub = "from prefect import flow\n\n@flow\ndef stub(): pass"
        result = json.loads(asyncio.run(validate_conversion(dag_source, flow_stub)))
        guidance = result["comparison_guidance"]
        assert "Kubernetes" in guidance
        assert "httpx" in guidance

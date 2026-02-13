"""Tests for scaffold tool."""

import asyncio
import json
import pytest
from pathlib import Path
import tempfile

from airflow_unfactor.tools.scaffold import (
    scaffold_project,
    _write_pyproject_toml,
    _write_readme,
    _write_conftest,
    _write_prefect_yaml,
    _write_dockerfile,
    _write_docker_compose,
    _write_github_workflow,
)


class TestScaffoldProject:
    """Tests for scaffold_project function."""

    def test_scaffold_empty_directory(self, tmp_path):
        """Test scaffolding with empty DAGs directory."""
        dags_dir = tmp_path / "dags"
        dags_dir.mkdir()
        output_dir = tmp_path / "output"

        result_json = asyncio.run(scaffold_project(
            dags_directory=str(dags_dir),
            output_directory=str(output_dir),
        ))
        result = json.loads(result_json)

        assert result["converted"] == 0
        assert result["failed"] == 0
        assert output_dir.exists()
        assert (output_dir / "flows").exists()
        assert (output_dir / "tests").exists()
        assert (output_dir / "pyproject.toml").exists()

    def test_scaffold_with_simple_dag(self, tmp_path):
        """Test scaffolding with a simple DAG."""
        dags_dir = tmp_path / "dags"
        dags_dir.mkdir()
        output_dir = tmp_path / "output"

        # Write a simple DAG
        dag_content = '''
from airflow import DAG
from airflow.operators.python import PythonOperator

def my_task():
    return "hello"

with DAG("simple_dag") as dag:
    t1 = PythonOperator(task_id="task1", python_callable=my_task)
'''
        (dags_dir / "simple_dag.py").write_text(dag_content)

        result_json = asyncio.run(scaffold_project(
            dags_directory=str(dags_dir),
            output_directory=str(output_dir),
            project_name="my_project",
        ))
        result = json.loads(result_json)

        assert result["converted"] == 1
        assert result["project_name"] == "my_project"
        assert (output_dir / "flows" / "simple_dag.py").exists()
        assert (output_dir / "tests" / "flows" / "test_simple_dag.py").exists()
        assert (output_dir / "migration" / "airflow_sources" / "simple_dag.py").exists()

    def test_scaffold_skips_init_files(self, tmp_path):
        """Test that __init__.py files are skipped."""
        dags_dir = tmp_path / "dags"
        dags_dir.mkdir()
        output_dir = tmp_path / "output"

        (dags_dir / "__init__.py").write_text("")
        (dags_dir / "__pycache__").mkdir()

        result_json = asyncio.run(scaffold_project(
            dags_directory=str(dags_dir),
            output_directory=str(output_dir),
        ))
        result = json.loads(result_json)

        assert result["converted"] == 0

    def test_scaffold_without_docker(self, tmp_path):
        """Test scaffolding without Docker files."""
        dags_dir = tmp_path / "dags"
        dags_dir.mkdir()
        output_dir = tmp_path / "output"

        asyncio.run(scaffold_project(
            dags_directory=str(dags_dir),
            output_directory=str(output_dir),
            include_docker=False,
        ))

        assert not (output_dir / "Dockerfile").exists()
        assert not (output_dir / "docker-compose.yml").exists()

    def test_scaffold_without_github_actions(self, tmp_path):
        """Test scaffolding without GitHub Actions."""
        dags_dir = tmp_path / "dags"
        dags_dir.mkdir()
        output_dir = tmp_path / "output"

        asyncio.run(scaffold_project(
            dags_directory=str(dags_dir),
            output_directory=str(output_dir),
            include_github_actions=False,
        ))

        assert not (output_dir / ".github").exists()


class TestWritePyprojectToml:
    """Tests for _write_pyproject_toml helper."""

    def test_generates_valid_toml(self, tmp_path):
        """Test that generated pyproject.toml is valid."""
        _write_pyproject_toml(tmp_path, "test_project")
        content = (tmp_path / "pyproject.toml").read_text()

        assert 'name = "test_project"' in content
        assert 'prefect>=3.0.0' in content
        assert 'requires-python = ">=3.11"' in content


class TestWriteReadme:
    """Tests for _write_readme helper."""

    def test_includes_project_name(self, tmp_path):
        """Test that README includes project name."""
        _write_readme(tmp_path, "my_flows", ["flow_a", "flow_b"])
        content = (tmp_path / "README.md").read_text()

        assert "# my_flows" in content
        assert "- `flow_a`" in content
        assert "- `flow_b`" in content

    def test_handles_empty_flows(self, tmp_path):
        """Test README with no flows."""
        _write_readme(tmp_path, "empty_project", [])
        content = (tmp_path / "README.md").read_text()

        assert "(none converted yet)" in content


class TestWriteConftest:
    """Tests for _write_conftest helper."""

    def test_includes_prefect_harness(self, tmp_path):
        """Test that conftest includes Prefect test harness."""
        _write_conftest(tmp_path)
        content = (tmp_path / "conftest.py").read_text()

        assert "prefect_test_harness" in content
        assert "@pytest.fixture" in content


class TestWritePrefectYaml:
    """Tests for _write_prefect_yaml helper."""

    def test_generates_deployment_config(self, tmp_path):
        """Test that prefect.yaml is generated."""
        _write_prefect_yaml(tmp_path, ["my_flow"])
        content = (tmp_path / "prefect.yaml").read_text()

        assert "deployments:" in content
        assert "my_flow" in content
        assert "work_pool:" in content

    def test_handles_empty_flows(self, tmp_path):
        """Test prefect.yaml with no flows."""
        _write_prefect_yaml(tmp_path, [])
        content = (tmp_path / "prefect.yaml").read_text()

        assert "deployments:" in content


class TestWriteDockerfile:
    """Tests for _write_dockerfile helper."""

    def test_generates_dockerfile(self, tmp_path):
        """Test that Dockerfile is generated."""
        _write_dockerfile(tmp_path)
        content = (tmp_path / "Dockerfile").read_text()

        assert "FROM python:3.11-slim" in content
        assert "prefect" in content


class TestWriteDockerCompose:
    """Tests for _write_docker_compose helper."""

    def test_generates_compose_file(self, tmp_path):
        """Test that docker-compose.yml is generated."""
        _write_docker_compose(tmp_path, "my_project")
        content = (tmp_path / "docker-compose.yml").read_text()

        assert "services:" in content
        assert "worker:" in content
        assert "server:" in content


class TestWriteGithubWorkflow:
    """Tests for _write_github_workflow helper."""

    def test_generates_workflow(self, tmp_path):
        """Test that GitHub workflow is generated."""
        _write_github_workflow(tmp_path)
        workflow_path = tmp_path / ".github" / "workflows" / "test.yml"

        assert workflow_path.exists()
        content = workflow_path.read_text()
        assert "pytest" in content
        assert "actions/checkout" in content

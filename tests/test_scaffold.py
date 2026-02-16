"""Tests for scaffold tool.

The scaffold tool creates project directory structure only - it does NOT
generate flow code. Code generation is left to the LLM using the analyze tool.
"""

import asyncio
import json

from airflow_unfactor.tools.scaffold import (
    _write_conftest,
    _write_docker_compose,
    _write_dockerfile,
    _write_github_workflow,
    _write_prefect_yaml,
    _write_pyproject_toml,
    _write_readme,
    scaffold_project,
)


class TestScaffoldProject:
    """Tests for scaffold_project function."""

    def test_scaffold_creates_directory_structure(self, tmp_path):
        """Test scaffolding creates basic directory structure."""
        output_dir = tmp_path / "output"

        result_json = asyncio.run(
            scaffold_project(
                output_directory=str(output_dir),
            )
        )
        result = json.loads(result_json)

        assert output_dir.exists()
        assert (output_dir / "deployments").exists()
        assert (output_dir / "tests").exists()
        assert (output_dir / "pyproject.toml").exists()
        assert (output_dir / "prefect.yaml").exists()
        assert "created_directories" in result
        assert "created_files" in result

    def test_scaffold_with_project_name(self, tmp_path):
        """Test scaffolding with custom project name."""
        output_dir = tmp_path / "output"

        result_json = asyncio.run(
            scaffold_project(
                output_directory=str(output_dir),
                project_name="my_custom_project",
            )
        )
        result = json.loads(result_json)

        assert result["project_name"] == "my_custom_project"

    def test_scaffold_without_docker(self, tmp_path):
        """Test scaffolding without Docker files."""
        output_dir = tmp_path / "output"

        asyncio.run(
            scaffold_project(
                output_directory=str(output_dir),
                include_docker=False,
            )
        )

        assert not (output_dir / "Dockerfile").exists()
        assert not (output_dir / "docker-compose.yml").exists()

    def test_scaffold_without_github_actions(self, tmp_path):
        """Test scaffolding without GitHub Actions."""
        output_dir = tmp_path / "output"

        asyncio.run(
            scaffold_project(
                output_directory=str(output_dir),
                include_github_actions=False,
            )
        )

        assert not (output_dir / ".github").exists()

    def test_scaffold_with_all_options(self, tmp_path):
        """Test scaffolding with all options enabled."""
        output_dir = tmp_path / "output"

        result_json = asyncio.run(
            scaffold_project(
                output_directory=str(output_dir),
                project_name="full_project",
                include_docker=True,
                include_github_actions=True,
            )
        )
        result = json.loads(result_json)

        assert (output_dir / "Dockerfile").exists()
        assert (output_dir / "docker-compose.yml").exists()
        assert (output_dir / ".github" / "workflows" / "test.yml").exists()
        assert result["structure"]["docker"] is True
        assert result["structure"]["ci"] is True

    def test_scaffold_includes_next_steps(self, tmp_path):
        """Test that scaffold result includes next steps guidance."""
        output_dir = tmp_path / "output"

        result_json = asyncio.run(
            scaffold_project(output_directory=str(output_dir))
        )
        result = json.loads(result_json)

        assert "next_steps" in result
        assert len(result["next_steps"]) > 0


class TestWritePyprojectToml:
    """Tests for _write_pyproject_toml helper."""

    def test_generates_valid_toml(self, tmp_path):
        """Test that generated pyproject.toml is valid."""
        _write_pyproject_toml(tmp_path, "test_project")
        content = (tmp_path / "pyproject.toml").read_text()

        assert 'name = "test_project"' in content
        assert "prefect>=3.0.0" in content
        assert 'requires-python = ">=3.11"' in content


class TestWriteReadme:
    """Tests for _write_readme helper."""

    def test_includes_project_name(self, tmp_path):
        """Test that README includes project name."""
        _write_readme(tmp_path, "my_flows")
        content = (tmp_path / "README.md").read_text()

        assert "# my_flows" in content
        assert "deployments/" in content

    def test_includes_migration_workflow(self, tmp_path):
        """Test README includes migration workflow."""
        _write_readme(tmp_path, "test_project")
        content = (tmp_path / "README.md").read_text()

        assert "airflow-unfactor" in content
        assert "prefect deploy" in content


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
        _write_prefect_yaml(tmp_path, "my_project")
        content = (tmp_path / "prefect.yaml").read_text()

        assert "name: my_project" in content
        assert "deployments:" in content
        assert "work_pools:" in content

    def test_includes_schedule_definitions(self, tmp_path):
        """Test prefect.yaml includes schedule definitions."""
        _write_prefect_yaml(tmp_path, "test_project")
        content = (tmp_path / "prefect.yaml").read_text()

        assert "schedules:" in content
        assert "cron:" in content


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
        _write_docker_compose(tmp_path)
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

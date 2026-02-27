"""Tests for scaffold tool.

The scaffold tool creates project directory structure only - it does NOT
generate flow code. Code generation is left to the LLM using the analyze tool.
"""

import asyncio
import json

from airflow_unfactor.tools.scaffold import (
    _schedule_yaml,
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

        result_json = asyncio.run(scaffold_project(output_directory=str(output_dir)))
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


class TestScheduleYaml:
    """Tests for _schedule_yaml helper function."""

    def test_none_returns_empty(self):
        """None schedule_interval returns empty string."""
        assert _schedule_yaml(None) == ""

    def test_empty_string_returns_empty(self):
        """Empty string returns empty string."""
        assert _schedule_yaml("") == ""

    def test_once_returns_empty(self):
        """@once schedule returns empty string."""
        assert _schedule_yaml("@once") == ""

    def test_cron_string(self):
        """Cron expression generates cron block."""
        result = _schedule_yaml("0 6 * * *")
        assert 'cron: "0 6 * * *"' in result
        assert "schedules:" in result

    def test_interval_seconds(self):
        """Digit-only string generates interval block."""
        result = _schedule_yaml("3600")
        assert "interval: 3600" in result
        assert "schedules:" in result

    def test_preset_daily(self):
        """@daily preset maps to cron 0 0 * * *."""
        result = _schedule_yaml("@daily")
        assert 'cron: "0 0 * * *"' in result

    def test_preset_hourly(self):
        """@hourly preset maps to cron 0 * * * *."""
        result = _schedule_yaml("@hourly")
        assert 'cron: "0 * * * *"' in result

    def test_preset_weekly(self):
        """@weekly preset maps to cron 0 0 * * 0."""
        result = _schedule_yaml("@weekly")
        assert 'cron: "0 0 * * 0"' in result

    def test_preset_monthly(self):
        """@monthly preset maps to cron 0 0 1 * *."""
        result = _schedule_yaml("@monthly")
        assert 'cron: "0 0 1 * *"' in result


class TestScheduleTranslation:
    """Tests for schedule_interval parameter in scaffold_project."""

    def test_scaffold_with_cron_schedule(self, tmp_path):
        """scaffold_project with cron schedule generates cron in prefect.yaml."""
        output_dir = tmp_path / "output"
        asyncio.run(
            scaffold_project(
                output_directory=str(output_dir),
                project_name="my_flow",
                schedule_interval="0 6 * * *",
            )
        )
        content = (output_dir / "prefect.yaml").read_text()
        assert 'cron: "0 6 * * *"' in content
        # Should be under deployments section (real entry, not commented)
        lines = content.splitlines()
        cron_line = next((i for i, l in enumerate(lines) if 'cron: "0 6 * * *"' in l), None)
        assert cron_line is not None, "cron line not found"
        # Verify it's not commented out
        assert not lines[cron_line].lstrip().startswith("#")

    def test_scaffold_with_interval_schedule(self, tmp_path):
        """scaffold_project with seconds string generates interval in prefect.yaml."""
        output_dir = tmp_path / "output"
        asyncio.run(
            scaffold_project(
                output_directory=str(output_dir),
                project_name="my_flow",
                schedule_interval="3600",
            )
        )
        content = (output_dir / "prefect.yaml").read_text()
        assert "interval: 3600" in content

    def test_scaffold_with_no_schedule(self, tmp_path):
        """scaffold_project with no schedule omits schedules from real deployment."""
        output_dir = tmp_path / "output"
        asyncio.run(
            scaffold_project(
                output_directory=str(output_dir),
                project_name="my_flow",
                schedule_interval=None,
            )
        )
        content = (output_dir / "prefect.yaml").read_text()
        # deployments section should exist but have no real (uncommented) deployment
        assert "deployments:" in content
        # The real deployments list should be empty ([]); cron may appear in commented examples
        assert "  []" in content

    def test_scaffold_with_once_schedule(self, tmp_path):
        """scaffold_project with @once omits schedules section."""
        output_dir = tmp_path / "output"
        asyncio.run(
            scaffold_project(
                output_directory=str(output_dir),
                project_name="my_flow",
                schedule_interval="@once",
            )
        )
        content = (output_dir / "prefect.yaml").read_text()
        # Should behave like None — no real deployment with schedules
        assert "  []" in content

    def test_scaffold_with_preset_daily(self, tmp_path):
        """scaffold_project with @daily generates cron 0 0 * * * in prefect.yaml."""
        output_dir = tmp_path / "output"
        asyncio.run(
            scaffold_project(
                output_directory=str(output_dir),
                project_name="my_flow",
                schedule_interval="@daily",
            )
        )
        content = (output_dir / "prefect.yaml").read_text()
        assert 'cron: "0 0 * * *"' in content

    def test_scaffold_report_includes_schedule(self, tmp_path):
        """scaffold_project result JSON includes schedule field."""
        output_dir = tmp_path / "output"
        result_json = asyncio.run(
            scaffold_project(
                output_directory=str(output_dir),
                schedule_interval="0 6 * * *",
            )
        )
        result = json.loads(result_json)
        assert result["schedule"] == "0 6 * * *"

    def test_scaffold_report_schedule_none(self, tmp_path):
        """scaffold_project result JSON has schedule: null when not provided."""
        output_dir = tmp_path / "output"
        result_json = asyncio.run(
            scaffold_project(output_directory=str(output_dir))
        )
        result = json.loads(result_json)
        assert result["schedule"] is None

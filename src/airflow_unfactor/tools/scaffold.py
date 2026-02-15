"""Generate project skeleton for migrated Prefect flows."""

import json
from pathlib import Path

from airflow_unfactor.tools.convert import convert_dag


async def scaffold_project(
    dags_directory: str | None,
    output_directory: str,
    project_name: str | None = None,
    include_docker: bool = True,
    include_github_actions: bool = True,
) -> str:
    """Generate a clean project skeleton for Prefect flows.

    Creates a well-organized project structure following Prefect best practices,
    inspired by prefecthq/flows architecture.

    If dags_directory is provided, will also convert those DAGs (deprecated).
    For new architecture, pass dags_directory=None to just create structure.

    Args:
        dags_directory: Directory containing Airflow DAG files to migrate (or None for pure scaffolding)
        output_directory: Where to create the new project
        project_name: Project name (defaults to directory name)
        include_docker: Include Dockerfile and docker-compose.yml
        include_github_actions: Include CI workflow

    Returns:
        JSON with scaffold report
    """
    output_dir = Path(output_directory)
    input_dir = Path(dags_directory) if dags_directory else None
    project_name = project_name or (input_dir.name if input_dir else output_dir.name).replace("-", "_").replace(" ", "_")

    # Create project structure
    dirs = {
        "flows": output_dir / "flows",
        "tasks": output_dir / "tasks",
        "deployments": output_dir / "deployments",
        "infrastructure": output_dir / "infrastructure",
        "tests": output_dir / "tests",
        "tests_flows": output_dir / "tests" / "flows",
        "tests_tasks": output_dir / "tests" / "tasks",
        "migration": output_dir / "migration",
        "migration_sources": output_dir / "migration" / "airflow_sources",
        "migration_notes": output_dir / "migration" / "conversion_notes",
    }

    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)

    # Convert DAGs (if directory provided - this is deprecated behavior)
    converted = 0
    failed = 0
    errors = []
    flow_names = []

    if input_dir is None:
        # Pure scaffolding mode - no DAG conversion
        pass
    elif not input_dir.exists():
        errors.append({"file": str(input_dir), "error": "Directory does not exist"})
    else:
        for dag_file in input_dir.glob("*.py"):
            if dag_file.name.startswith("__"):
                continue

            try:
                result_json = await convert_dag(
                    path=str(dag_file),
                    include_comments=True,
                    generate_tests=True,
                )
                result = json.loads(result_json)

                if "error" in result:
                    failed += 1
                    errors.append({"file": dag_file.name, "error": result["error"]})
                    continue

                # Determine flow name from mapping or filename
                flow_name = _extract_flow_name(result, dag_file)
                flow_names.append(flow_name)

                # Write flow code
                flow_file = dirs["flows"] / f"{flow_name}.py"
                flow_file.write_text(result.get("flow_code", ""))

                # Write test code
                if result.get("test_code"):
                    test_file = dirs["tests_flows"] / f"test_{flow_name}.py"
                    test_file.write_text(result["test_code"])

                # Write runbook
                if result.get("conversion_runbook_md"):
                    runbook_file = dirs["migration_notes"] / f"{flow_name}_runbook.md"
                    runbook_file.write_text(result["conversion_runbook_md"])

                # Copy original for reference
                source_copy = dirs["migration_sources"] / dag_file.name
                source_copy.write_text(dag_file.read_text())

                converted += 1

            except Exception as e:
                failed += 1
                errors.append({"file": dag_file.name, "error": str(e)})

    # Generate project files
    _write_pyproject_toml(output_dir, project_name)
    _write_readme(output_dir, project_name, flow_names)
    _write_conftest(dirs["tests"])
    _write_init_files(dirs)
    _write_prefect_yaml(output_dir, flow_names)

    if include_docker:
        _write_dockerfile(output_dir)
        _write_docker_compose(output_dir, project_name)

    if include_github_actions:
        _write_github_workflow(output_dir)

    report = {
        "project_name": project_name,
        "output_directory": str(output_dir),
        "converted": converted,
        "failed": failed,
        "errors": errors if errors else None,
        "structure": {
            "flows": f"{converted} flow files",
            "tests": f"{converted} test files",
            "runbooks": f"{converted} migration runbooks",
            "docker": include_docker,
            "ci": include_github_actions,
        },
    }

    # Write report
    report_path = output_dir / "scaffold_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    report["report_path"] = str(report_path)

    return json.dumps(report, indent=2)


def _extract_flow_name(result: dict, dag_file: Path) -> str:
    """Extract flow name from conversion result or filename."""
    mapping = result.get("original_to_new_mapping", {})
    if mapping:
        # Use first task name pattern to guess flow name
        pass
    # Default to filename
    return dag_file.stem.replace("-", "_")


def _write_pyproject_toml(output_dir: Path, project_name: str) -> None:
    """Write pyproject.toml."""
    content = f'''[project]
name = "{project_name}"
version = "0.1.0"
description = "Prefect flows migrated from Airflow"
requires-python = ">=3.11"
dependencies = [
    "prefect>=3.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
'''
    (output_dir / "pyproject.toml").write_text(content)


def _write_readme(output_dir: Path, project_name: str, flow_names: list[str]) -> None:
    """Write README.md."""
    flows_list = (
        "\n".join([f"- `{name}`" for name in flow_names])
        if flow_names
        else "- (none converted yet)"
    )
    content = f"""# {project_name}

Prefect flows migrated from Apache Airflow.

## Flows

{flows_list}

## Setup

```bash
# Install dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Deploy flows
prefect deploy --all
```

## Project Structure

```
{project_name}/
├── flows/           # Prefect flow entrypoints
├── tasks/           # Reusable task functions
├── deployments/     # Deployment configurations
├── infrastructure/  # Work pool and worker configs
├── tests/           # pytest tests
└── migration/       # Original DAGs and runbooks
    ├── airflow_sources/    # Original DAG files (read-only reference)
    └── conversion_notes/   # Migration runbooks and TODOs
```

## Migration Notes

See `migration/conversion_notes/` for DAG-specific migration runbooks.

---

Generated by [airflow-unfactor](https://github.com/prefect/airflow-unfactor)
"""
    (output_dir / "README.md").write_text(content)


def _write_conftest(tests_dir: Path) -> None:
    """Write pytest conftest.py."""
    content = '''"""Pytest configuration for Prefect flow tests."""

import pytest
from prefect.testing.utilities import prefect_test_harness


@pytest.fixture(scope="module")
def prefect_harness():
    """Provide Prefect test harness for flow tests."""
    with prefect_test_harness():
        yield
'''
    (tests_dir / "conftest.py").write_text(content)


def _write_init_files(dirs: dict[str, Path]) -> None:
    """Write __init__.py files."""
    for key in ["flows", "tasks", "tests", "tests_flows", "tests_tasks"]:
        init_file = dirs[key] / "__init__.py"
        init_file.write_text("")


def _write_prefect_yaml(output_dir: Path, flow_names: list[str]) -> None:
    """Write prefect.yaml deployment configuration."""
    deployments = []
    for name in flow_names:
        deployments.append(f"""  - name: {name}
    entrypoint: flows/{name}.py:{name}
    work_pool:
      name: default""")

    deployments_yaml = "\n".join(deployments) if deployments else "  []"
    content = f"""# Prefect deployment configuration
# See: https://docs.prefect.io/concepts/deployments/

name: {output_dir.name}

deployments:
{deployments_yaml}
"""
    (output_dir / "prefect.yaml").write_text(content)


def _write_dockerfile(output_dir: Path) -> None:
    """Write Dockerfile."""
    content = """FROM python:3.11-slim

WORKDIR /app

# Install uv for fast dependency management
RUN pip install uv

# Copy project files
COPY pyproject.toml .
COPY flows/ flows/
COPY tasks/ tasks/

# Install dependencies
RUN uv pip install --system -e .

# Default command
CMD ["prefect", "worker", "start", "--pool", "default"]
"""
    (output_dir / "Dockerfile").write_text(content)


def _write_docker_compose(output_dir: Path, project_name: str) -> None:
    """Write docker-compose.yml."""
    content = """services:
  worker:
    build: .
    environment:
      - PREFECT_API_URL=${PREFECT_API_URL:-http://localhost:4200/api}
    depends_on:
      - server

  server:
    image: prefecthq/prefect:3-python3.11
    command: prefect server start --host 0.0.0.0
    ports:
      - "4200:4200"
    volumes:
      - prefect-data:/root/.prefect

volumes:
  prefect-data:
"""
    (output_dir / "docker-compose.yml").write_text(content)


def _write_github_workflow(output_dir: Path) -> None:
    """Write GitHub Actions workflow."""
    workflow_dir = output_dir / ".github" / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)

    content = """name: Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Set up Python
        run: uv python install 3.11

      - name: Install dependencies
        run: uv pip install -e ".[dev]"

      - name: Run tests
        run: pytest
"""
    (workflow_dir / "test.yml").write_text(content)

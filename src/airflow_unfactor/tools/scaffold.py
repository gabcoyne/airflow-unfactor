"""Generate project skeleton for Prefect flows."""

import json
from pathlib import Path

# Airflow preset schedule names → cron equivalents
_PRESET_CRON: dict[str, str] = {
    "@daily": "0 0 * * *",
    "@hourly": "0 * * * *",
    "@weekly": "0 0 * * 0",
    "@monthly": "0 0 1 * *",
    "@yearly": "0 0 1 1 *",
    "@annually": "0 0 1 1 *",
}


def _schedule_yaml(schedule_interval: str | None) -> str:
    """Generate the schedules YAML block for a deployment entry.

    Per project conventions: when schedule_interval is None or @once,
    omit the schedules section entirely — no comments, no placeholders.

    Args:
        schedule_interval: A cron string, preset alias (@daily, etc.),
            seconds as a digit string, or None.

    Returns:
        YAML string for the schedules block (with leading indentation),
        or empty string if no schedule should be emitted.
    """
    if not schedule_interval or schedule_interval.strip() == "@once":
        return ""

    interval = schedule_interval.strip()

    # Preset alias conversion
    if interval in _PRESET_CRON:
        cron = _PRESET_CRON[interval]
        return f'    schedules:\n      - cron: "{cron}"\n'

    # Interval in seconds (pure digits)
    if interval.isdigit():
        return f"    schedules:\n      - interval: {interval}\n"

    # Cron expression (contains spaces or starts with @)
    return f'    schedules:\n      - cron: "{interval}"\n'


async def scaffold_project(
    output_directory: str,
    project_name: str | None = None,
    include_docker: bool = True,
    include_github_actions: bool = True,
    schedule_interval: str | None = None,
) -> str:
    """Generate a clean project skeleton for Prefect flows.

    Creates a well-organized project structure following Prefect best practices,
    inspired by prefecthq/flows architecture.

    This tool creates the directory structure only - the LLM generates the flow code.

    Args:
        output_directory: Where to create the new project
        project_name: Project name (defaults to directory name)
        include_docker: Include Dockerfile and docker-compose.yml
        include_github_actions: Include CI workflow
        schedule_interval: Cron string, preset alias (@daily, etc.),
            seconds as digits, or None. Generates real schedule config in
            prefect.yaml when provided; omits schedules section when None.

    Returns:
        JSON with scaffold report including created directories and next steps
    """
    output_dir = Path(output_directory)
    project_name = project_name or output_dir.name.replace("-", "_").replace(" ", "_")

    # Create project structure following prefecthq/flows conventions
    dirs = {
        "deployments": output_dir / "deployments",
        "deployments_default": output_dir / "deployments" / "default",
        "tests": output_dir / "tests",
    }

    created_directories = []
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)
        created_directories.append(str(dir_path.relative_to(output_dir)))

    # Generate project files
    created_files = []

    _write_pyproject_toml(output_dir, project_name)
    created_files.append("pyproject.toml")

    _write_readme(output_dir, project_name)
    created_files.append("README.md")

    _write_conftest(dirs["tests"])
    created_files.append("tests/conftest.py")

    _write_prefect_yaml(output_dir, project_name, schedule_interval)
    created_files.append("prefect.yaml")

    if include_docker:
        _write_dockerfile(output_dir)
        _write_docker_compose(output_dir)
        created_files.extend(["Dockerfile", "docker-compose.yml"])

    if include_github_actions:
        _write_github_workflow(output_dir)
        created_files.append(".github/workflows/test.yml")

    report = {
        "project_name": project_name,
        "output_directory": str(output_dir),
        "created_directories": created_directories,
        "created_files": created_files,
        "structure": {
            "docker": include_docker,
            "ci": include_github_actions,
        },
        "schedule": schedule_interval,
        "next_steps": [
            "1. Use analyze() to analyze your Airflow DAGs",
            "2. Use get_context() to fetch relevant Prefect patterns",
            "3. Generate Prefect flow code and place in deployments/<workspace>/<flow>/flow.py",
            "4. Update prefect.yaml with your deployment configuration",
            "5. Run tests with: pytest",
            "6. Deploy with: prefect deploy --all",
        ],
    }

    return json.dumps(report, indent=2)


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


def _write_readme(output_dir: Path, project_name: str) -> None:
    """Write README.md."""
    content = f"""# {project_name}

Prefect flows migrated from Apache Airflow.

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
├── deployments/         # Flow implementations
│   └── <workspace>/     # Workspace grouping
│       └── <flow>/      # Individual flow
│           ├── flow.py
│           ├── Dockerfile (optional)
│           └── requirements.txt (optional)
├── tests/               # pytest tests
├── prefect.yaml         # Deployment configuration
└── pyproject.toml       # Python project config
```

## Workflow

1. Read your Airflow DAG with `read_dag`
2. Use `lookup_concept` for translation guidance, then generate Prefect flow code
3. Place flows in `deployments/<workspace>/<flow>/flow.py`
4. Update `prefect.yaml` with deployment configuration
5. Deploy with `prefect deploy --all`

---

Generated by [airflow-unfactor](https://github.com/gabcoyne/airflow-unfactor)
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


def _write_prefect_yaml(
    output_dir: Path,
    project_name: str,
    schedule_interval: str | None = None,
) -> None:
    """Write prefect.yaml deployment configuration template.

    When schedule_interval is provided, generates a real deployment entry
    with schedule config. When None, keeps a commented-out example.
    """
    schedule_block = _schedule_yaml(schedule_interval)

    if schedule_block:
        # Real deployment entry with schedule
        deployments_section = (
            f"deployments:\n"
            f"  - name: {project_name}\n"
            f"    entrypoint: deployments/default/{project_name}/flow.py:{project_name}\n"
            f"{schedule_block}"
            f"    work_pool: *default_pool\n"
        )
    else:
        # Commented-out example (no schedule)
        deployments_section = (
            "deployments:\n"
            "  # Example deployment:\n"
            "  # - name: My Flow\n"
            "  #   description: Converted from Airflow DAG 'my_dag'\n"
            "  #   entrypoint: deployments/default/my-flow/flow.py:my_flow\n"
            "  #   schedules:\n"
            "  #     - *hourly\n"
            "  #   work_pool: *default_pool\n"
            "  []\n"
        )

    content = f"""# Prefect deployment configuration
# See: https://docs.prefect.io/concepts/deployments/

name: {project_name}
prefect-version: 3.0.0

# Pull step - configure your repository
# pull:
#   - prefect.deployments.steps.git_clone:
#       repository: https://github.com/org/{project_name}
#       branch: main

# Reusable definitions
definitions:
  work_pools:
    default: &default_pool
      name: default
      job_variables:
        image: "{{{{ image }}}}"

  schedules:
    hourly: &hourly
      cron: "0 * * * *"
    daily: &daily
      cron: "0 0 * * *"

# Deployments - add your flows here
{deployments_section}"""
    (output_dir / "prefect.yaml").write_text(content)


def _write_dockerfile(output_dir: Path) -> None:
    """Write Dockerfile."""
    content = """FROM python:3.11-slim

WORKDIR /app

# Install uv for fast dependency management
RUN pip install uv

# Copy project files
COPY pyproject.toml .
COPY deployments/ deployments/

# Install dependencies
RUN uv pip install --system -e .

# Default command
CMD ["prefect", "worker", "start", "--pool", "default"]
"""
    (output_dir / "Dockerfile").write_text(content)


def _write_docker_compose(output_dir: Path) -> None:
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

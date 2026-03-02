"""Generate prefect.yaml deployment configuration from DAG metadata."""

import json
from pathlib import Path
from typing import Any


def _slugify(name: str) -> str:
    """Convert snake_case or any name to kebab-case slug."""
    return name.replace("_", "-").lower()


def _flow_to_deployment_yaml(
    flow_name: str,
    entrypoint: str,
    schedule: str | None = None,
    parameters: dict[str, Any] | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    dataset_triggers: list[str] | None = None,
) -> str:
    """Build the YAML block for a single deployment entry."""
    slug = _slugify(flow_name)
    lines = [f"  - name: {slug}"]

    if description:
        lines.append(f"    description: {description}")

    lines.append(f"    entrypoint: {entrypoint}")

    if tags:
        lines.append(f"    tags: [{', '.join(tags)}]")

    if parameters:
        lines.append("    parameters:")
        for k, v in parameters.items():
            if isinstance(v, str):
                lines.append(f'      {k}: "{v}"')
            else:
                lines.append(f"      {k}: {v}")

    if schedule:
        schedule = schedule.strip()
        _PRESET_CRON = {
            "@daily": "0 0 * * *",
            "@hourly": "0 * * * *",
            "@weekly": "0 0 * * 0",
            "@monthly": "0 0 1 * *",
            "@yearly": "0 0 1 1 *",
        }
        if schedule in _PRESET_CRON:
            cron = _PRESET_CRON[schedule]
            lines.append(f'    schedules:\n      - cron: "{cron}"')
        elif schedule.isdigit():
            lines.append(f"    schedules:\n      - interval: {schedule}")
        else:
            lines.append(f'    schedules:\n      - cron: "{schedule}"')

    if dataset_triggers:
        lines.append("    # Dataset triggers require Prefect Automations (not representable in prefect.yaml).")
        lines.append("    # Create an Automation for each dataset trigger below:")
        for ds in dataset_triggers:
            lines.append(f"    #   - trigger: event on dataset '{ds}' → run this deployment")
        lines.append("    # See: https://docs.prefect.io/concepts/automations")

    lines.append("    work_pool: *default_pool")
    return "\n".join(lines)


def _build_prefect_yaml(
    project_name: str,
    flows: list[dict[str, Any]],
) -> str:
    """Build the full prefect.yaml document."""
    deployments = "\n".join(
        _flow_to_deployment_yaml(**{k: v for k, v in f.items()})
        for f in flows
    )

    return f"""# Prefect deployment configuration
# See: https://docs.prefect.io/concepts/deployments/

name: {project_name}
prefect-version: 3.0.0

# Configure your repository pull step:
# pull:
#   - prefect.deployments.steps.git_clone:
#       repository: https://github.com/org/{project_name}
#       branch: main

definitions:
  work_pools:
    default: &default_pool
      name: default  # TODO: set your work pool name (uv run prefect work-pool create <name>)
      job_variables:
        image: "{{{{ image }}}}"

  schedules:
    hourly: &hourly
      cron: "0 * * * *"
    daily: &daily
      cron: "0 0 * * *"

deployments:
{deployments}
"""


async def generate_deployment(
    output_directory: str,
    flows: list[dict[str, Any]],
    workspace: str = "default",
) -> str:
    """Write prefect.yaml deployment configuration from DAG metadata.

    Args:
        output_directory: Directory to write prefect.yaml into.
        flows: List of flow dicts. Each requires flow_name and entrypoint;
            all other fields (schedule, parameters, description, tags,
            dataset_triggers) are optional.
        workspace: Workspace name (default: "default").

    Returns:
        JSON with created_file, deployment_names, next_steps.
    """
    output_dir = Path(output_directory)
    output_dir.mkdir(parents=True, exist_ok=True)

    project_name = _slugify(output_dir.name)
    content = _build_prefect_yaml(project_name=project_name, flows=flows)

    prefect_yaml = output_dir / "prefect.yaml"
    prefect_yaml.write_text(content)

    deployment_names = [_slugify(f["flow_name"]) for f in flows]

    has_dataset_triggers = any(f.get("dataset_triggers") for f in flows)

    next_steps = [
        "Set up a work pool: uv run prefect work-pool create <name> --type process",
        "Update the work_pool name in prefect.yaml",
        "Configure the pull step in prefect.yaml with your git repository",
        "Deploy: uv run prefect deploy --all",
    ]
    if has_dataset_triggers:
        next_steps.append(
            "Create Automations for dataset triggers: https://docs.prefect.io/concepts/automations"
        )

    return json.dumps(
        {
            "created_file": str(prefect_yaml),
            "deployment_names": deployment_names,
            "next_steps": next_steps,
        },
        indent=2,
    )

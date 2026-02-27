"""Knowledge loader for Airflow→Prefect translation mappings.

Loads Colin-compiled JSON output when available, falls back to
minimal built-in mappings otherwise.
"""

import difflib
import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Minimal fallback mappings when Colin output is unavailable.
FALLBACK_KNOWLEDGE: dict[str, dict[str, Any]] = {
    "PythonOperator": {
        "concept_type": "operator",
        "airflow": {"name": "PythonOperator", "module": "airflow.operators.python"},
        "prefect_equivalent": {
            "pattern": "@task decorator",
            "package": "prefect",
            "import": "from prefect import task",
            "example": "@task\ndef my_task():\n    ...",
        },
        "translation_rules": [
            "Replace PythonOperator with @task decorator",
            "The python_callable becomes the decorated function body",
            "op_args/op_kwargs become function parameters",
        ],
    },
    "BashOperator": {
        "concept_type": "operator",
        "airflow": {"name": "BashOperator", "module": "airflow.operators.bash"},
        "prefect_equivalent": {
            "pattern": "prefect_shell.ShellOperation or subprocess",
            "package": "prefect-shell",
            "import": "from prefect_shell import ShellOperation",
            "example": "ShellOperation(commands=['echo hello']).run()",
        },
        "translation_rules": [
            "Replace BashOperator with ShellOperation.run() or subprocess",
            "bash_command becomes the commands list",
        ],
    },
    "XCom": {
        "concept_type": "concept",
        "airflow": {"description": "Cross-communication between tasks via push/pull"},
        "prefect_equivalent": {
            "pattern": "Task return values",
            "description": "Tasks return values directly; downstream tasks receive them as parameters",
        },
        "translation_rules": [
            "Replace xcom_push with task return values",
            "Replace xcom_pull with passing return values to downstream tasks",
            "Remove ti.xcom_push/ti.xcom_pull calls",
        ],
        "gotchas": [
            "Prefect tasks must return serializable values",
            "Large data should use result serializers or artifacts",
        ],
    },
    "TaskGroup": {
        "concept_type": "pattern",
        "airflow": {"description": "Group tasks visually and logically in the DAG UI"},
        "prefect_equivalent": {
            "pattern": "Subflow",
            "description": "Use a nested @flow for logical grouping",
            "example": "@flow\ndef my_subflow():\n    task_a()\n    task_b()",
        },
        "translation_rules": [
            "Convert TaskGroup to a @flow-decorated function",
            "Tasks inside the group become tasks called from the subflow",
        ],
    },
    "DAG": {
        "concept_type": "concept",
        "airflow": {"description": "Directed Acyclic Graph — the top-level workflow container"},
        "prefect_equivalent": {
            "pattern": "@flow decorator",
            "package": "prefect",
            "import": "from prefect import flow",
            "example": "@flow\ndef my_flow():\n    ...",
        },
        "translation_rules": [
            "Replace DAG context manager with @flow decorator",
            "DAG parameters become flow parameters",
            "schedule_interval becomes a Prefect deployment schedule",
        ],
    },
    "postgres_default": {
        "concept_type": "connection",
        "airflow": {"description": "PostgreSQL connection via Airflow connection URI"},
        "prefect_equivalent": {
            "block_type": "SqlAlchemyConnector",
            "package": "prefect-sqlalchemy",
            "import": "from prefect_sqlalchemy import SqlAlchemyConnector",
            "example": 'connector = SqlAlchemyConnector.load("postgres-default")',
        },
        "translation_rules": [
            "Create a SqlAlchemyConnector block in Prefect",
            "Migrate connection URI from Airflow connection to block configuration",
        ],
    },
    "ShortCircuitOperator": {
        "concept_type": "operator",
        "airflow": {"name": "ShortCircuitOperator", "module": "airflow.operators.python"},
        "prefect_equivalent": {
            "pattern": "@task with conditional return + flow control",
            "description": "Replace with @task returning bool; use if/else in @flow to skip downstream",
        },
        "translation_rules": [
            "Replace ShortCircuitOperator with a @task that returns a boolean",
            "In the @flow, use if/else to conditionally call downstream tasks based on the return value",
            "Python control flow handles short-circuit behavior natively",
        ],
    },
    "BranchPythonOperator": {
        "concept_type": "operator",
        "airflow": {"name": "BranchPythonOperator", "module": "airflow.operators.python"},
        "prefect_equivalent": {
            "pattern": "Python if/else in @flow",
            "description": "Replace with if/else block in the @flow; python_callable return becomes branch condition",
        },
        "translation_rules": [
            "Replace BranchPythonOperator with if/else logic in the @flow",
            "The python_callable return value (branch task_id) becomes the if/else condition",
            "Python control flow handles branching natively — no special operator needed",
        ],
    },
    "EmptyOperator": {
        "concept_type": "operator",
        "airflow": {"name": "EmptyOperator", "module": "airflow.operators.empty"},
        "prefect_equivalent": {
            "pattern": "Remove or use pass",
            "description": "EmptyOperator is a pure placeholder — remove it or restructure task calls directly",
        },
        "translation_rules": [
            "Remove EmptyOperator nodes — they are pure placeholders with no logic",
            "If used for wiring (upstream/downstream), restructure task calls directly in @flow",
        ],
    },
    "DummyOperator": {
        "concept_type": "operator",
        "airflow": {"name": "DummyOperator", "module": "airflow.operators.dummy"},
        "prefect_equivalent": {
            "pattern": "Remove or use pass",
            "description": "DummyOperator (Airflow <2.4 name for EmptyOperator) — remove it",
        },
        "translation_rules": [
            "DummyOperator is the Airflow <2.4 name for EmptyOperator — treat identically",
            "Remove nodes; restructure task calls directly if used for wiring",
        ],
    },
    "EmailOperator": {
        "concept_type": "operator",
        "airflow": {"name": "EmailOperator", "module": "airflow.operators.email"},
        "prefect_equivalent": {
            "pattern": "prefect-email or smtplib @task",
            "package": "prefect-email",
            "description": "Use prefect-email EmailServerCredentials block, or wrap smtplib in @task",
        },
        "translation_rules": [
            "Use prefect-email package: EmailServerCredentials block + send_email_message @task",
            "Alternatively, wrap smtplib.sendmail in a @task for full control",
        ],
    },
    "TriggerDagRunOperator": {
        "concept_type": "operator",
        "airflow": {"name": "TriggerDagRunOperator", "module": "airflow.operators.trigger_dagrun"},
        "prefect_equivalent": {
            "pattern": "run_deployment() from prefect.deployments",
            "import": "from prefect.deployments import run_deployment",
            "description": "Replace with run_deployment() call; DAG ID becomes deployment name",
        },
        "translation_rules": [
            "Replace TriggerDagRunOperator with run_deployment() from prefect.deployments",
            "trigger_dag_id becomes the deployment name",
            "conf becomes the parameters dict passed to run_deployment()",
        ],
    },
    "ExternalTaskSensor": {
        "concept_type": "operator",
        "airflow": {"name": "ExternalTaskSensor", "module": "airflow.sensors.external_task"},
        "prefect_equivalent": {
            "pattern": "Automation trigger or flow parameter",
            "description": "Use Prefect Automations to trigger on upstream flow completion, or pass results explicitly",
        },
        "translation_rules": [
            "Use Prefect Automations to trigger this flow when an upstream deployment completes",
            "Alternatively, restructure to pass upstream results explicitly as flow parameters",
        ],
    },
    "FileSensor": {
        "concept_type": "operator",
        "airflow": {"name": "FileSensor", "module": "airflow.sensors.filesystem"},
        "prefect_equivalent": {
            "pattern": "@task polling loop or watchdog",
            "description": "Wrap Path.exists() check in @task with retry/delay, or use filesystem event trigger",
        },
        "translation_rules": [
            "Wrap a Path.exists() check in a @task with Prefect retries (max_retries + retry_delay_seconds)",
            "Alternatively, use a filesystem event trigger via Prefect Automations",
        ],
    },
    "PythonSensor": {
        "concept_type": "operator",
        "airflow": {"name": "PythonSensor", "module": "airflow.sensors.python"},
        "prefect_equivalent": {
            "pattern": "@task with retry",
            "description": "The poke callable becomes a @task; use Prefect retries for polling behavior",
        },
        "translation_rules": [
            "Convert the poke callable to a @task",
            "Use Prefect retries (max_retries + retry_delay_seconds) to replicate polling behavior",
        ],
    },
}


def normalize_query(query: str) -> str:
    """Normalize Jinja-style queries for lookup.

    Strips {{ }}, macros., and var.value. prefixes so that
    lookup_concept("{{ macros.ds_add(ds, 5) }}") finds the ds_add entry.

    Args:
        query: The raw query string, possibly wrapped in Jinja syntax.

    Returns:
        Normalized query string suitable for knowledge lookup.
    """
    q = query.strip()
    # Strip {{ }} wrapper
    match = re.match(r"^\{\{\s*(.+?)\s*\}\}$", q)
    if match:
        q = match.group(1)
    # Strip macros. prefix
    if q.startswith("macros."):
        q = q[len("macros."):]
    # Strip var.value. prefix
    if q.startswith("var.value."):
        q = q[len("var.value."):]
    return q


def load_knowledge(colin_output_dir: str = "colin/output") -> dict[str, Any]:
    """Load compiled knowledge from Colin output directory.

    Reads all JSON files from the Colin output directory and merges
    them into a single lookup dictionary keyed by concept name.

    Args:
        colin_output_dir: Path to Colin's compiled output.

    Returns:
        Dict mapping concept names to their translation knowledge.
    """
    output_path = Path(colin_output_dir)
    if not output_path.exists():
        return {}

    knowledge: dict[str, Any] = {}
    for json_file in output_path.glob("*.json"):
        try:
            data = json.loads(json_file.read_text())
            if isinstance(data, dict):
                # If the JSON has a top-level "entries" list, index by name
                if "entries" in data and isinstance(data["entries"], list):
                    for entry in data["entries"]:
                        if "name" in entry:
                            knowledge[entry["name"]] = entry
                # If it's a flat dict of concepts, merge directly
                else:
                    for key, value in data.items():
                        if isinstance(value, dict):
                            knowledge[key] = value
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(
                "Failed to parse %s: %s: %s",
                json_file.name, type(e).__name__, e
            )
            continue

    return knowledge


def lookup(concept: str, knowledge: dict[str, Any]) -> dict[str, Any]:
    """Look up a concept in the knowledge base.

    Tries exact match first, then case-insensitive, then substring.
    Normalizes Jinja syntax before lookup so that queries like
    "{{ macros.ds_add(ds, 5) }}" resolve to the ds_add entry.

    Args:
        concept: The concept to look up (operator name, pattern, etc.)
        knowledge: The loaded knowledge dict.

    Returns:
        The matching entry, or a not_found result with suggestions.
    """
    concept = normalize_query(concept)

    # Exact match
    if concept in knowledge:
        return {"status": "found", "source": "colin", **knowledge[concept]}

    # Case-insensitive match
    lower = concept.lower()
    for key, value in knowledge.items():
        if key.lower() == lower:
            return {"status": "found", "source": "colin", **value}

    # Substring match
    for key, value in knowledge.items():
        if lower in key.lower() or key.lower() in lower:
            return {"status": "found", "source": "colin", **value}

    # Try fallback
    if concept in FALLBACK_KNOWLEDGE:
        return {"status": "found", "source": "fallback", **FALLBACK_KNOWLEDGE[concept]}

    for key, value in FALLBACK_KNOWLEDGE.items():
        if key.lower() == lower:
            return {"status": "found", "source": "fallback", **value}

    for key, value in FALLBACK_KNOWLEDGE.items():
        if lower in key.lower() or key.lower() in lower:
            return {"status": "found", "source": "fallback", **value}

    # Not found
    return {
        "status": "not_found",
        "suggestions": suggestions(concept, knowledge),
        "fallback_advice": (
            "Try searching with a different name, or use search_prefect_docs "
            "for real-time documentation lookup."
        ),
    }


def suggestions(query: str, knowledge: dict[str, Any]) -> list[str]:
    """Generate suggestions for a not-found query.

    Args:
        query: The query that wasn't found.
        knowledge: The loaded knowledge dict.

    Returns:
        List of similar concept names.
    """
    all_keys = list(knowledge.keys()) + list(FALLBACK_KNOWLEDGE.keys())
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_keys: list[str] = []
    for k in all_keys:
        if k not in seen:
            seen.add(k)
            unique_keys.append(k)

    # Build case-insensitive lookup: lower → original case
    lower_to_orig: dict[str, str] = {k.lower(): k for k in unique_keys}
    lower_keys = list(lower_to_orig.keys())

    # Use difflib for fuzzy matching (case-insensitive)
    close = difflib.get_close_matches(query.lower(), lower_keys, n=5, cutoff=0.4)
    return [lower_to_orig[k] for k in close]

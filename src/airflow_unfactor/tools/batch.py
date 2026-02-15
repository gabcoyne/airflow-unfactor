"""Batch convert Airflow DAGs."""

import json
from pathlib import Path

from airflow_unfactor.tools.convert import convert_dag


async def batch_convert(
    directory: str,
    output_directory: str | None = None,
) -> str:
    """Convert multiple DAGs in a directory.

    Args:
        directory: Directory containing DAG files
        output_directory: Output directory (default: same as input with _prefect suffix)

    Returns:
        JSON with conversion report
    """
    input_dir = Path(directory)
    output_dir = Path(output_directory) if output_directory else input_dir.parent / f"{input_dir.name}_prefect"
    output_dir.mkdir(parents=True, exist_ok=True)

    converted = 0
    failed = 0
    skipped = 0
    errors = []

    for dag_file in input_dir.glob("*.py"):
        if dag_file.name.startswith("__"):
            skipped += 1
            continue

        try:
            result_json = await convert_dag(path=str(dag_file), include_comments=True)
            result = json.loads(result_json)

            if "error" in result:
                failed += 1
                errors.append({"file": dag_file.name, "error": result["error"]})
            else:
                output_file = output_dir / dag_file.name.replace(".py", "_flow.py")
                output_file.write_text(result.get("flow_code", ""))
                converted += 1
        except Exception as e:
            failed += 1
            errors.append({"file": dag_file.name, "error": str(e)})

    report = {
        "converted": converted,
        "failed": failed,
        "skipped": skipped,
        "output_directory": str(output_dir),
        "errors": errors if errors else None,
    }

    # Write report
    report_path = output_dir / "migration_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    report["report_path"] = str(report_path)

    return json.dumps(report, indent=2)
"""Read an Airflow DAG file and return raw source with minimal metadata.

The LLM reads the code directly — no AST parsing, no structural extraction.
"""

import json
from pathlib import Path


async def read_dag(
    path: str | None = None,
    content: str | None = None,
) -> str:
    """Read a DAG file and return the raw source code.

    Args:
        path: Path to a DAG file on disk.
        content: Inline DAG source code.

    Returns:
        JSON with source, file_path, file_size_bytes, line_count — or error.
    """
    if not path and not content:
        return json.dumps({"error": "Either path or content must be provided"})

    if content:
        return json.dumps(
            {
                "source": content,
                "file_path": None,
                "file_size_bytes": len(content.encode("utf-8")),
                "line_count": content.count("\n") + 1,
            }
        )

    assert path is not None  # guaranteed by early return above
    file = Path(path)
    if not file.exists():
        return json.dumps({"error": f"File not found: {path}", "source": None})

    source = file.read_text()
    return json.dumps(
        {
            "source": source,
            "file_path": str(file.resolve()),
            "file_size_bytes": file.stat().st_size,
            "line_count": source.count("\n") + 1,
        }
    )

"""airflow-unfactor MCP Server.

Provides tools for LLM-assisted conversion of Apache Airflow DAGs
to Prefect flows. The LLM reads raw DAG code and generates Prefect
flows using translation knowledge compiled by Colin.

Built with FastMCP.
"""

from fastmcp import FastMCP

from airflow_unfactor.tools.lookup import lookup_concept as _lookup_concept
from airflow_unfactor.tools.read_dag import read_dag as _read_dag
from airflow_unfactor.tools.scaffold import scaffold_project
from airflow_unfactor.tools.search_docs import search_prefect_docs as _search_docs
from airflow_unfactor.tools.validate import validate_conversion

mcp = FastMCP(
    "airflow-unfactor",
    instructions="""\
Airflow-to-Prefect migration assistant. You read raw DAG source code
directly and generate complete Prefect flows.

## Workflow

1. **read_dag** — Read the Airflow DAG file (returns raw source code for you to analyze)
2. **lookup_concept** — Query translation knowledge for Airflow→Prefect mappings
   (operators, patterns, connections, core concepts). Backed by Colin-compiled
   knowledge from live sources, with built-in fallback mappings.
3. **search_prefect_docs** — Search current Prefect documentation for anything
   not covered by lookup_concept (optional, requires network)
4. **Generate** — Write complete Prefect flow code based on the DAG source and
   translation knowledge
5. **validate** — Compare original DAG and generated flow (syntax check on the
   generated code + both sources returned for your structural comparison)
6. **scaffold** — Create Prefect project directory structure (optional)

## Key principles

- You read raw code directly — there is no AST intermediary
- lookup_concept is pre-compiled from live Airflow source and Prefect docs
- search_prefect_docs queries real-time Prefect documentation for gaps
- validate returns both sources so you can verify the conversion yourself
""",
)


@mcp.tool
async def read_dag(
    path: str | None = None,
    content: str | None = None,
) -> str:
    """Read an Airflow DAG file and return raw source with metadata.

    Accepts a file path or inline content. Returns the source code,
    file path, size, and line count. The LLM reads the code directly.

    Args:
        path: Path to a DAG file on disk.
        content: Inline DAG source code.

    Returns:
        JSON with source, file_path, file_size_bytes, line_count — or error.
    """
    return await _read_dag(path=path, content=content)


@mcp.tool
async def lookup_concept(concept: str) -> str:
    """Look up Airflow→Prefect translation knowledge for a concept.

    Searches Colin-compiled knowledge for operators, patterns,
    connections, and core concepts. Falls back to built-in mappings
    if Colin output is not available.

    Args:
        concept: The Airflow concept to look up (e.g. "PythonOperator",
                "XCom", "TaskGroup", "postgres_default").

    Returns:
        JSON with concept_type, airflow info, prefect_equivalent,
        translation_rules, and source ("colin" or "fallback").
    """
    return await _lookup_concept(concept)


@mcp.tool
async def search_prefect_docs(query: str) -> str:
    """Search current Prefect documentation via the Prefect MCP server.

    For real-time queries beyond what Colin pre-compiled. Returns
    search results or an error with suggestion to run 'colin run'.

    Args:
        query: Search query for Prefect docs.

    Returns:
        JSON with search results or error.
    """
    return await _search_docs(query)


@mcp.tool
async def validate(
    original_dag: str,
    converted_flow: str,
) -> str:
    """Validate a converted Prefect flow against the original Airflow DAG.

    Returns both source files for comparison plus a syntax check on
    the generated code. You perform the structural comparison.

    Args:
        original_dag: Path or inline content of the original DAG.
        converted_flow: Path or inline content of the generated flow.

    Returns:
        JSON with original_source, converted_source, syntax_valid,
        syntax_errors, and comparison_guidance.
    """
    return await validate_conversion(original_dag, converted_flow)


@mcp.tool
async def scaffold(
    output_directory: str,
    project_name: str | None = None,
    workspace: str = "default",
    flow_names: list[str] | None = None,
    include_docker: bool = True,
    include_github_actions: bool = True,
    schedule_interval: str | None = None,
) -> str:
    """Generate a Prefect project directory structure.

    Creates the project skeleton following prefecthq/flows conventions.
    Does NOT generate flow code - that's for the LLM to do.

    Args:
        output_directory: Where to create the project
        project_name: Project name (defaults to directory name)
        workspace: Workspace name for deployments/<workspace>/ structure
        flow_names: List of flow names to create directories for
        include_docker: Include Dockerfile template
        include_github_actions: Include CI workflow template
        schedule_interval: Cron string, preset (@daily etc.), seconds, or None.

    Returns:
        JSON with created_directories, created_files, prefect_yaml_template, next_steps
    """
    return await scaffold_project(
        output_directory=output_directory,
        project_name=project_name,
        include_docker=include_docker,
        include_github_actions=include_github_actions,
        schedule_interval=schedule_interval,
    )


def main() -> None:
    """Run the MCP server over stdio."""
    import logging
    import sys
    from pathlib import Path

    if len(sys.argv) > 1:
        print(f"error: unrecognized arguments: {' '.join(sys.argv[1:])}", file=sys.stderr)
        sys.exit(2)

    colin_dir = Path("colin/output")
    if not colin_dir.exists() or not list(colin_dir.glob("*.json")):
        logging.getLogger("airflow_unfactor").warning(
            "Colin output directory missing or empty (%s). "
            "Run `colin run` to compile translation knowledge. "
            "Falling back to built-in operator mappings.",
            colin_dir,
        )

    mcp.run()


if __name__ == "__main__":
    main()

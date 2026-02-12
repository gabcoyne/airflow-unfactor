"""airflow-unfactor MCP Server.

Converts Apache Airflow DAGs to Prefect flows with AI assistance.
Built with FastMCP - the fast, Pythonic way to build MCP servers.
"""

from typing import Optional
from fastmcp import FastMCP

from airflow_unfactor.tools.analyze import analyze_dag
from airflow_unfactor.tools.convert import convert_dag
from airflow_unfactor.tools.validate import validate_conversion
from airflow_unfactor.tools.explain import explain_concept
from airflow_unfactor.tools.batch import batch_convert
from airflow_unfactor.tools.external import prefect_search, astronomer_migration


mcp = FastMCP(
    "airflow-unfactor",
    instructions="Convert Apache Airflow DAGs to Prefect flows with confidence",
)


@mcp.tool
async def analyze(path: Optional[str] = None, content: Optional[str] = None, include_external_context: bool = True) -> str:
    """Analyze an Airflow DAG to understand its structure.

    Args:
        path: Path to the DAG file
        content: DAG code content (alternative to path)

    Returns:
        JSON with operators, dependencies, XCom usage, and complexity score
    """
    return await analyze_dag(path=path, content=content, include_external_context=include_external_context)


@mcp.tool
async def convert(
    path: Optional[str] = None,
    content: Optional[str] = None,
    include_comments: bool = True,
    generate_tests: bool = True,
    include_external_context: bool = True,
) -> str:
    """Convert an Airflow DAG to a Prefect flow.

    Args:
        path: Path to the DAG file
        content: DAG code content (alternative to path)
        include_comments: Include educational comments explaining Prefect advantages
        generate_tests: Generate pytest tests for the converted flow
        include_external_context: Enrich conversion with external MCP context

    Returns:
        JSON with flow_code, test_code, warnings, task mapping,
        dataset conversion outputs, and migration runbook
    """
    return await convert_dag(
        path=path,
        content=content,
        include_comments=include_comments,
        generate_tests=generate_tests,
        include_external_context=include_external_context,
    )


@mcp.tool
async def validate(original_dag: str, converted_flow: str) -> str:
    """Validate that a converted flow matches the original DAG.

    Args:
        original_dag: Path or content of the original Airflow DAG
        converted_flow: Path or content of the converted Prefect flow

    Returns:
        JSON with validation results and test suggestions
    """
    return await validate_conversion(
        original_dag=original_dag,
        converted_flow=converted_flow,
    )


@mcp.tool
async def explain(concept: str, include_external_context: bool = True) -> str:
    """Explain an Airflow concept and its Prefect equivalent.

    Args:
        concept: Airflow concept (XCom, Sensor, Executor, Hook, Connection, Variable)

    Returns:
        JSON with explanation, advantages, and code examples
    """
    return await explain_concept(concept=concept, include_external_context=include_external_context)


@mcp.tool
async def batch(
    directory: str,
    output_directory: Optional[str] = None,
) -> str:
    """Convert multiple DAGs in a directory.

    Args:
        directory: Directory containing Airflow DAG files
        output_directory: Output directory for converted flows (default: {directory}_prefect)

    Returns:
        JSON with conversion report (converted, failed, skipped counts)
    """
    return await batch_convert(
        directory=directory,
        output_directory=output_directory,
    )


@mcp.tool
async def prefect_search_tool(query: str) -> str:
    """Proxy to Prefect MCP search."""
    return await prefect_search(query)


@mcp.tool
async def astronomer_migration_tool(query: str) -> str:
    """Proxy to Astronomer Airflow 2→3 migration MCP tool."""
    return await astronomer_migration(query)


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()

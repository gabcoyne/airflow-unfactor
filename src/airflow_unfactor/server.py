"""airflow-unfactor MCP Server.

Converts Apache Airflow DAGs to Prefect flows with AI assistance.
Built with FastMCP - the fast, Pythonic way to build MCP servers.
"""

from fastmcp import FastMCP

from airflow_unfactor.tools.analyze import analyze_dag
from airflow_unfactor.tools.batch import batch_convert
from airflow_unfactor.tools.convert import convert_dag
from airflow_unfactor.tools.explain import explain_concept
from airflow_unfactor.tools.external import astronomer_migration, prefect_search
from airflow_unfactor.tools.scaffold import scaffold_project
from airflow_unfactor.tools.validate import validate_conversion

mcp = FastMCP(
    "airflow-unfactor",
    instructions="Convert Apache Airflow DAGs to Prefect flows with confidence",
)


@mcp.tool
async def analyze(
    path: str | None = None, content: str | None = None, include_external_context: bool = True
) -> str:
    """Analyze an Airflow DAG to understand its structure.

    Args:
        path: Path to the DAG file
        content: DAG code content (alternative to path)

    Returns:
        JSON with operators, dependencies, XCom usage, and complexity score
    """
    return await analyze_dag(
        path=path, content=content, include_external_context=include_external_context
    )


@mcp.tool
async def convert(
    path: str | None = None,
    content: str | None = None,
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
    output_directory: str | None = None,
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
async def scaffold(
    dags_directory: str,
    output_directory: str,
    project_name: str | None = None,
    include_docker: bool = True,
    include_github_actions: bool = True,
) -> str:
    """Generate a clean project skeleton with migrated flows.

    Creates a well-organized project structure following Prefect best practices.

    Args:
        dags_directory: Directory containing Airflow DAG files to migrate
        output_directory: Where to create the new project
        project_name: Project name (defaults to directory name)
        include_docker: Include Dockerfile and docker-compose.yml
        include_github_actions: Include CI workflow

    Returns:
        JSON with scaffold report (converted counts, project structure)
    """
    return await scaffold_project(
        dags_directory=dags_directory,
        output_directory=output_directory,
        project_name=project_name,
        include_docker=include_docker,
        include_github_actions=include_github_actions,
    )


@mcp.tool
async def prefect_search_tool(query: str) -> str:
    """Proxy to Prefect MCP search."""
    return await prefect_search(query)


@mcp.tool
async def astronomer_migration_tool(query: str) -> str:
    """Proxy to Astronomer Airflow 2→3 migration MCP tool."""
    return await astronomer_migration(query)


def main() -> None:
    """Run the MCP server or HTTP server with wizard UI.

    By default, runs the MCP server over stdio for use with MCP clients.
    With --ui flag, starts an HTTP server with the wizard UI.
    """
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(
        description="Convert Apache Airflow DAGs to Prefect flows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  airflow-unfactor              # Run MCP server (default)
  airflow-unfactor --ui         # Start wizard UI at http://localhost:8765
  airflow-unfactor --ui --port 9000  # Custom port
        """,
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Start HTTP server with wizard UI instead of MCP server",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port for HTTP server (default: 8765)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Host to bind HTTP server (default: localhost)",
    )

    args = parser.parse_args()

    if args.ui:
        from airflow_unfactor.http_server import run_server

        try:
            asyncio.run(run_server(port=args.port, host=args.host))
        except KeyboardInterrupt:
            print("\nShutting down...")
    else:
        mcp.run()


if __name__ == "__main__":
    main()

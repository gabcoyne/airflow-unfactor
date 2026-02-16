"""airflow-unfactor MCP Server.

Provides rich analysis payloads for LLM-assisted conversion of
Apache Airflow DAGs to Prefect flows.

Built with FastMCP - the fast, Pythonic way to build MCP servers.
"""

from fastmcp import FastMCP

from airflow_unfactor.tools.analyze import analyze_dag
from airflow_unfactor.tools.context import (
    get_connection_mapping,
    get_operator_mapping,
    get_prefect_context,
)
from airflow_unfactor.tools.external import astronomer_migration as _astronomer_migration
from airflow_unfactor.tools.external import prefect_search as _prefect_search
from airflow_unfactor.tools.scaffold import scaffold_project
from airflow_unfactor.tools.validate import validate_conversion

mcp = FastMCP(
    "airflow-unfactor",
    instructions="""Airflow-to-Prefect migration assistant.

Use these tools to analyze Airflow DAGs and get context for generating Prefect flows.

Recommended workflow:
1. analyze() - Get comprehensive DAG analysis payload
2. get_context() - Fetch relevant Prefect documentation
3. Generate Prefect flow code using the analysis and context
4. validate() - Verify the generated code matches the original structure

The LLM should generate complete, functional Prefect flows - not this tool.
This tool provides rich analysis payloads to inform that generation.""",
)


# =============================================================================
# ANALYSIS TOOLS - Primary tools for understanding Airflow DAGs
# =============================================================================


@mcp.tool
async def analyze(
    path: str | None = None,
    content: str | None = None,
    include_external_context: bool = True,
) -> str:
    """Analyze an Airflow DAG and return a rich structured payload for LLM conversion.

    This is the primary analysis tool. It extracts comprehensive information from
    the DAG including structure, patterns, configuration, and migration notes.

    Args:
        path: Path to the DAG file
        content: DAG code content (alternative to path)
        include_external_context: Enrich with external MCP context (Prefect docs, etc.)

    Returns:
        JSON with comprehensive analysis:
        - dag_id, airflow_version detection
        - structure: operators, dependencies, task_groups, imports
        - patterns: xcom, sensors, trigger_rules, branching, connections, variables
        - dag_config: schedule, catchup, default_args, tags
        - complexity: score and factors
        - migration_notes: actionable conversion guidance
        - original_code: for LLM reference
    """
    return await analyze_dag(
        path=path, content=content, include_external_context=include_external_context
    )


# =============================================================================
# CONTEXT TOOLS - Fetch Prefect documentation and patterns
# =============================================================================


@mcp.tool
async def get_context(
    topics: list[str] | None = None,
    detected_features: list[str] | None = None,
) -> str:
    """Fetch relevant Prefect documentation and patterns for conversion.

    Call this BEFORE generating Prefect code to get up-to-date patterns
    and best practices.

    Args:
        topics: Topics to fetch docs for. Options:
            - "flows" - Flow decorator best practices
            - "tasks" - Task decorator, retries, configuration
            - "blocks" - Credentials and configuration blocks
            - "deployments" - prefect.yaml configuration
            - "work_pools" - Kubernetes, Docker work pool setup
            - "events" - Event-driven automations and triggers

        detected_features: Features found in the DAG to get specific guidance:
            - "sensors" - Polling patterns, event triggers
            - "xcom" - Data passing with return values
            - "taskflow" - TaskFlow API migration
            - "datasets" - Event-driven dependencies
            - "branching" - Conditional execution
            - "dynamic_mapping" - .map() usage
            - "task_groups" - Subflow patterns
            - "connections" - Block configuration
            - "variables" - Variable/secret management

    Returns:
        JSON with:
        - documentation: Relevant Prefect docs
        - operator_patterns: Airflow→Prefect operator mappings
        - connection_mappings: Connection→Block type mappings
        - deployment_template: prefect.yaml structure and examples
    """
    return await get_prefect_context(topics=topics, detected_features=detected_features)


@mcp.tool
async def operator_mapping(operator_type: str) -> str:
    """Get detailed Prefect equivalent for a specific Airflow operator.

    Args:
        operator_type: The Airflow operator (e.g., "PythonOperator", "S3KeySensor")

    Returns:
        JSON with:
        - prefect_pattern: The Prefect equivalent approach
        - example: Code example
        - notes: Migration considerations
    """
    return await get_operator_mapping(operator_type)


@mcp.tool
async def connection_mapping(connection_id: str) -> str:
    """Get Prefect block mapping for an Airflow connection.

    Args:
        connection_id: The Airflow connection ID (e.g., "aws_default", "postgres_conn")

    Returns:
        JSON with:
        - block_type: Prefect block type to use
        - package: prefect integration package
        - notes: Configuration guidance
    """
    return await get_connection_mapping(connection_id)


# =============================================================================
# VALIDATION TOOLS - Verify generated code
# =============================================================================


@mcp.tool
async def validate(original_dag: str, converted_flow: str) -> str:
    """Validate that generated Prefect code matches the original DAG structure.

    Use this after the LLM generates code to verify:
    - All tasks are accounted for
    - Dependencies are preserved
    - Configuration is complete

    Args:
        original_dag: Path or content of the original Airflow DAG
        converted_flow: Path or content of the generated Prefect flow

    Returns:
        JSON with:
        - is_valid: Overall validation status
        - task_coverage: Tasks present in both
        - missing_tasks: Tasks not converted
        - dependency_check: Dependency graph comparison
        - suggestions: Improvement recommendations
    """
    return await validate_conversion(
        original_dag=original_dag,
        converted_flow=converted_flow,
    )


# =============================================================================
# SCAFFOLDING TOOLS - Project structure (not code generation)
# =============================================================================


@mcp.tool
async def scaffold(
    output_directory: str,
    project_name: str | None = None,
    workspace: str = "default",
    flow_names: list[str] | None = None,
    include_docker: bool = True,
    include_github_actions: bool = True,
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

    Returns:
        JSON with:
        - created_directories: List of directories created
        - created_files: List of template files created
        - prefect_yaml_template: Template for prefect.yaml
        - next_steps: What to do after scaffolding
    """
    return await scaffold_project(
        output_directory=output_directory,
        project_name=project_name,
        include_docker=include_docker,
        include_github_actions=include_github_actions,
    )


# =============================================================================
# EXTERNAL MCP PROXIES - Access to Prefect and Astronomer MCPs
# =============================================================================


@mcp.tool
async def prefect_search(query: str) -> str:
    """Search Prefect documentation via the Prefect MCP server.

    Use this to fetch current Prefect documentation and patterns.

    Args:
        query: Search query for Prefect docs

    Returns:
        Search results from Prefect documentation
    """
    return await _prefect_search(query)


@mcp.tool
async def astronomer_migration(query: str) -> str:
    """Get Airflow 2→3 migration guidance from Astronomer MCP.

    Useful for understanding Airflow changes before converting to Prefect.

    Args:
        query: Migration question or topic

    Returns:
        Migration guidance from Astronomer
    """
    return await _astronomer_migration(query)


def main() -> None:
    """Run the MCP server or HTTP server with wizard UI.

    By default, runs the MCP server over stdio for use with MCP clients.
    With --ui flag, starts an HTTP server with the wizard UI.
    """
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(
        description="Analyze Apache Airflow DAGs for LLM-assisted Prefect conversion",
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

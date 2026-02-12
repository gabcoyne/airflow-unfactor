"""airflow-unfactor MCP Server.

Converts Apache Airflow DAGs to Prefect flows with AI assistance.
"""

import asyncio
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from airflow_unfactor.tools.analyze import analyze_dag
from airflow_unfactor.tools.convert import convert_dag
from airflow_unfactor.tools.validate import validate_conversion
from airflow_unfactor.tools.explain import explain_concept
from airflow_unfactor.tools.batch import batch_convert

logger = logging.getLogger(__name__)

app = Server("airflow-unfactor")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="analyze_dag",
            description="Analyze an Airflow DAG file to understand its structure, operators, and complexity.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to DAG file"},
                    "content": {"type": "string", "description": "DAG code (if not using path)"},
                },
            },
        ),
        Tool(
            name="convert_dag",
            description="Convert an Airflow DAG to a Prefect flow with educational comments.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to DAG file"},
                    "content": {"type": "string", "description": "DAG code (if not using path)"},
                    "include_comments": {"type": "boolean", "default": True},
                },
            },
        ),
        Tool(
            name="validate_conversion",
            description="Validate that a converted Prefect flow is behaviorally equivalent to the original DAG.",
            inputSchema={
                "type": "object",
                "properties": {
                    "original_dag": {"type": "string", "description": "Original DAG path or content"},
                    "converted_flow": {"type": "string", "description": "Converted flow path or content"},
                },
                "required": ["original_dag", "converted_flow"],
            },
        ),
        Tool(
            name="explain_concept",
            description="Explain an Airflow concept and its Prefect equivalent.",
            inputSchema={
                "type": "object",
                "properties": {
                    "concept": {
                        "type": "string",
                        "description": "Airflow concept (XCom, Sensor, Executor, Hook, Connection, Variable)",
                    },
                },
                "required": ["concept"],
            },
        ),
        Tool(
            name="batch_convert",
            description="Convert multiple DAGs in a directory.",
            inputSchema={
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "Directory containing DAG files"},
                    "output_directory": {"type": "string", "description": "Output directory for flows"},
                },
                "required": ["directory"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    handlers = {
        "analyze_dag": analyze_dag,
        "convert_dag": convert_dag,
        "validate_conversion": validate_conversion,
        "explain_concept": explain_concept,
        "batch_convert": batch_convert,
    }

    handler = handlers.get(name)
    if not handler:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    try:
        result = await handler(**arguments)
        return [TextContent(type="text", text=result)]
    except Exception as e:
        logger.exception(f"Error in {name}")
        return [TextContent(type="text", text=f"Error: {e}")]


async def run_server():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main():
    """Entry point."""
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
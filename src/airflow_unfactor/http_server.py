"""HTTP server for wizard UI and API.

Provides REST API endpoints for the wizard UI to call the MCP tools,
and serves the embedded wizard UI when --ui mode is enabled.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from aiohttp import web
from aiohttp.web import Request, Response

from airflow_unfactor.tools.analyze import analyze_dag
from airflow_unfactor.tools.convert import convert_dag
from airflow_unfactor.tools.scaffold import scaffold_project
from airflow_unfactor.tools.validate import validate_conversion

logger = logging.getLogger(__name__)


def json_response(data: dict[str, Any], status: int = 200) -> Response:
    """Create a JSON response."""
    return web.json_response(data, status=status)


def error_response(message: str, details: str | None = None, status: int = 400) -> Response:
    """Create an error response."""
    error_data: dict[str, Any] = {"error": message}
    if details:
        error_data["details"] = details
    return web.json_response(error_data, status=status)


async def analyze_handler(request: Request) -> Response:
    """Handle /api/analyze requests."""
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return error_response("Invalid JSON")

    path = data.get("path")
    content = data.get("content")

    if not path and not content:
        return error_response("Either 'path' or 'content' is required")

    try:
        result = await analyze_dag(path=path, content=content)
        return json_response(json.loads(result))
    except Exception as e:
        logger.exception("Analysis failed")
        return error_response("Analysis failed", str(e), status=500)


async def convert_handler(request: Request) -> Response:
    """Handle /api/convert requests."""
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return error_response("Invalid JSON")

    path = data.get("path")
    content = data.get("content")

    if not path and not content:
        return error_response("Either 'path' or 'content' is required")

    try:
        result = await convert_dag(
            path=path,
            content=content,
            include_comments=data.get("include_comments", True),
            generate_tests=data.get("generate_tests", True),
            include_external_context=data.get("include_external_context", False),
        )
        return json_response(json.loads(result))
    except Exception as e:
        logger.exception("Conversion failed")
        return error_response("Conversion failed", str(e), status=500)


async def validate_handler(request: Request) -> Response:
    """Handle /api/validate requests."""
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return error_response("Invalid JSON")

    original_dag = data.get("original_dag")
    converted_flow = data.get("converted_flow")

    if not original_dag or not converted_flow:
        return error_response("Both 'original_dag' and 'converted_flow' are required")

    try:
        result = await validate_conversion(
            original_dag=original_dag,
            converted_flow=converted_flow,
        )
        return json_response(json.loads(result))
    except Exception as e:
        logger.exception("Validation failed")
        return error_response("Validation failed", str(e), status=500)


async def scaffold_handler(request: Request) -> Response:
    """Handle /api/scaffold requests."""
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return error_response("Invalid JSON")

    dags_directory = data.get("dags_directory")
    output_directory = data.get("output_directory")

    if not dags_directory or not output_directory:
        return error_response("Both 'dags_directory' and 'output_directory' are required")

    try:
        result = await scaffold_project(
            dags_directory=dags_directory,
            output_directory=output_directory,
            project_name=data.get("project_name"),
            include_docker=data.get("include_docker", True),
            include_github_actions=data.get("include_github_actions", True),
        )
        return json_response(json.loads(result))
    except Exception as e:
        logger.exception("Scaffold failed")
        return error_response("Scaffold failed", str(e), status=500)


async def health_handler(request: Request) -> Response:
    """Handle /health requests."""
    from datetime import UTC, datetime

    return json_response({
        "status": "ok",
        "version": "0.1.0",
        "timestamp": datetime.now(UTC).isoformat(),
    })


def get_ui_path() -> Path | None:
    """Get path to embedded UI directory."""
    # Check for UI in package
    ui_dir = Path(__file__).parent / "ui"
    if ui_dir.exists() and (ui_dir / "index.html").exists():
        return ui_dir

    # Check for development build
    dev_ui = Path(__file__).parent.parent.parent.parent / "mcp-app" / "dist"
    if dev_ui.exists() and (dev_ui / "index.html").exists():
        return dev_ui

    return None


@web.middleware
async def cors_middleware(request: Request, handler: Any) -> Response:
    """Add CORS headers to all responses."""
    if request.method == "OPTIONS":
        return web.Response(
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            }
        )

    response = await handler(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


def create_app(ui_path: Path | None = None) -> web.Application:
    """Create the HTTP application.

    Args:
        ui_path: Path to UI directory. If None, UI won't be served.

    Returns:
        Configured aiohttp Application.
    """
    app = web.Application(middlewares=[cors_middleware])

    # API routes
    app.router.add_post("/api/analyze", analyze_handler)
    app.router.add_post("/api/convert", convert_handler)
    app.router.add_post("/api/validate", validate_handler)
    app.router.add_post("/api/scaffold", scaffold_handler)
    app.router.add_get("/health", health_handler)

    # Serve UI if available
    if ui_path and ui_path.exists():
        async def index_handler(request: Request) -> Response:
            index_file = ui_path / "index.html"
            return web.FileResponse(index_file)

        app.router.add_get("/", index_handler)
        # Serve static assets if they exist separately
        if (ui_path / "assets").exists():
            app.router.add_static("/assets", ui_path / "assets")

    return app


async def run_server(port: int = 8765, host: str = "localhost") -> None:
    """Run the HTTP server.

    Args:
        port: Port to listen on.
        host: Host to bind to.
    """
    ui_path = get_ui_path()
    app = create_app(ui_path)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()

    print(f"airflow-unfactor HTTP server running at http://{host}:{port}")
    print(f"  API endpoints: http://{host}:{port}/api/...")
    print(f"  Health check:  http://{host}:{port}/health")

    if ui_path:
        print(f"  Wizard UI:     http://{host}:{port}/")
    else:
        print("  Wizard UI:     Not available (run npm run build in mcp-app/)")

    # Keep running until interrupted
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await runner.cleanup()

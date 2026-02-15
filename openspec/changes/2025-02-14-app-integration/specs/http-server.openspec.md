# Spec: HTTP Server Mode

## Overview

Add an HTTP server mode to airflow-unfactor that serves both API endpoints and the wizard UI.

## Interface

### CLI

```bash
# Default: MCP server over stdio
airflow-unfactor

# HTTP server with wizard UI
airflow-unfactor --ui

# Custom port
airflow-unfactor --ui --port 9000

# Help
airflow-unfactor --help
```

### API Endpoints

All endpoints accept JSON and return JSON.

#### POST /api/analyze

Analyze a DAG file.

**Request:**
```json
{
  "path": "/path/to/dag.py",
  // OR
  "content": "from airflow import DAG..."
}
```

**Response:**
```json
{
  "dag_id": "my_dag",
  "operators": [{"type": "PythonOperator", "task_id": "extract", "count": 1}],
  "dependencies": [["extract", "transform"]],
  "complexity_score": 42,
  "conversion_notes": ["Uses TaskFlow API"]
}
```

#### POST /api/convert

Convert a DAG to Prefect flow.

**Request:**
```json
{
  "path": "/path/to/dag.py",
  "include_comments": true,
  "generate_tests": true
}
```

**Response:**
```json
{
  "flow_code": "@flow...",
  "test_code": "def test_...",
  "warnings": ["Custom operator detected"],
  "original_to_new_mapping": {"extract": "extract_task"}
}
```

#### POST /api/validate

Validate a conversion.

**Request:**
```json
{
  "original_dag": "/path/to/dag.py",
  "converted_flow": "@flow..."
}
```

**Response:**
```json
{
  "is_valid": true,
  "confidence_score": 85,
  "issues": [],
  "suggestions": []
}
```

#### POST /api/scaffold

Generate project structure.

**Request:**
```json
{
  "dags_directory": "/path/to/dags",
  "output_directory": "/path/to/output",
  "project_name": "my-prefect-project",
  "include_docker": true,
  "include_github_actions": true
}
```

**Response:**
```json
{
  "files_created": ["flows/my_flow.py", "tests/test_my_flow.py"],
  "project_structure": "...",
  "warnings": []
}
```

#### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "timestamp": "2025-02-14T12:00:00Z"
}
```

### Static Files

When `--ui` is passed:
- `/` serves `index.html`
- All other static assets served from embedded UI bundle

## Implementation

### Module: `src/airflow_unfactor/http_server.py`

```python
"""HTTP server for wizard UI and API."""

import json
from aiohttp import web
from airflow_unfactor.tools.analyze import analyze_dag
from airflow_unfactor.tools.convert import convert_dag
from airflow_unfactor.tools.validate import validate_conversion
from airflow_unfactor.tools.scaffold import scaffold_project

async def analyze_handler(request: web.Request) -> web.Response:
    data = await request.json()
    result = await analyze_dag(**data)
    return web.json_response(json.loads(result))

# ... other handlers ...

def create_app(ui_path: str | None = None) -> web.Application:
    app = web.Application()
    app.router.add_post('/api/analyze', analyze_handler)
    app.router.add_post('/api/convert', convert_handler)
    app.router.add_post('/api/validate', validate_handler)
    app.router.add_post('/api/scaffold', scaffold_handler)
    app.router.add_get('/health', health_handler)

    if ui_path:
        app.router.add_static('/', ui_path)

    return app

async def run_server(port: int = 8765, with_ui: bool = True):
    ui_path = get_ui_path() if with_ui else None
    app = create_app(ui_path)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', port)
    await site.start()
    print(f"Server running at http://localhost:{port}")
    if with_ui:
        print(f"Wizard UI at http://localhost:{port}/")
```

### Server Entry Point Updates

```python
# server.py additions

def main():
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(
        description='Airflow to Prefect migration tool'
    )
    parser.add_argument(
        '--ui', action='store_true',
        help='Start HTTP server with wizard UI'
    )
    parser.add_argument(
        '--port', type=int, default=8765,
        help='Port for HTTP server (default: 8765)'
    )
    args = parser.parse_args()

    if args.ui:
        from airflow_unfactor.http_server import run_server
        asyncio.run(run_server(port=args.port))
    else:
        mcp.run()
```

## Error Handling

All API errors return JSON with:
```json
{
  "error": "Error message",
  "details": "Optional details"
}
```

HTTP status codes:
- 200: Success
- 400: Bad request (invalid JSON, missing fields)
- 500: Server error (conversion failed, etc.)

## CORS

Enable CORS for all origins in development. In production, restrict to same-origin.

## Security

- No authentication required (local development tool)
- File paths validated to prevent directory traversal
- Only read operations on user files (no writes except scaffold output)

## Testing

```python
# tests/test_http_server.py

import pytest
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from airflow_unfactor.http_server import create_app

class TestHTTPServer(AioHTTPTestCase):
    async def get_application(self):
        return create_app(ui_path=None)

    @unittest_run_loop
    async def test_health(self):
        response = await self.client.get('/health')
        assert response.status == 200
        data = await response.json()
        assert data['status'] == 'ok'

    @unittest_run_loop
    async def test_analyze(self):
        response = await self.client.post('/api/analyze', json={
            'content': 'from airflow import DAG...'
        })
        assert response.status == 200
```

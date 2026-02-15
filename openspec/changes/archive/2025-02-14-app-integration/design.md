# Design: MCP App Integration

## Architecture

### Current State

```
┌─────────────────────────┐     ┌─────────────────────────┐
│   Python MCP Server     │     │  TypeScript MCP Server  │
│   (airflow-unfactor)    │     │     (mcp-app)           │
│                         │     │                         │
│  - analyze              │◄────│  - wizard/analyze       │
│  - convert              │     │  - wizard/convert       │
│  - validate             │     │  - wizard/validate      │
│  - explain              │     │  - wizard/scaffold      │
│  - batch                │     │  - migration-wizard     │
│  - scaffold             │     │                         │
│                         │     │  + serves UI resource   │
│  Port: stdio            │     │  Port: 3002             │
└─────────────────────────┘     └─────────────────────────┘
                                         ▲
                                         │
                              Expects Python at :3001
                              (doesn't exist)
```

### Proposed State

```
┌─────────────────────────────────────────────────────────┐
│              Python MCP Server (airflow-unfactor)        │
│                                                          │
│  MCP Tools (stdio or HTTP):                             │
│  - analyze, convert, validate, explain, batch, scaffold │
│                                                          │
│  HTTP Server (--ui mode):                               │
│  - /mcp        → MCP-over-HTTP                          │
│  - /api/*      → Tool API endpoints                     │
│  - /           → Serve wizard UI (embedded)             │
│                                                          │
│  Port: 8765 (configurable)                              │
└─────────────────────────────────────────────────────────┘
```

## Implementation Approach

### Option A: Embed UI in Python (Recommended)

1. Build mcp-app to produce dist/index.html (single file)
2. Include built HTML in Python package
3. Python serves it via HTTP when `--ui` flag passed
4. UI makes API calls to same Python server

**Pros:**
- Single process, single command
- No TypeScript runtime needed by users
- Simpler deployment

**Cons:**
- Need to rebuild UI on changes
- Larger package size

### Option B: Keep Separate Servers

1. Document the two-server setup
2. Add `docker-compose.yml` for easy orchestration
3. MCP App proxies to Python server

**Pros:**
- Clean separation
- Can develop UI independently

**Cons:**
- Complex user setup
- Two processes to manage
- Confusing for newcomers

## Decision: Option A (Embed UI)

## Implementation Details

### 1. Python Server Changes

```python
# server.py
import argparse
from fastmcp import FastMCP
from aiohttp import web  # Add dependency

mcp = FastMCP("airflow-unfactor")

# ... existing tools ...

async def create_api_app():
    """Create HTTP API for wizard UI."""
    app = web.Application()

    async def analyze_handler(request):
        data = await request.json()
        result = await analyze_dag(**data)
        return web.json_response(json.loads(result))

    async def convert_handler(request):
        data = await request.json()
        result = await convert_dag(**data)
        return web.json_response(json.loads(result))

    app.router.add_post('/api/analyze', analyze_handler)
    app.router.add_post('/api/convert', convert_handler)
    app.router.add_post('/api/validate', validate_handler)
    app.router.add_post('/api/scaffold', scaffold_handler)

    # Serve embedded UI
    app.router.add_static('/', get_ui_path())

    return app

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ui', action='store_true',
                        help='Start HTTP server with wizard UI')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()

    if args.ui:
        asyncio.run(start_http_server(args.port))
    else:
        mcp.run()  # Default: stdio MCP
```

### 2. MCP App Build Integration

```toml
# pyproject.toml additions
[project.optional-dependencies]
ui = [
    "aiohttp>=3.9.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/airflow_unfactor"]
include = [
    "src/airflow_unfactor/ui/index.html",
]
```

### 3. Build Pipeline

```yaml
# .github/workflows/build-ui.yml
name: Build UI

on:
  push:
    paths:
      - 'mcp-app/**'
  pull_request:
    paths:
      - 'mcp-app/**'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
          cache-dependency-path: mcp-app/package-lock.json

      - name: Install & Build
        working-directory: mcp-app
        run: |
          npm ci
          npm run build

      - name: Copy to Python package
        run: |
          mkdir -p src/airflow_unfactor/ui
          cp mcp-app/dist/index.html src/airflow_unfactor/ui/

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: ui-build
          path: src/airflow_unfactor/ui/
```

### 4. UI Code Updates

Update mcp-app to call relative API endpoints:

```typescript
// src/lib/api.ts
const API_BASE = window.location.origin;

export async function analyzeDAG(path: string) {
  const response = await fetch(`${API_BASE}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  });
  return response.json();
}
```

## Documentation Structure

### Jekyll docs/ additions

```
docs/
├── wizard/
│   ├── index.md         # Wizard overview
│   ├── quickstart.md    # Getting started with wizard
│   ├── steps.md         # Wizard step reference
│   └── deployment.md    # Production deployment
├── configuration/
│   ├── external-mcp.md  # External MCP setup
│   └── environment.md   # Environment variables
```

## Migration Path

1. Build mcp-app and embed in Python package
2. Add `--ui` mode to Python server
3. Update README with wizard instructions
4. Remove TypeScript MCP server (server.ts)
5. Keep mcp-app/src for UI development only
6. Remove docs-site/ after content migration
7. Update CI to build UI as part of release

## Testing Strategy

- Unit tests for new HTTP handlers
- E2E test: start server with --ui, verify wizard loads
- Snapshot test: wizard renders correctly

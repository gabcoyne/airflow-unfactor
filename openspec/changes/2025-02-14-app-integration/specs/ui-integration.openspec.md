# Spec: UI Build Integration

## Overview

Integrate the mcp-app wizard UI with the Python package so it can be served when `--ui` is passed.

## Build Process

### Local Development

```bash
# Build UI and copy to Python package
./scripts/build-ui.sh

# Or manually:
cd mcp-app
npm ci
npm run build
cp dist/index.html ../src/airflow_unfactor/ui/
```

### CI Build

The UI is built and bundled into the Python package during release:

```yaml
# .github/workflows/release.yml
jobs:
  build:
    steps:
      - name: Build UI
        working-directory: mcp-app
        run: |
          npm ci
          npm run build
          mkdir -p ../src/airflow_unfactor/ui
          cp dist/index.html ../src/airflow_unfactor/ui/

      - name: Build Python package
        run: python -m build
```

## UI Changes Required

### 1. Remove TypeScript MCP Server

Delete `mcp-app/server.ts` - no longer needed since Python serves the UI.

### 2. Update API Calls

Change from hardcoded URLs to relative:

```typescript
// Before (mcp-app/src/lib/api.ts)
const PYTHON_SERVER_URL = "http://localhost:3001";

// After
const API_BASE = "";  // Same origin

export async function analyzeDAG(path: string) {
  const response = await fetch(`${API_BASE}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Analysis failed');
  }
  return response.json();
}

export async function convertDAG(options: ConvertOptions) {
  const response = await fetch(`${API_BASE}/api/convert`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(options),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Conversion failed');
  }
  return response.json();
}

// ... similar for validate, scaffold
```

### 3. Update package.json Scripts

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "typecheck": "tsc --noEmit"
  }
}
```

Remove `serve` script since we no longer run a TypeScript server.

### 4. Vite Config for Single-File Output

Ensure `vite.config.ts` produces a single `index.html`:

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { viteSingleFile } from 'vite-plugin-singlefile';

export default defineConfig({
  plugins: [react(), viteSingleFile()],
  build: {
    outDir: 'dist',
    cssCodeSplit: false,
    rollupOptions: {
      output: {
        inlineDynamicImports: true,
      },
    },
  },
});
```

## Python Package Structure

```
src/airflow_unfactor/
├── __init__.py
├── server.py          # MCP server with --ui flag
├── http_server.py     # HTTP server implementation
├── ui/
│   ├── __init__.py    # get_ui_path() helper
│   └── index.html     # Built wizard UI (single file)
├── tools/
├── converters/
└── analysis/
```

### ui/__init__.py

```python
"""Wizard UI resources."""

import importlib.resources

def get_ui_path() -> str:
    """Get path to UI directory."""
    with importlib.resources.path('airflow_unfactor.ui', 'index.html') as p:
        return str(p.parent)

def get_ui_html() -> str:
    """Get UI HTML content."""
    return importlib.resources.read_text('airflow_unfactor.ui', 'index.html')
```

## Package Data

Update `pyproject.toml`:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/airflow_unfactor"]

[tool.hatch.build.targets.wheel.force-include]
"src/airflow_unfactor/ui/index.html" = "airflow_unfactor/ui/index.html"
```

Or use MANIFEST.in:

```
include src/airflow_unfactor/ui/*.html
```

## .gitignore Updates

```gitignore
# Built UI (generated, but tracked for releases)
# Note: We track the built UI so pip installs work
# !src/airflow_unfactor/ui/index.html

# mcp-app development
mcp-app/node_modules/
mcp-app/dist/
```

## Development Workflow

### For UI Development

```bash
# Terminal 1: Run Python server with API
airflow-unfactor --ui --port 8765

# Terminal 2: Run Vite dev server (hot reload)
cd mcp-app
npm run dev
# Open http://localhost:5173 (proxies API to :8765)
```

Add proxy config to `vite.config.ts`:

```typescript
export default defineConfig({
  plugins: [react(), viteSingleFile()],
  server: {
    proxy: {
      '/api': 'http://localhost:8765',
    },
  },
  // ...
});
```

### For Full-Stack Testing

```bash
./scripts/build-ui.sh
airflow-unfactor --ui
# Open http://localhost:8765
```

## scripts/build-ui.sh

```bash
#!/bin/bash
set -e

echo "Building UI..."
cd "$(dirname "$0")/../mcp-app"

npm ci
npm run build

mkdir -p ../src/airflow_unfactor/ui
cp dist/index.html ../src/airflow_unfactor/ui/

echo "UI built and copied to src/airflow_unfactor/ui/"
```

## Testing

```python
# tests/test_ui_integration.py

def test_ui_path_exists():
    from airflow_unfactor.ui import get_ui_path
    path = get_ui_path()
    assert (path / 'index.html').exists()

def test_ui_html_loads():
    from airflow_unfactor.ui import get_ui_html
    html = get_ui_html()
    assert '<html' in html
    assert 'Migration Wizard' in html  # Or some expected content
```

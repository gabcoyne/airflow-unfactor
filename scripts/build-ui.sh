#!/bin/bash
# Build the wizard UI and copy to Python package

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MCP_APP_DIR="$PROJECT_ROOT/mcp-app"
UI_DIR="$PROJECT_ROOT/src/airflow_unfactor/ui"

echo "Building wizard UI..."
echo "  Source: $MCP_APP_DIR"
echo "  Target: $UI_DIR"

cd "$MCP_APP_DIR"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm ci
fi

# Build
echo "Running build..."
npm run build

# Copy to Python package
echo "Copying to Python package..."
mkdir -p "$UI_DIR"
cp dist/index.html "$UI_DIR/"

echo ""
echo "UI built successfully!"
echo "  Output: $UI_DIR/index.html"
echo ""
echo "To test:"
echo "  airflow-unfactor --ui"
echo "  open http://localhost:8765"

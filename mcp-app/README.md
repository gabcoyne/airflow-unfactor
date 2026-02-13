# Airflow Migration Wizard MCP App

An interactive MCP App that provides a wizard interface for migrating Airflow DAGs to Prefect flows.

## Features

- **7-Step Wizard**: Guided migration process from DAG selection to project export
- **DAG Analysis**: Automatic analysis of Airflow DAGs with complexity scoring
- **Code Conversion**: Convert DAGs to Prefect flows with educational comments
- **Validation**: Verify conversion accuracy with confidence scores
- **Project Generation**: Generate complete Prefect project structure following PrefectHQ/flows patterns
- **Export Options**: Download as ZIP or copy individual files

## Architecture

This MCP App consists of:

1. **React UI** (`src/`): Single-page wizard application using shadcn/ui components
2. **MCP Server** (`server.ts`): TypeScript server that:
   - Registers the `migration-wizard` tool
   - Serves the UI as an MCP resource
   - Proxies tool calls to the Python backend

## Development

### Prerequisites

- Node.js 18+
- npm or pnpm

### Setup

```bash
npm install
```

### Build

```bash
npm run build
```

This produces a single `dist/index.html` file with all assets inlined.

### Development Server

```bash
npm run dev
```

Starts Vite dev server at http://localhost:5173

### Start MCP Server

```bash
npm start
```

Starts the MCP server at http://localhost:3002

## Wizard Steps

1. **Select DAGs**: Choose which Airflow DAG files to migrate
2. **Analyze**: Review analysis of operators, dependencies, and complexity
3. **Configure**: Set conversion options (comments, tests, runbook)
4. **Validate**: Run conversion and validation, review results
5. **Project Setup**: Configure project name, workspace, and dependencies
6. **Deployment**: Configure work pools, schedules, and prefect.yaml
7. **Export**: Browse generated files and download as ZIP

## MCP Integration

### Tool Registration

The `migration-wizard` tool is registered with:

```typescript
server.tool(
  "migration-wizard",
  "Interactive wizard to migrate Airflow DAGs to Prefect flows...",
  { dags_directory: z.string().optional() },
  async (args) => { /* ... */ }
);
```

### Backend Communication

The MCP server proxies calls to the Python backend:

- `wizard/analyze` - Analyze a DAG file
- `wizard/convert` - Convert a DAG to Prefect flow
- `wizard/validate` - Validate conversion accuracy
- `wizard/scaffold` - Generate project structure

## Output Structure

Generated projects follow the PrefectHQ/flows structure:

```
project-name/
├── .gitignore
├── .prefectignore
├── README.md
├── pyproject.toml (optional)
└── deployments/
    └── workspace/
        ├── prefect.yaml
        └── flow-name/
            ├── flow.py
            ├── requirements.txt
            ├── test_flow.py (optional)
            └── Dockerfile (optional)
```

## Configuration

Environment variables:

- `PORT` - MCP server port (default: 3002)
- `PYTHON_SERVER_URL` - Python backend URL (default: http://localhost:3001)

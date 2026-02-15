# OpenSpec: External MCP Integration (Astronomer + Prefect)

## Overview
Integrate external MCP servers into airflow-unfactor to provide domain guidance during analysis and conversion.

Primary sources:
- Astronomer MCP: airflow 2→3 migration guidance (mcpmarket skill)
- Prefect MCP: Prefect docs knowledge base (docs.prefect.io/mcp)

## Requirements

### R1: External MCP Server Registry
Define external MCP servers in a config file that can be overridden by env vars.

Example config (mcp.external.json):
```json
{
  "prefect": {
    "url": "https://docs.prefect.io/mcp",
    "transport": "http",
    "headers": {}
  },
  "astronomer": {
    "url": "<astronomer-mcp-url>",
    "transport": "http",
    "headers": {}
  }
}
```

Env overrides:
- `MCP_PREFECT_URL`
- `MCP_ASTRONOMER_URL`
- `MCP_PREFECT_HEADERS` (JSON string)
- `MCP_ASTRONOMER_HEADERS` (JSON string)

### R2: Tool Adapters
Expose local MCP tools that proxy to external servers:

- `prefect_search(query: str)` → Prefect MCP Search
- `astronomer_migration(query: str)` → Astronomer migration tool

### R3: Integration Points
- `analyze`: optional external enrichment (migration guidance + links)
- `convert`: optional external enrichment (best practices + warnings)
- `explain`: optional external enrichment (Prefect examples)

### R4: Runtime Behavior
- External calls are **enabled by default** via `include_external_context: bool = true`
- Setting `include_external_context=false` must fully disable external MCP calls
- Timeouts and failures must **not** break core conversion
- Responses should be attached under `external_context` with provenance

### R5: Response Format
Example:
```json
{
  "flow_code": "...",
  "warnings": [],
  "external_context": {
    "prefect": {
      "ok": true,
      "tool": "SearchPrefect",
      "query": "taskflow conversion",
      "elapsed_ms": 123,
      "result": { ... }
    },
    "astronomer": {
      "ok": false,
      "tool": "Airflow2to3Migration",
      "query": "datasets -> assets",
      "elapsed_ms": 8000,
      "error": "timeout"
    }
  }
}
```

Canonical provider payload:
- `ok: bool` required
- `tool: str` required
- `query: str` required
- `elapsed_ms: int` required
- Exactly one of:
  - Success: `result: object|array|string|number|bool|null`
  - Failure: `error: str`

### R6: Security
- Do not log secrets or raw auth headers
- Fail closed on invalid JSON headers
- Graceful degradation if servers unavailable

## Implementation Locations
- `src/airflow_unfactor/external_mcp.py` (client + config)
- `src/airflow_unfactor/tools/*.py` (optional enrichment)

## Test Cases

### TC1: Prefect MCP search
Input: `prefect_search("taskflow")`
Expected: results + links from docs.prefect.io/mcp

### TC2: Astronomer migration guidance
Input: `astronomer_migration("datasets -> assets")`
Expected: migration hints

### TC3: Conversion with external context
Input: `convert(..., include_external_context=true)`
Expected: `external_context` attached

### TC4: Server unreachable
Input: external server down
Expected: conversion still returns, with warning in `external_context`

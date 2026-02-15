---
layout: page
title: External MCP Configuration
permalink: /configuration/external-mcp/
---

# External MCP Configuration

airflow-unfactor can enrich conversions with context from external MCP servers, providing additional documentation and migration guidance.

## Supported External MCPs

### Prefect Documentation MCP

Provides current Prefect documentation and best practices to help guide your conversion.

### Astronomer Migration MCP

Provides Airflow 2→3 migration guidance relevant to patterns detected in your DAGs.

## Configuration

### Environment Variables

Set the following environment variables to configure external MCP endpoints:

```bash
# Prefect MCP endpoint
export AIRFLOW_UNFACTOR_PREFECT_MCP_URL="https://mcp.prefect.io"

# Astronomer MCP endpoint
export AIRFLOW_UNFACTOR_ASTRONOMER_MCP_URL="https://mcp.astronomer.io"

# Timeout for external calls (seconds)
export AIRFLOW_UNFACTOR_EXTERNAL_TIMEOUT="10"
```

### Configuration File

Alternatively, create `mcp.external.json` in your working directory:

```json
{
  "prefect": {
    "enabled": true,
    "url": "https://mcp.prefect.io",
    "timeout_seconds": 10
  },
  "astronomer": {
    "enabled": true,
    "url": "https://mcp.astronomer.io",
    "timeout_seconds": 10
  },
  "fallback_mode": "silent"
}
```

## Fallback Behavior

When external MCPs are unavailable, conversion proceeds without enrichment. Configure fallback behavior with the `fallback_mode` setting:

- **`silent`** (default): No warning, conversion proceeds normally
- **`warn`**: Include a warning in conversion output
- **`error`**: Return an error if external MCP is unavailable

## Disabling External Context

To convert without external context enrichment:

### CLI Usage

External context is enabled by default. The `include_external_context` parameter controls this behavior when calling tools directly.

### MCP Tool Call

```json
{
  "name": "convert",
  "arguments": {
    "path": "/path/to/dag.py",
    "include_external_context": false
  }
}
```

### Wizard UI

The wizard UI does not use external context by default for faster response times. This may be configurable in future versions.

## Output Format

When external context is included, conversion results contain an `external_context` field:

```json
{
  "flow_code": "...",
  "external_context": {
    "prefect": {
      "ok": true,
      "result": "Relevant Prefect documentation..."
    },
    "astronomer": {
      "ok": true,
      "result": "Migration guidance for detected patterns..."
    }
  }
}
```

If an external MCP fails:

```json
{
  "external_context": {
    "prefect": {
      "ok": false,
      "error": "timeout"
    }
  }
}
```

## Privacy

When external MCP enrichment is enabled:

- Only query strings are sent to external servers
- Your DAG code is **not** sent externally
- Queries describe detected patterns, not actual code content

Example query: "Airflow DAG with 3 PythonOperators, TaskGroup, and XCom usage"

## Troubleshooting

### Timeout Errors

Increase the timeout:

```bash
export AIRFLOW_UNFACTOR_EXTERNAL_TIMEOUT="30"
```

### Connection Refused

Verify the MCP endpoint URLs are correct and accessible from your network.

### Certificate Errors

If using self-signed certificates for internal MCP servers, you may need to configure SSL verification (not recommended for production).

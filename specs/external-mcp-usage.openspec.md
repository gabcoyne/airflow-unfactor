# OpenSpec: External MCP Usage in airflow-unfactor

## Purpose
Define **how** external MCP servers (Astronomer + Prefect) are used throughout the toolchain to enrich analysis, conversion, and explanations.

External MCP servers (unauthenticated):
- Prefect MCP: https://docs.prefect.io/mcp
- Astronomer MCP (Airflow 2→3 migration): https://mcpmarket.com/ja/tools/skills/airflow-2-to-3-migration

## Usage Principles
1. **Non-blocking**: core conversion must succeed without external context.
2. **Best-effort**: failures return warnings in `external_context` only.
3. **Provenance**: include tool + query metadata in responses.
4. **Deterministic inputs**: build stable queries from DAG analysis.
5. **Default-on**: external enrichment is enabled unless `include_external_context=false`.

## Integration Points

### 1) analyze()
**Purpose**: Add migration guidance to structural analysis.

**External MCP calls**:
- Prefect MCP: `SearchPrefect` with query derived from operator count and patterns.
- Astronomer MCP: migration notes for datasets/assets/operator changes.

**Example query**:
```
SearchPrefect: "Analyze Airflow DAG. Operators: <n>, TaskFlow=<bool>, Datasets=<bool>"
Astronomer: "Airflow 2 to 3 migration: datasets->assets, operator changes"
```

**Response**:
```json
{
  "external_context": {
    "prefect": {
      "ok": true,
      "tool": "SearchPrefect",
      "query": "...",
      "elapsed_ms": 123,
      "result": {}
    },
    "astronomer": {
      "ok": false,
      "tool": "Airflow2to3Migration",
      "query": "...",
      "elapsed_ms": 8000,
      "error": "timeout"
    }
  }
}
```

### 2) convert()
**Purpose**: Provide migration hints and Prefect best practices alongside conversion output.

**External MCP calls**:
- Prefect MCP: TaskFlow/Datasets/Sensors best practices.
- Astronomer MCP: explicit Airflow 2→3 migration notes relevant to detected patterns.

**Example query**:
```
SearchPrefect: "Convert Airflow DAG to Prefect flow. TaskFlow=<bool>, Datasets=<bool>, Sensors=<bool>"
Astronomer: "Airflow 2 to 3 migration: dataset->asset, operator renames"
```

**Response**:
```json
{
  "flow_code": "...",
  "warnings": [],
  "external_context": { ... }
}
```

### 3) explain()
**Purpose**: Enrich concept explanations with canonical Prefect guidance.

**External MCP calls**:
- Prefect MCP: `SearchPrefect` for the concept.

**Example query**:
```
SearchPrefect: "<concept> in Prefect"
```

### 4) CLI / Batch
**Purpose**: surface external context per file (summaries only, no blocking).

## Configuration
- No auth required (headers = `{}`)
- Env overrides:
  - `MCP_PREFECT_URL`
  - `MCP_ASTRONOMER_URL`
  - `MCP_PREFECT_HEADERS` (optional JSON)
  - `MCP_ASTRONOMER_HEADERS` (optional JSON)

## Failure Handling
- Any external MCP error → `external_context.<provider>.ok=false`
- Do not fail analyze/convert/explain when MCP is unavailable
- Never log header values

## Canonical `external_context` Schema
Per provider (`prefect`, `astronomer`):
- Required: `ok`, `tool`, `query`, `elapsed_ms`
- Success payload: `result`
- Failure payload: `error`
- `result` and `error` are mutually exclusive

## Tests
- Stub external calls in unit tests
- Add integration test behind env flag (optional)

---

**Resolved defaults**:
- External context is ON by default.
- Callers can disable with `include_external_context=false`.

# Architecture

**Analysis Date:** 2026-02-26

## Pattern Overview

**Overall:** FastMCP-based LLM-assisted code generation tool for Airflow-to-Prefect migrations.

**Key Characteristics:**
- Raw source code analysis (no AST intermediary)
- Knowledge compilation from external sources (Colin) with fallback mappings
- Real-time documentation lookup via external MCP integration
- Tool-based validation and scaffolding
- LLM-centric code generation (tools provide inputs, LLM generates code)

## Layers

**MCP Server Layer:**
- Purpose: Entry point and tool registration via FastMCP
- Location: `src/airflow_unfactor/server.py`
- Contains: Tool definitions, server configuration, LLM instructions
- Depends on: Tool implementations, knowledge system
- Used by: LLM clients over MCP protocol

**Tool Layer:**
- Purpose: Provide discrete, focused operations for the LLM
- Location: `src/airflow_unfactor/tools/`
- Contains: Five tool implementations (read_dag, lookup_concept, search_prefect_docs, validate, scaffold)
- Depends on: Knowledge system, validation utilities, external MCP client
- Used by: Server layer for registration

**Knowledge Layer:**
- Purpose: Manage translation mappings (Airflow concepts to Prefect equivalents)
- Location: `src/airflow_unfactor/knowledge.py`
- Contains: Knowledge loader, lookup algorithm, fallback mappings
- Depends on: Colin-compiled JSON output (optional), in-memory fallback dictionary
- Used by: lookup_concept tool

**External Integration Layer:**
- Purpose: Communicate with Prefect MCP server for real-time documentation
- Location: `src/airflow_unfactor/external_mcp.py`
- Contains: FastMCP client wrapper, HTTP transport handling, error management
- Depends on: FastMCP Client library
- Used by: search_prefect_docs tool

**Validation Layer:**
- Purpose: Syntax checking and error reporting for generated code
- Location: `src/airflow_unfactor/validation.py`
- Contains: Python AST-based syntax validation, result data structures
- Depends on: Python stdlib ast module
- Used by: validate tool

## Data Flow

**DAG Reading Flow:**

1. LLM calls `read_dag` with path or inline content
2. Tool reads file from disk or uses provided content
3. Returns raw source code + metadata (path, size, line count)
4. LLM analyzes raw source directly

**Knowledge Lookup Flow:**

1. LLM calls `lookup_concept` with operator/pattern name (e.g., "PythonOperator")
2. Knowledge loader attempts to read Colin-compiled JSON from `colin/output/` directory
3. Lookup algorithm tries: exact match → case-insensitive → substring
4. If not found in Colin output, checks fallback built-in mappings
5. Returns translation rules, examples, and source (colin or fallback)
6. If still not found, returns suggestions for related concepts

**Documentation Search Flow:**

1. LLM calls `search_prefect_docs` for real-time Prefect documentation
2. Tool queries Prefect MCP server via FastMCP HTTP client
3. Prefect MCP runs SearchPrefect tool and returns results
4. Tool extracts text content and returns to LLM
5. On network error/timeout, returns error message with advice to run 'colin run'

**Code Generation & Validation Flow:**

1. LLM reads DAG with `read_dag` → analyzes raw source
2. LLM calls `lookup_concept` multiple times for operators/patterns found in DAG
3. LLM optionally calls `search_prefect_docs` for patterns not in lookup
4. LLM generates complete Prefect flow code
5. LLM calls `validate` with original DAG and generated flow
6. Tool returns: both sources + syntax validation + comparison guidance
7. LLM reviews validation results and refines if needed

**Project Scaffolding Flow:**

1. LLM calls `scaffold` with output directory and project name
2. Tool creates directory structure following `prefecthq/flows` conventions
3. Tool generates: pyproject.toml, README, conftest.py, prefect.yaml, Dockerfile, GitHub Actions
4. Returns report with created paths and next steps
5. LLM then generates flow code into created structure

**State Management:**

- No persistent state between tool calls (stateless design)
- Knowledge is loaded fresh each time `lookup_concept` is called
- Colin output is optional; fallback mappings always available
- Each tool call is independent and can fail gracefully

## Key Abstractions

**MCP Tool:**
- Purpose: Discrete operation exposed to LLM as a single callable
- Examples: `read_dag`, `lookup_concept`, `search_prefect_docs`, `validate`, `scaffold`
- Pattern: Async function returning JSON string, defined with `@mcp.tool` decorator

**Knowledge Entry:**
- Purpose: Represents a single Airflow→Prefect mapping
- Examples: PythonOperator, BashOperator, XCom, TaskGroup, connections
- Structure: concept_type, airflow info, prefect_equivalent, translation_rules, gotchas

**Validation Result:**
- Purpose: Structured output of syntax validation
- Examples: `ValidationResult(valid=True)` or `ValidationResult(valid=False, line=42, column=10, error="...")`
- Pattern: Dataclass with boolean status + optional error details

**Colin Knowledge Format:**
- Purpose: Pre-compiled translation knowledge from live sources
- Location: Output from `colin run` → `colin/output/*.json`
- Structure: Flat JSON objects or arrays with "entries" field, keyed by concept name
- Fallback: If Colin output missing, uses hardcoded FALLBACK_KNOWLEDGE dictionary

## Entry Points

**MCP Server:**
- Location: `src/airflow_unfactor/server.py::main()`
- Triggers: Run as `airflow-unfactor` command or via MCP client
- Responsibilities: Initialize FastMCP, register tools, run over stdio

**Tool Entrypoints:**
- `read_dag`: Read Airflow DAG source code
- `lookup_concept`: Query translation knowledge
- `search_prefect_docs`: Search Prefect documentation via external MCP
- `validate`: Validate converted flow against original DAG
- `scaffold`: Generate Prefect project directory structure

## Error Handling

**Strategy:** Explicit error returns in JSON, no exceptions thrown to caller.

**Patterns:**
- Missing files: `{"error": "File not found: ..."}`
- Network failures: `{"error": "Cannot connect to Prefect MCP at ...", "fallback_advice": "..."}`
- Timeouts: `{"error": "Prefect MCP request timed out after 15s"}`
- Concept not found: `{"status": "not_found", "suggestions": [...], "fallback_advice": "..."}`
- Syntax errors: `{"syntax_valid": false, "syntax_errors": [{"line": N, "column": M, "message": "..."}]}`

## Cross-Cutting Concerns

**Logging:** No structured logging; errors returned in JSON responses. Tool calls are side-effect free.

**Validation:** Python syntax validation via AST parsing for generated code. Structural validation is delegated to LLM.

**Authentication:** None required. External Prefect MCP server accessed without credentials (public documentation).

**External Dependencies:**
- FastMCP 2.14+ for MCP protocol and HTTP client
- Python 3.11+ for stdlib (ast, json, pathlib)
- Optional: Colin output directory for pre-compiled knowledge

---

*Architecture analysis: 2026-02-26*

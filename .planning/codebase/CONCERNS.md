# Codebase Concerns

**Analysis Date:** 2026-02-26

## Path/Content Ambiguity in Validation Tool

**Validation Tool Path Detection:**
- Issue: `validate_conversion()` in `src/airflow_unfactor/tools/validate.py` uses heuristics to distinguish between file paths and inline code: checks if input contains no newlines, is < 1024 characters, and the path exists. This is fragile.
- Files: `src/airflow_unfactor/tools/validate.py` (lines 30-37)
- Impact: If a user provides Python code < 1024 chars with no newlines that happens to match an existing filesystem path, the tool will read the file instead. Example: passing code string `"x=1"` when a file named `x=1` exists. Unlikely in practice but possible edge case.
- Fix approach: Add an explicit parameter to distinguish between path mode and content mode, or require paths to end with `.py` extension and/or contain path separators (`/` or `\`).

## Type Safety Issue: Bare `except Exception`

**Broad Exception Handling:**
- Issue: `search_prefect_mcp()` in `src/airflow_unfactor/external_mcp.py` uses bare `except Exception` (line 45), which catches all exceptions including `KeyboardInterrupt`, `SystemExit`, and unintended errors.
- Files: `src/airflow_unfactor/external_mcp.py` (lines 45-53)
- Current mitigation: Error messages provide user-facing context (connection errors, timeouts)
- Recommendations: Narrow the exception handler to catch specific exceptions (`ClientError`, `TimeoutError`, `ConnectionError`) from the FastMCP client library. Unrelated exceptions should propagate up for debugging.

## Incomplete Error Information on Invalid JSON

**Knowledge Loader Silent Skips:**
- Issue: `load_knowledge()` in `src/airflow_unfactor/knowledge.py` silently continues when JSON parsing fails or key access fails (lines 135-136). There's no logging of which files failed to parse.
- Files: `src/airflow_unfactor/knowledge.py` (line 135)
- Impact: If Colin output files become corrupted or malformed, users won't know why knowledge is missing. Silent failures make debugging difficult.
- Fix approach: Add debug logging or warnings when JSON files are skipped. Include the filename and error type.

## Type Assertion in read_dag

**Unsafe Assertion:**
- Issue: `read_dag()` uses `assert path is not None` (line 36 of `src/airflow_unfactor/tools/read_dag.py`) after an early return. While logically sound, assertions can be disabled with Python's `-O` flag in production.
- Files: `src/airflow_unfactor/tools/read_dag.py` (line 36)
- Impact: Low - early return guarantees path is not None, but assertion is brittle pattern
- Fix approach: Remove assertion and add explicit type guard or let type checker verify the logic.

## Type Ignore in External MCP

**Suppressed Type Error:**
- Issue: `search_prefect_mcp()` uses `# type: ignore[union-attr]` (line 43 of `src/airflow_unfactor/external_mcp.py`) when accessing `.text` attribute. The result type from FastMCP's `call_tool()` is not strongly typed.
- Files: `src/airflow_unfactor/external_mcp.py` (line 43)
- Impact: Future versions of FastMCP could change return types silently
- Fix approach: Add proper type annotations by importing FastMCP's result types and checking for content item types before accessing `.text`.

## Limited Search Result Ranking in Knowledge Lookup

**Suggestion Algorithm Simplicity:**
- Issue: The `suggestions()` function in `src/airflow_unfactor/knowledge.py` (lines 191-221) uses simple character-overlap scoring. It counts shared characters, not substring position or relevance.
- Files: `src/airflow_unfactor/knowledge.py` (lines 211-221)
- Impact: Suggestions may be low quality for queries with common characters (e.g., looking up "Task" might return high scores for "TaskGroup", "BashTask", "task_", etc. all equally)
- Fix approach: Use `difflib.SequenceMatcher.ratio()` or Levenshtein distance for better similarity scoring. Prioritize full word matches.

## No Environment Variable Validation

**Missing Env Var Guards:**
- Issue: `search_prefect_mcp()` reads `MCP_PREFECT_URL` but doesn't validate it as a valid URL. Invalid URLs will fail at runtime during HTTP connection.
- Files: `src/airflow_unfactor/external_mcp.py` (line 34)
- Impact: User provides malformed `MCP_PREFECT_URL`, tool fails with confusing HTTP error instead of clear validation message
- Fix approach: Use `urllib.parse.urlparse()` to validate URL format on startup or in the function, return clear error if invalid.

## Large DAG File Handling

**Unbounded File Size:**
- Issue: `read_dag()` reads entire file into memory with `file.read_text()` (line 41 of `src/airflow_unfactor/tools/read_dag.py`). No size limits or streaming.
- Files: `src/airflow_unfactor/tools/read_dag.py` (line 41)
- Impact: Very large DAG files (> 10MB) will be fully loaded into memory. MCP tools are supposed to be lightweight.
- Fix approach: Add a file size check (e.g., max 5MB) and return error with guidance if exceeded. Consider streaming for very large files.

## Incomplete Knowledge Base Coverage

**Fallback Mappings Are Minimal:**
- Issue: `FALLBACK_KNOWLEDGE` in `src/airflow_unfactor/knowledge.py` (lines 12-101) covers only 6 core operators/concepts. Many Airflow operators lack translation guidance.
- Files: `src/airflow_unfactor/knowledge.py` (lines 12-101)
- Impact: Users converting complex Airflow DAGs will frequently get "not_found" results for operators, forcing them to search Prefect docs manually or guess translations
- Fix approach: Expand fallback knowledge base with more operators (EmailOperator, KubernetesPodOperator, SparkOperator, S3Operator, etc.) or pre-compile with Colin more frequently.

## Constraint on Validation Tool Argument Sizes

**Path Limit Hit in Validate Tool:**
- Issue: The `validate()` tool has inline content that could be passed for both `original_dag` and `converted_flow` parameters. If both parameters together exceed the OS path limit (~255 chars per argument), the tool may silently fail during path detection.
- Files: `src/airflow_unfactor/tools/validate.py` (lines 32, 36)
- Context: Recent commit 204d8c3 fixed a similar issue ("Fix validate tool crash on inline content longer than OS path limit")
- Impact: Very long inline code strings (> 1024 chars) bypass the path check and work fine, but strings between 1024-OS_PATH_LIMIT could still cause issues
- Fix approach: Replace heuristic path detection with explicit parameters (`is_path=true|false`) instead of guessing based on string content.

## Missing Colin Output Graceful Degradation

**Colin Output Required for Full Functionality:**
- Issue: While `load_knowledge()` gracefully returns empty dict if Colin output is missing, the system is designed around Colin-compiled knowledge. Without it, only 6 fallback concepts are available.
- Files: `src/airflow_unfactor/knowledge.py` (line 117-118)
- Impact: Fresh installations without running `colin run` will have severely limited translation knowledge. Users may not realize they need to run Colin first.
- Fix approach: Add startup check in `server.py` that warns user if Colin output is not found, with instructions to run `colin run`. Consider pre-compiling a reasonable default knowledge base into the package.

## No Rate Limiting on External MCP Requests

**Unprotected Prefect Docs Search:**
- Issue: `search_prefect_docs` tool has no rate limiting. Users could spam the Prefect MCP server.
- Files: `src/airflow_unfactor/external_mcp.py` and `src/airflow_unfactor/tools/search_docs.py`
- Impact: If many LLM instances call this tool repeatedly, it could trigger rate limits or DoS-like behavior against Prefect docs
- Fix approach: Add simple rate limiting (e.g., max 1 request per second, exponential backoff) or cache results for identical queries.

## Regex Scoring in Knowledge Lookup

**Substring Match May Return Exact Matches Later:**
- Issue: The lookup function (lines 154-178 in `src/airflow_unfactor/knowledge.py`) iterates through fallback knowledge in order after Colin fails. If Colin has "Operator" and fallback has "PythonOperator", substring match for "Operator" might find fallback's "PythonOperator" if it comes first alphabetically.
- Files: `src/airflow_unfactor/knowledge.py` (lines 154-178)
- Impact: Users might get fallback knowledge when more detailed Colin knowledge exists
- Fix approach: Keep Colin and fallback lookups separate. Try Colin exact → case-insensitive → substring, then fallback exact → case-insensitive → substring, in that order.

---

*Concerns audit: 2026-02-26*

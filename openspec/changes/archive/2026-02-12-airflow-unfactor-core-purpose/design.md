## Context

airflow-unfactor is an MCP server that helps teams refactor Apache Airflow DAG code into Prefect flow code. The tool was built with FastMCP and provides AI-assisted conversion through Claude Desktop, Cursor, or direct CLI usage.

A comprehensive audit revealed the tool had fundamental gaps between its marketing ("liberation, not migration") and its actual capabilities. Generated code lost task dependencies, XCom patterns failed silently, Jinja2 templates caused runtime errors, and output was never validated. The P0 sprint fixed these critical issues; this design documents the architectural decisions made and establishes the foundation for ongoing development.

**Current State (Post-P0):**
- Dependency graph extraction and topological execution ordering implemented
- XCom detection handles simple patterns; complex patterns generate warnings
- Jinja2 template detection with Prefect runtime context hints
- Generated code validated with ast.parse() before returning
- 130 tests passing with comprehensive coverage

**Constraints:**
- Must remain MCP-compatible (tools exposed via FastMCP)
- Generated code must be valid Python that can be executed directly
- No runtime dependencies on airflow-unfactor after conversion
- Must support Prefect 3.x API conventions

## Goals / Non-Goals

**Goals:**
- Produce working, idiomatic Prefect code that preserves DAG execution semantics
- Clearly communicate what converts automatically vs. what requires manual review
- Provide actionable runbooks with DAG-specific migration guidance
- Maintain comprehensive specs that serve as both documentation and test contracts

**Non-Goals:**
- 100% automated conversion of all Airflow patterns (some require human judgment)
- Runtime migration tooling (this is a refactoring aid, not a migration framework)
- Supporting Airflow 1.x DAGs (focus on Airflow 2.x+ with TaskFlow API)
- Generating deployment infrastructure (work pools, workers, etc.)

## Decisions

### Decision 1: AST-based analysis over regex parsing

**Choice:** Use Python's `ast` module for all code analysis (dependency extraction, XCom detection, operator parsing).

**Rationale:** AST provides structural understanding of code that regex cannot reliably achieve. Handles multiline expressions, nested calls, and variable references correctly. Enables precise source location tracking for warnings.

**Alternatives considered:**
- Regex patterns: Faster to implement but brittle; fails on formatting variations, comments, multiline
- Tree-sitter: More powerful but adds external dependency; ast is stdlib

### Decision 2: Result objects over string returns

**Choice:** Converter functions return dataclass result objects containing `code`, `warnings`, and detection info (e.g., `BashConversionResult`, `PythonOperatorConversionResult`).

**Rationale:** Enables rich feedback to users about what was converted and what needs attention. Warnings can be aggregated and categorized. Detection info supports future enhancements.

**Alternatives considered:**
- Tuple returns: Less discoverable, harder to extend
- Dict returns: No type safety, easy to miss fields

### Decision 3: Topological sort with execution levels

**Choice:** Use Kahn's algorithm for topological sort, then group tasks by execution level for parallel execution hints.

**Rationale:** Preserves original DAG semantics while exposing parallelism opportunities. Level grouping provides clear visual structure in generated code. Comments explain which tasks can run in parallel.

**Alternatives considered:**
- Simple topological order: Loses parallelism information
- Dependency injection: Too complex for generated code readability

### Decision 4: Data passing for single upstream, wait_for for multiple

**Choice:** When task B depends only on task A, pass A's result as argument. When task C depends on A and B, use `task_c.submit(wait_for=[a_result, b_result])`.

**Rationale:** Data passing is idiomatic Prefect and enables implicit dependency tracking. wait_for handles fan-in patterns cleanly. This matches how Prefect developers would write the code manually.

**Alternatives considered:**
- Always use wait_for: Loses the data flow benefits of Prefect
- Always use data passing: Doesn't work for fan-in without awkward tuple returns

### Decision 5: Warning-first approach for complex patterns

**Choice:** When patterns cannot be safely converted (dynamic XCom, Jinja2, unknown operators), generate warnings and TODO comments rather than attempting broken conversion.

**Rationale:** Broken generated code wastes more user time than clearly-marked incomplete code. Users can make informed decisions about how to handle edge cases. Reduces false confidence in conversion quality.

**Alternatives considered:**
- Skip complex patterns entirely: Loses context about what was in the original
- Attempt best-effort conversion: Risk of subtle bugs that appear at runtime

### Decision 6: Validation before return

**Choice:** All generated code is validated with `ast.parse()` before being returned to the user.

**Rationale:** Catches syntax errors immediately rather than at user runtime. Reports error location to help debugging. Ensures every conversion produces at least syntactically valid Python.

**Alternatives considered:**
- No validation: Users discover errors themselves
- Full import validation: Too slow and requires actual Prefect installation

## Risks / Trade-offs

**[Risk] Complex XCom patterns silently produce incorrect code**
→ Mitigation: Comprehensive detection with warnings. AST-based extraction captures dynamic task_ids, custom keys, list patterns. Users explicitly told to review.

**[Risk] Generated code style doesn't match team conventions**
→ Mitigation: Generate clean, readable code as baseline. Users can run formatters (black, ruff) on output. Educational comments are optional (include_comments=False).

**[Risk] Prefect API changes break generated code**
→ Mitigation: Pin to Prefect 3.x patterns documented in official docs. Validate against current Context7 documentation. Test suite exercises generated code patterns.

**[Risk] Large DAGs produce unmanageable output**
→ Mitigation: Execution level grouping provides structure. Consider future enhancement for subflow extraction from TaskGroups.

**[Trade-off] Detailed warnings vs. clean output**
→ Choice: Prioritize user awareness over aesthetics. Warnings can be filtered; silent failures cannot be undone.

**[Trade-off] Comprehensive conversion vs. correct conversion**
→ Choice: Correct conversion of supported patterns over partial conversion of all patterns. Clear boundaries better than false completeness.

## Migration Plan

This design documents completed work (P0 sprint) and establishes patterns for future development. No migration required.

**Rollback:** Git revert to pre-P0 commits if critical issues discovered. All changes are additive to public API.

## Open Questions

1. **Should TaskGroups convert to subflows?** Current implementation warns; full subflow extraction would improve organization for complex DAGs.

2. **Dynamic task mapping support?** Airflow 2.3+ expand()/map() patterns need Prefect task.map() equivalent. Currently warns only.

3. **Provider operator coverage?** Only 15 operators mapped. Should we expand registry or document manual conversion patterns?

4. **Trigger rule conversion?** Airflow trigger rules (one_failed, all_done, etc.) have no direct Prefect equivalent. Need state handler patterns.

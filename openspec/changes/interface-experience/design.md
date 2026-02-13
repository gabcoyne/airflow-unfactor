## Context

airflow-unfactor is an MCP server that converts Airflow DAGs to Prefect flows. Current implementation handles basic operators, TaskFlow API, sensors, datasets, and provider operators. However, several Airflow patterns lack conversion support: dynamic task mapping, TaskGroups, trigger rules, Jinja2 templates, connections, and variables.

Investigation revealed Prefect has primitives to handle all these patterns:
- `.map()` for dynamic task mapping (mirrors `.expand()`)
- Subflows for TaskGroups
- `return_state=True` and `allow_failure` for trigger rules
- `runtime.flow_run.scheduled_start_time` for Jinja2 date variables
- Blocks for connections, Variables/Secrets for Airflow Variables

The codebase uses AST visitors for pattern detection (see `analysis/parser.py`, `analysis/version.py`) and code generation templates (see `converters/base.py`).

## Goals / Non-Goals

**Goals:**
- Convert all standard Airflow patterns to working Prefect code
- Generate scaffolding for patterns requiring runtime setup (Blocks, Secrets)
- Produce actionable runbooks with DAG-specific migration guidance
- Provide versioned JSON schema for tool response contracts

**Non-Goals:**
- Runtime execution of converted code (validation is static/syntactic)
- Automatic Block/Secret creation in Prefect Cloud (scaffolding only)
- Custom operator conversion without user input (prompt for guidance)
- Airflow plugin or hook conversion (out of scope)

## Decisions

### D1: Converter Module Organization
**Decision**: One converter module per capability in `src/airflow_unfactor/converters/`.

**Rationale**: Existing pattern (`sensors.py`, `datasets.py`, `taskflow.py`) works well. Each converter is independently testable. Keeps concerns separated.

**Alternatives considered**:
- Single monolithic converter: Rejected—harder to test and maintain
- Converter classes with inheritance: Rejected—over-engineered for stateless transforms

### D2: AST-Based Detection Over Regex
**Decision**: Use Python AST for pattern detection, not regex.

**Rationale**: Already established in codebase. AST handles nested structures, comments, string literals correctly. Regex would fail on multi-line patterns.

**Implementation**: Extend existing `ast.NodeVisitor` patterns. Each converter provides a visitor that collects relevant nodes.

### D3: Trigger Rule State Pattern Generation
**Decision**: Generate inline state-checking code rather than helper functions.

**Rationale**:
- Users see exactly what's happening (educational goal)
- No hidden dependencies on utility modules
- Easier to customize per-task

**Pattern**:
```python
# For trigger_rule="all_done"
state1 = upstream_task1(return_state=True)
state2 = upstream_task2(return_state=True)
downstream_task([state1, state2])  # Receives states, runs regardless
```

### D4: Jinja2 Conversion via F-String Replacement
**Decision**: Convert Jinja2 templates to f-strings with runtime context calls.

**Rationale**:
- f-strings are idiomatic Python
- `runtime.flow_run.scheduled_start_time` is the canonical Prefect equivalent
- Maintains string context (vs extracting to variables)

**Pattern**:
```python
# Airflow: "echo {{ ds }}"
# Prefect: f"echo {runtime.flow_run.scheduled_start_time.strftime('%Y-%m-%d')}"
```

### D5: Connection/Variable Scaffolding With Multiple Options
**Decision**: Generate scaffold code showing all valid Prefect patterns, with recommendations based on naming heuristics.

**Rationale**:
- Users choose appropriate pattern for their environment
- Sensitive data detection via name patterns (key, password, secret, token)
- No secrets in generated code

### D6: Custom Operator Handling via Prompt
**Decision**: Extract `execute()` method, generate TODO with original code, prompt user.

**Rationale**:
- Custom operators are user-defined—unknowable logic
- Providing the `execute()` body gives context for refactoring
- Better than silent skip or generic stub

### D7: Runbook as Structured Markdown
**Decision**: Generate `conversion_runbook_md` as structured markdown with checklists.

**Rationale**:
- Human-readable, copy-pasteable
- Checklist format for manual follow-up items
- Already established in current `convert` output

## Risks / Trade-offs

**[Risk] Jinja2 patterns we don't recognize** → Mitigation: Warn on unrecognized `{{ ... }}` patterns, include original in comment.

**[Risk] Trigger rule state patterns are verbose** → Mitigation: Educational comments explain the pattern. Verbosity is acceptable for correctness.

**[Risk] Connection type detection may be incomplete** → Mitigation: Map common hooks (Postgres, S3, BigQuery, Snowflake). Unknown hooks get generic Block scaffold with warning.

**[Risk] TaskGroup.expand() semantic mismatch** → Mitigation: Document that Prefect subflows don't have native `.expand()`. Generated wrapper task is explicit workaround.

**[Trade-off] Inline code generation vs utility functions**: Chose inline for transparency. Users can refactor to utilities if desired.

**[Trade-off] Multiple scaffold options vs single recommendation**: Chose multiple options with recommendations. Users have different deployment contexts.

## Open Questions

1. **Schema versioning strategy**: Semver? Date-based? Start with `1.0.0` and iterate.
2. **External MCP enrichment for new converters**: Should trigger rule conversion query Prefect MCP for state handling best practices? Defer to post-implementation.

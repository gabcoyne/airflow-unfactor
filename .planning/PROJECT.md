# airflow-unfactor — Completeness Audit

## What This Is

An MCP server that helps LLMs convert Apache Airflow 2.x DAGs to Prefect flows. The LLM reads raw DAG source code directly and generates complete Prefect flows using pre-compiled translation knowledge from Colin and live Prefect documentation. This milestone is a comprehensive completeness pass — research what real-world Airflow users need converted, identify gaps, and close them.

## Core Value

Every Airflow 2.x operator, pattern, and connection type a user encounters in production should have translation guidance — either via Colin-compiled knowledge, fallback mappings, or Prefect docs search.

## Requirements

### Validated

- ✓ Read raw DAG source code (file path or inline) — existing
- ✓ Look up Airflow→Prefect translation knowledge (Colin + fallback) — existing
- ✓ Search live Prefect documentation for gaps — existing
- ✓ Validate generated flow (syntax check + both sources for comparison) — existing
- ✓ Scaffold Prefect project directory structure — existing
- ✓ Graceful degradation when Colin output or Prefect MCP unavailable — existing
- ✓ 60 passing tests with async support — existing

### Active

- [ ] Comprehensive operator coverage for Airflow 2.x ecosystem
- [ ] Coverage of complex DAG patterns (dynamic DAGs, branching, sensors, callbacks)
- [ ] Coverage of connection/hook types used in production
- [ ] Validation against real-world production-style DAGs
- [ ] Gap analysis: what operators/patterns are users most likely to encounter?

### Out of Scope

- Airflow 1.x compatibility — targeting 2.x only
- TaskFlow API decorator patterns — can add later if needed
- Runtime execution of converted flows — we generate code, not run it
- UI/visual features — focus on MCP tool completeness

## Context

The codebase is mature with clean architecture: 5 MCP tools, a knowledge compilation pipeline (Colin), and external Prefect MCP integration. The fallback knowledge base covers only 6 core concepts (PythonOperator, BashOperator, BranchPythonOperator, XCom, TaskGroup, connections). Colin-compiled output covers more, but we haven't audited whether it covers the full Airflow 2.x operator landscape.

The concerns audit flagged: limited fallback knowledge, simple suggestion algorithm, silent JSON parse failures, and no startup warning when Colin output is missing.

Test fixtures come from Astronomer 2.9 but may not cover the breadth of real-world DAG patterns.

## Constraints

- **Target version**: Airflow 2.x only (2.0–2.10+)
- **Architecture**: LLM-centric — tools provide knowledge, LLM generates code. No AST intermediary.
- **Knowledge pipeline**: Colin compiles from live sources; fallback must cover the most common operators independently.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Airflow 2.x only | Vast majority of production installs; 1.x adds complexity for diminishing returns | — Pending |
| Research + real DAG validation | Confidence requires both directions: know what's expected AND test against reality | — Pending |
| Expand fallback knowledge | Users without Colin output should still get useful guidance for common operators | — Pending |

---
*Last updated: 2026-02-26 after initialization*

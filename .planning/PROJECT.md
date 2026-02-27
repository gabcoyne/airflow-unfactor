# airflow-unfactor

## What This Is

An MCP server that helps LLMs convert Apache Airflow 2.x DAGs to Prefect flows. The LLM reads raw DAG source code directly and generates complete Prefect flows using pre-compiled translation knowledge from Colin and live Prefect documentation. Five MCP tools provide the full conversion workflow: read DAG source, look up translation knowledge, search live Prefect docs, validate generated code, and scaffold project structure.

## Core Value

Every Airflow 2.x operator, pattern, and connection type a user encounters in production should have translation guidance — either via Colin-compiled knowledge, fallback mappings, or Prefect docs search.

## Requirements

### Validated

- ✓ Read raw DAG source code (file path or inline) — v1.0
- ✓ Look up Airflow→Prefect translation knowledge (Colin + fallback) — v1.0
- ✓ Search live Prefect documentation for gaps — v1.0
- ✓ Validate generated flow (syntax check + both sources for comparison) — v1.0
- ✓ Scaffold Prefect project directory structure with schedule support — v1.0
- ✓ Graceful degradation when Colin output or Prefect MCP unavailable — v1.0
- ✓ Colin models for enterprise operators: Kubernetes, Databricks, Spark, HTTP, SSH — v1.0
- ✓ Colin models for cloud/SaaS operators: Azure ADF, Azure Blob, dbt Cloud — v1.0
- ✓ Jinja macro translation: ds_add, dag_run.conf, var.value, next_ds, prev_ds, run_id — v1.0
- ✓ Concept entries for depends_on_past and deferrable operators with "no direct equivalent" guidance — v1.0
- ✓ Schedule translation: cron, interval, presets → prefect.yaml schedule config — v1.0
- ✓ Fuzzy matching via difflib for misspelled operator lookups — v1.0
- ✓ 15-entry fallback knowledge for users without Colin output — v1.0
- ✓ Startup warning when Colin output missing or empty — v1.0
- ✓ JSON parse error logging with filename and error type — v1.0
- ✓ Operator-specific validation guidance for Kubernetes, Databricks, Azure, dbt, HTTP, SSH — v1.0
- ✓ Production-style fixture DAGs for all new operator types — v1.0
- ✓ 147 passing tests — v1.0

### Active

(None yet — define with next milestone)

### Out of Scope

- Airflow 1.x compatibility — targeting 2.x only; 1.x is EOL with substantially different APIs
- TaskFlow API decorator patterns — syntactic sugar over standard operators; can add later
- Runtime execution of converted flows — we generate code, not run it; running unreviewed code risks data corruption
- AST-based structural analysis — LLMs understand intent from raw source better than AST captures structure
- UI/visual features — engineering effort better spent on knowledge completeness
- Automatic block/secret creation — requires live Prefect API credentials; blocks are environment-specific

## Context

**Current state:** v1.0 shipped. 4,782 lines of Python across `src/` and `tests/`. 147 tests passing. Colin knowledge covers 12+ operator families, Jinja macros, and advanced patterns. The server handles misspelled lookups, missing Colin output, and corrupt JSON gracefully.

**Tech stack:** Python 3.12+, MCP SDK (mcp[cli]), Colin (knowledge compilation), uv (package management).

**Known tech debt:**
- `workspace`/`flow_names` silently dropped in scaffold MCP wrapper
- `SparkSubmitOperator` missing from validate_conversion() detection
- `validate_generated_code()` orphaned in validation.py
- Phase 1 missing VERIFICATION.md

## Constraints

- **Target version**: Airflow 2.x only (2.0–2.10+)
- **Architecture**: LLM-centric — tools provide knowledge, LLM generates code. No AST intermediary.
- **Knowledge pipeline**: Colin compiles from live sources; fallback must cover the most common operators independently.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Airflow 2.x only | Vast majority of production installs; 1.x adds complexity for diminishing returns | ✓ Good — focused scope delivered faster |
| LLM reads raw source, no AST | LLMs understand intent from source better than AST captures structure | ✓ Good — simpler architecture, better results |
| Colin for knowledge compilation | Live source + LLM summarization produces higher-quality knowledge than static mappings | ✓ Good — 12+ operator families compiled successfully |
| Expand fallback knowledge to 15 | Users without Colin output need guidance for common operators | ✓ Good — covers sensors, branching, cross-DAG operators |
| difflib for fuzzy matching | Simple, stdlib, effective at cutoff=0.4 with case-insensitive wrapper | ✓ Good — handles typos and case differences |
| normalize_query at lookup() entry | All callers benefit from Jinja syntax stripping transparently | ✓ Good — `{{ macros.ds_add }}` works without caller changes |
| schedule_interval as str, not timedelta | MCP receives strings; digits represent seconds; keeps interface simple | ✓ Good — clean API surface |
| depends_on_past/deferrable: equivalent=none | Honest about paradigm gaps; workarounds documented, not false equivalences | ✓ Good — prevents incorrect conversions |
| Conditional operator guidance in validate | Appends extras only when detected; base checklist unchanged | ✓ Good — no regression for existing users |

---
*Last updated: 2026-02-27 after v1.0 milestone*

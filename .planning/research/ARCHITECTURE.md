# Architecture Research

**Domain:** Airflow-to-Prefect migration tooling (MCP server + knowledge base)
**Researched:** 2026-02-26
**Confidence:** HIGH (architecture analysis from live codebase + verified Airflow/Prefect docs)

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Knowledge Build Time (Colin)                 │
│                                                                  │
│  colin/models/                colin run                         │
│  ├── concepts.md     ──────►  colin/output/concepts.json        │
│  ├── connections.md  ──────►  colin/output/connections.json     │
│  ├── patterns.md     ──────►  colin/output/patterns.json        │
│  └── operators/              colin/output/operators-*.json      │
│      ├── core.md                                                 │
│      ├── aws.md                                                  │
│      ├── database.md                                             │
│      ├── gcp.md                                                  │
│      └── sensors.md                                              │
└───────────────────────────────┬─────────────────────────────────┘
                                │ compiled JSON (78 entries today)
┌───────────────────────────────▼─────────────────────────────────┐
│                      Runtime MCP Server                          │
│                                                                  │
│  knowledge.py                                                    │
│  ├── load_knowledge()    ← colin/output/*.json (primary)        │
│  ├── FALLBACK_KNOWLEDGE  ← 6-entry hardcoded dict (secondary)   │
│  └── lookup()            ← exact → case-insensitive → substring │
│                                                                  │
│  tools/                                                          │
│  ├── read_dag.py         → raw source + metadata for LLM        │
│  ├── lookup.py           → translation rules from knowledge      │
│  ├── search_docs.py      → live Prefect MCP at docs.prefect.io  │
│  ├── validate.py         → both sources + AST syntax check      │
│  └── scaffold.py         → prefecthq/flows directory structure   │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Current State |
|-----------|----------------|---------------|
| Colin models | Source-of-truth authoring for translation knowledge | 8 files covering 78 concepts; no kubernetes/docker/dbt operators |
| Colin output JSON | Compiled, LLM-queryable knowledge | 8 JSON files, loaded fresh per `lookup_concept` call |
| FALLBACK_KNOWLEDGE | Offline fallback when Colin output absent | 6 entries only (DAG, PythonOperator, BashOperator, XCom, TaskGroup, postgres_default) |
| knowledge.py | Load and lookup logic | Stateless, loads full JSON each call; no caching |
| validate tool | Syntax check + both sources for LLM review | AST syntax only; structural comparison delegated to LLM |
| search_docs tool | Gap-filling via live Prefect documentation | Works; depends on network + Prefect MCP availability |

## Recommended Project Structure

The existing structure is sound. The gap is breadth of Colin model coverage, not the architecture itself.

```
colin/
├── models/
│   ├── concepts.md           # Core Airflow→Prefect concept mappings (12 entries)
│   ├── connections.md        # Connection→Block mappings (17 entries)
│   ├── patterns.md           # Structural pattern translations (10 entries)
│   ├── prefect-context.md    # Prefect runtime context reference
│   └── operators/
│       ├── core.md           # PythonOperator, BashOperator, etc. (10 entries)
│       ├── aws.md            # S3, Lambda, ECS, Glue, etc. (11 entries)
│       ├── database.md       # Postgres, MySQL, Snowflake, etc. (6 entries)
│       ├── gcp.md            # BigQuery, GCS, Dataproc, etc. (6 entries)
│       └── sensors.md        # File, S3, HTTP, SQL sensors (6 entries)
│
│   # GAPS — new files needed:
│       ├── kubernetes.md     # KubernetesPodOperator (most-used in enterprise)
│       ├── docker.md         # DockerOperator
│       ├── databricks.md     # DatabricksSubmitRunOperator, DatabricksRunNowOperator
│       ├── azure.md          # AzureDataFactoryRunPipelineOperator, WasbOperator, etc.
│       ├── dbt.md            # DbtCloudRunJobOperator, DbtCloudGetJobRunArtifactOperator
│       ├── http.md           # SimpleHttpOperator (extremely common)
│       └── transfer.md       # S3ToRedshiftOperator, GCSToGCSOperator patterns
│
└── output/                   # Compiled from `colin run` — 8 JSON files today
```

### Structure Rationale

The provider-as-file grouping in `colin/models/operators/` is correct: it mirrors Airflow's own provider package organization (`apache-airflow-providers-cncf-kubernetes`, `apache-airflow-providers-docker`, etc.) and makes it easy for engineers to see what's covered at a glance. Each new operator provider warrants its own `.md` file.

Connections and patterns should remain single files — they are cross-cutting and don't map cleanly to one provider.

## Architectural Patterns

### Pattern 1: Provider-Scoped Knowledge Files

**What:** One Colin model file per Airflow provider package. Each file covers the 3-8 most important operators in that provider.

**When to use:** Whenever adding operators from a new `apache-airflow-providers-*` package.

**Trade-offs:** A flat operator file (all providers in one file) would be simpler to load but harder to maintain and audit for gaps. Provider-scoped files match the Airflow ecosystem's own organization.

**Example:**
```
# colin/models/operators/kubernetes.md
{% section KubernetesPodOperator %}
## operator
KubernetesPodOperator

## module
airflow.providers.cncf.kubernetes.operators.pod

## prefect_pattern
KubernetesJob block or flow.deploy() with Kubernetes work pool

## prefect_package
prefect-kubernetes

## translation_rules
- Replace KubernetesPodOperator with prefect-kubernetes KubernetesJob block
- image → KubernetesJob image parameter
- cmds/arguments → KubernetesJob command
- env_vars → environment in KubernetesJob spec
- namespace → namespace in KubernetesJob spec
- For simple container execution: consider DockerContainer block instead
{% endsection %}
```

### Pattern 2: Tiered Knowledge Lookup

**What:** The existing three-tier lookup (Colin → FALLBACK_KNOWLEDGE → not_found+suggestions) is correct architecture. The gap is coverage, not the tier structure.

**When to use:** Always. The tier structure handles graceful degradation.

**Trade-offs:** Current `FALLBACK_KNOWLEDGE` has only 6 entries, meaning users without Colin output get very limited guidance. The fallback tier should cover the top ~20 operators that production users encounter most often (PythonOperator, BashOperator, KubernetesPodOperator, SimpleHttpOperator, BranchPythonOperator, ShortCircuitOperator, and the core connection types).

**Expansion approach:** Rather than expanding `FALLBACK_KNOWLEDGE` to match Colin (which would create maintenance duplication), the fallback should be expanded only to cover the highest-frequency operators. Colin output remains the primary — fallback is for cold-start only.

### Pattern 3: Structural Validation Delegated to LLM

**What:** The `validate` tool performs AST syntax checking mechanically, then delegates all structural correctness (task count, dependency graph, XCom replacement) to LLM comparison of both source texts.

**When to use:** This is the correct design given the LLM-centric architecture. An AST-based structural comparator would be brittle across DAG styles.

**Trade-offs:** The current `comparison_guidance` in `validate.py` is the LLM's checklist. Expanding this checklist to cover additional operator types (e.g., "Kubernetes pods are mapped to KubernetesJob blocks, not inlined subprocess calls") improves validation quality without changing the architecture.

**Example expansion for the guidance string:**
```python
"comparison_guidance": (
    "Compare the original Airflow DAG with the generated Prefect flow. Verify:\n"
    "1. All tasks from the DAG are represented in the flow\n"
    "2. Task dependencies are preserved (>> chains become function call order)\n"
    "3. XCom push/pull is replaced with task return values and parameters\n"
    "4. Connections are mapped to Prefect blocks\n"
    "5. Variables are mapped to Prefect variables or environment config\n"
    "6. Schedule, retries, and other DAG config is carried over\n"
    "7. Sensors are converted to polling tasks with retries or event triggers\n"
    "8. TaskGroups are converted to subflows\n"
    "9. Trigger rules are handled with state inspection\n"
    "10. KubernetesPodOperator becomes KubernetesJob block (not subprocess)\n"
    "11. Dynamic task mapping (.expand()) becomes .map()\n"
    "12. DatabricksSubmitRunOperator uses prefect-databricks, not raw HTTP\n"
    "13. Callbacks become state change hooks on @flow/@task decorators\n"
    "14. Pools become tag-based concurrency limits\n"
    "15. Dataset scheduling becomes emit_event() + automations"
),
```

## Data Flow

### Knowledge Build Flow

```
Colin model (*.md with {% section %} blocks)
    ↓ colin run
Colin output (*.json, one file per model)
    ↓ load_knowledge()
In-memory dict keyed by concept name
    ↓ lookup(concept, knowledge)
Matched entry or not_found + suggestions
    ↓ JSON response
LLM uses translation rules to generate Prefect flow
```

### Coverage Gap Analysis Flow

The missing providers that production users will hit most often, ranked by frequency:

1. **KubernetesPodOperator** (cncf-kubernetes provider) — 64.4% of enterprise users use Kubernetes operators per 2025 State of Airflow. No coverage today.
2. **SimpleHttpOperator** (http provider) — ubiquitous for API calls. No coverage today.
3. **DockerOperator** (docker provider) — common in containerized data pipelines. No coverage today.
4. **DatabricksSubmitRunOperator / DatabricksRunNowOperator** (databricks provider) — Databricks is the most common Spark platform. Databricks block exists in connections.json but no operator entries.
5. **DbtCloudRunJobOperator** (dbt-cloud provider) — dbt is now a core part of most data stacks. dbt block in connections.json, no operator.
6. **AzureDataFactoryRunPipelineOperator** (microsoft-azure provider) — Azure customers are a large segment. Azure credentials block exists, no operators.
7. **SparkSubmitOperator / SparkJDBCOperator** (apache-spark provider) — common in data engineering. No coverage.
8. **EmailOperator** — exists in core.md already.
9. **PapermillOperator** (papermill provider) — notebook-heavy teams use this. No coverage.
10. **SFTPOperator / SSHOperator** (sftp/ssh providers) — legacy integration pattern, still common.

### Validation Data Flow

```
LLM generates Prefect flow code
    ↓ validate(original_dag=dag_content, converted_flow=flow_code)
validate.py:
    ├── AST syntax parse (mechanical — catches SyntaxError)
    └── Returns: original_source + converted_source + syntax_valid + comparison_guidance
LLM reads both sources + guidance checklist
    ↓
LLM verifies structural correctness (task count, dependency graph, operator mappings)
    ↓
LLM iterates if issues found
```

## Operator Coverage Build Order

Build operators in this order, prioritizing by production frequency and the risk of the LLM generating incorrect code without guidance:

**Phase 1 — High frequency, high risk of wrong translation:**
1. `operators/kubernetes.md` — KubernetesPodOperator → KubernetesJob block. Without guidance, LLMs often use subprocess or Docker instead.
2. `operators/http.md` — SimpleHttpOperator → httpx/requests task. Simple but extremely common.
3. `operators/docker.md` — DockerOperator → DockerContainer block or KubernetesJob. Guidance prevents inlining docker SDK calls incorrectly.

**Phase 2 — High frequency cloud providers:**
4. `operators/databricks.md` — DatabricksSubmitRunOperator, DatabricksRunNowOperator → prefect-databricks blocks.
5. `operators/azure.md` — AzureDataFactoryRunPipelineOperator, WasbHook pattern → prefect-azure blocks.
6. `operators/dbt.md` — DbtCloudRunJobOperator → DbtCloudCredentials + DbtCoreOperation.

**Phase 3 — Long tail operators:**
7. `operators/spark.md` — SparkSubmitOperator → DatabricksCredentials or custom task.
8. `operators/sftp.md` — SFTPOperator, SSHOperator → paramiko/fabric tasks + Secret blocks.
9. `operators/papermill.md` — PapermillOperator → papermill Python call in a @task.
10. `operators/transfer.md` — Transfer operators (S3ToRedshift, GCSToGCS already in gcp.md, etc.) → explicit read + write tasks.

**Phase 4 — FALLBACK_KNOWLEDGE expansion:**
11. Add top-10 operators to `FALLBACK_KNOWLEDGE` in `knowledge.py` so users without Colin output still get core guidance. Include: KubernetesPodOperator, SimpleHttpOperator, DockerOperator, DatabricksSubmitRunOperator, BranchPythonOperator (currently missing from fallback), ShortCircuitOperator, ExternalTaskSensor.

## Validation Strategy

The current validation is syntactic only (AST parse). The architecture is correct — structural validation belongs to the LLM, not the tool. The validation tool's role is to:

1. **Mechanically verify:** Python syntax, file readability, encoding.
2. **Provide comparison substrate:** Return both source texts so the LLM has everything it needs.
3. **Guide LLM comparison:** The `comparison_guidance` checklist is the mechanism for directing LLM review.

As coverage expands, the `comparison_guidance` checklist in `validate.py` should grow in parallel. Each new operator type that gets Colin knowledge should add a corresponding checklist item — this ensures the LLM checks the specific translation when reviewing output.

**What validation does NOT need:**
- AST-based task graph comparison (brittle, complex, duplicates LLM capability)
- Import presence checking (the LLM handles this)
- Runtime execution of the generated flow (out of scope)

**What validation SHOULD gain over time:**
- A check that `prefect` is imported in the generated flow (trivial, prevents a common LLM omission)
- A check that no `airflow` imports remain in the generated flow (catches incomplete conversion)
- Expansion of `comparison_guidance` per-operator-type items as each operator file is added to Colin

## Anti-Patterns

### Anti-Pattern 1: Growing FALLBACK_KNOWLEDGE to Match Colin

**What people do:** Duplicate all Colin entries into `FALLBACK_KNOWLEDGE` to ensure offline coverage.

**Why it's wrong:** Creates a maintenance split — changes must be made in both Colin models and `FALLBACK_KNOWLEDGE`. The authoritative source of truth is the Colin model files; JSON output is derived.

**Do this instead:** Keep `FALLBACK_KNOWLEDGE` to ~15-20 highest-frequency operators. Direct users to run `colin run` for full coverage. Use `search_prefect_docs` as the true fallback for gaps.

### Anti-Pattern 2: One Giant Colin Model File

**What people do:** Add all new operators to `operators/core.md` for simplicity.

**Why it's wrong:** Makes gap auditing impossible. You can't tell "do we cover the Azure provider?" without grepping through the file.

**Do this instead:** One file per provider package. The file name mirrors the provider: `kubernetes.md` for `apache-airflow-providers-cncf-kubernetes`.

### Anti-Pattern 3: AST-Based Structural Validation

**What people do:** Write code to parse both DAG and flow ASTs, compare task node counts, verify import presence.

**Why it's wrong:** Airflow DAGs have many forms (context manager, `@dag` decorator, dynamic task creation). Writing a robust comparator is a significant engineering effort with high ongoing maintenance. The LLM does this better with the raw text.

**Do this instead:** Trust the LLM for structural comparison. Improve the `comparison_guidance` checklist when gaps are discovered.

### Anti-Pattern 4: Caching Knowledge in Memory Across Calls

**What people do:** Load `colin/output/` once at server startup and cache.

**Why it's wrong:** If `colin run` rebuilds output during a session, the server won't see the update without restart. Also, colin output files may not exist at startup time.

**Do this instead:** The current design (load on each `lookup_concept` call) is correct. The files are small (~78 JSON entries) and filesystem reads are fast. If performance becomes an issue later, invalidation-based caching (watch file mtime) is the right fix.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Prefect MCP (`docs.prefect.io/mcp`) | FastMCP HTTP client in `external_mcp.py` | Fallback when down: returns error + advises `colin run`. Timeout: 15s. |
| Colin build pipeline | `colin run` in `colin/` directory; outputs JSON to `colin/output/` | Must be run separately; MCP server reads output passively |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| server.py ↔ tools/ | Direct async function calls | Tools are registered with `@mcp.tool` in server.py |
| tools/lookup.py ↔ knowledge.py | `load_knowledge()` + `lookup()` function calls | Stateless; knowledge loaded per call |
| tools/validate.py ↔ validation.py | `validate_python_syntax()` function call | Pure function; no I/O |
| tools/search_docs.py ↔ external_mcp.py | `search_prefect_docs()` async function | Network I/O; may fail; errors returned in JSON |

## Sources

- Airflow provider package list: [https://airflow.apache.org/docs/apache-airflow-providers/packages-ref.html](https://airflow.apache.org/docs/apache-airflow-providers/packages-ref.html) — HIGH confidence (official docs)
- Prefect migration guide: [https://docs.prefect.io/v3/how-to-guides/migrate/airflow](https://docs.prefect.io/v3/how-to-guides/migrate/airflow) — HIGH confidence (official docs)
- State of Airflow 2025 (operator usage statistics): [https://www.astronomer.io/airflow/state-of-airflow/](https://www.astronomer.io/airflow/state-of-airflow/) — MEDIUM confidence (survey data, not directly verified from report)
- Live codebase analysis: `src/airflow_unfactor/`, `colin/models/`, `colin/output/` — HIGH confidence (direct inspection)

---
*Architecture research for: Airflow-to-Prefect migration tooling (airflow-unfactor)*
*Researched: 2026-02-26*

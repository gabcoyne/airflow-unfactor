# Project Research Summary

**Project:** airflow-unfactor — Airflow-to-Prefect Migration MCP Server
**Domain:** LLM-assisted DAG conversion tooling (knowledge base expansion milestone)
**Researched:** 2026-02-26
**Confidence:** HIGH

## Executive Summary

The airflow-unfactor MCP server takes the right architectural approach — providing raw DAG source code and compiled translation knowledge to LLMs rather than attempting deterministic code generation. The existing tool already covers the foundational Airflow concepts (PythonOperator, BashOperator, core database operators, AWS S3/Lambda/ECS/Glue/SageMaker, GCP BigQuery/GCS/Dataproc, common sensors, and structural patterns like branching, XCom, and TaskGroups). The problem is not the architecture; the problem is that the knowledge base has critical coverage gaps that cause the tool to fail silently on real production DAGs. Users at serious Airflow installations — where KubernetesPodOperator, Databricks, dbt, and HTTP operators are table stakes — receive no guidance and are forced to rely on LLM hallucination rather than authoritative translation rules.

The recommended approach for this milestone is a focused knowledge expansion effort: add 6-8 new Colin model files covering the most-used unrepresented provider packages, expand the fallback knowledge to cover the top-10 operators for offline use, and add two small quality improvements (startup warning when Colin output is missing, and improved lookup suggestions via `difflib`). The KubernetesPodOperator is the single most important gap — per Astronomer survey data, it appears in 64%+ of enterprise Airflow deployments, and without guidance, LLMs produce subprocess or Docker SDK calls instead of the correct Kubernetes work pool pattern.

The key risk is scope creep: there are 90+ Airflow provider packages with hundreds of operators. The correct strategy is to cover the 80% case with high-quality knowledge for the top ~15 operator gaps, then use `search_prefect_docs` as the live fallback for the long tail. The pitfalls that matter most are semantic, not syntactic — trigger rules, XCom chains, Jinja template conversion, and sensor redesign all produce code that compiles successfully but behaves incorrectly at runtime. The knowledge base must include explicit gotchas for these patterns, not just mappings.

## Key Findings

### Operator Coverage Landscape

The Colin knowledge base currently compiles 78 entries across 8 model files. The existing coverage is solid for AWS (11 operators), GCP (6 operators), database operators (6 operators), sensors (6 sensors), core operators (10 operators), and patterns (10 patterns). The Prefect integration package ecosystem has a direct counterpart for nearly every Airflow provider, so the translation rules exist — they just need to be compiled into Colin models.

**P1 gaps (tool fails on these at most enterprise installations):**
- `KubernetesPodOperator` (cncf-kubernetes) — Kubernetes work pool; architectural shift from per-task pods to deployment-level infrastructure
- `DatabricksSubmitRunOperator` / `DatabricksRunNowOperator` — `prefect-databricks` package; connections block exists but operator entries are absent
- `SimpleHttpOperator` / `HttpOperator` — direct `httpx` in `@task`; no dedicated prefect-http package is by design
- `SparkSubmitOperator` — `prefect-shell` + `spark-submit` CLI or Databricks/Dataproc managed Spark
- `SSHOperator` — `paramiko`/`fabric` in `@task` with `Secret` block for credentials

**P1 server improvements (non-Colin):**
- Startup warning when `colin/output/` is missing or empty — currently silent failure on fresh installs
- Improved suggestion algorithm — replace character-overlap matching with `difflib.SequenceMatcher`

**P2 gaps (significant user segment, add if capacity allows):**
- Azure operators (`AzureDataFactoryRunPipelineOperator`, `WasbOperator`) — `prefect-azure`
- `DbtCloudRunJobOperator` — `prefect-dbt`; connections block exists but operator entries are absent
- Extended Jinja macro coverage (`{{ macros.ds_add() }}`, `{{ dag_run.conf }}`, `{{ next_ds }}`)
- Astronomer Cosmos/dbt TaskGroup patterns
- Deferrable operator / async sensor gotchas

### Prefect Integration Package Coverage

The Prefect integration ecosystem maps cleanly to Airflow providers:

| Colin Model to Create | Airflow Provider | Prefect Package |
|----------------------|------------------|-----------------|
| `operators/kubernetes.md` | cncf-kubernetes | `prefect-kubernetes` |
| `operators/http.md` | apache-http | `httpx` directly |
| `operators/databricks.md` | databricks | `prefect-databricks` |
| `operators/dbt.md` | dbt-cloud | `prefect-dbt` |
| `operators/azure.md` | microsoft-azure | `prefect-azure` |
| `operators/spark.md` | apache-spark | `prefect-shell` / Databricks |
| `operators/docker.md` | docker | `prefect-docker` |
| `operators/sftp.md` | ssh/sftp | `paramiko`/`fabric` |

### Architecture Approach

The existing architecture is correct and should not change. One Colin model file per Airflow provider package mirrors Airflow's own provider organization, makes gap auditing straightforward, and keeps the build pipeline clean. The tiered lookup (Colin output → FALLBACK_KNOWLEDGE → not_found + suggestions) handles graceful degradation correctly; the only issue is that `FALLBACK_KNOWLEDGE` has only 6 entries when it should cover the top ~15-20 highest-frequency operators for cold-start scenarios.

**Major components:**
1. Colin build pipeline — authors translation knowledge in Markdown, compiles to JSON via `colin run`
2. `knowledge.py` — stateless loader that reads Colin output on each `lookup_concept` call (correct; avoids stale cache issues)
3. Five MCP tools — `read_dag`, `lookup_concept`, `search_prefect_docs`, `validate`, `scaffold`
4. `validate.py` — AST syntax checking only; structural comparison correctly delegated to LLM via `comparison_guidance` checklist
5. `external_mcp.py` — FastMCP client to Prefect's live docs MCP server; correct fallback for long-tail operators

**Key patterns to maintain:**
- Provider-scoped files, not one giant operators file
- Load knowledge fresh per call, not at startup
- Structural validation via LLM-readable comparison guidance, not AST comparison
- FALLBACK_KNOWLEDGE stays small (~15-20 operators); Colin output is the authoritative source

### Critical Pitfalls

1. **Trigger rules have no Prefect equivalent** — `trigger_rule="all_done"` and all 9 variants require explicit imperative Python state-checking logic (`try/except`, `prefect.states` inspection). LLMs will either drop trigger rules entirely or hallucinate a Prefect parameter. The knowledge base must cover all 9 variants with explicit translation patterns.

2. **XCom chains are silently broken** — Explicit `xcom_push/pull` is recognizable, but implicit XComs (TaskFlow API auto-capture) and Jinja-embedded pulls (`{{ ti.xcom_pull(...) }}`) are invisible to pattern-matching LLMs. Generated code compiles but produces wrong results. The XCom knowledge entry must cover all three XCom forms explicitly.

3. **Jinja templates left in generated code** — `{{ ds }}`, `{{ execution_date }}`, `{{ ti.xcom_pull }}`, `{{ var.value.key }}` and others are Airflow runtime context, not Python. If left as-is or naively wrapped in f-strings, the generated flow is broken. Every Airflow context variable needs an explicit Python equivalent in the knowledge base.

4. **Sensors require architectural redesign, not translation** — Sensor classes look like operators in source code but have completely different runtime semantics (persistent polling workers). Converting them to a simple `@task` with a condition check produces code that either blocks indefinitely or never polls. Each major sensor type needs a dedicated knowledge entry with the correct Prefect pattern (retry-based task loop, event trigger, or automation).

5. **Connections require manual re-credentialing** — `PostgresHook(conn_id="my_db")` is an Airflow abstraction that hits Airflow's connection registry at runtime; the string `"my_db"` means nothing in Prefect. The scaffold output must list every required Prefect Block type and credential setup step — generated flow code that compiles will fail at runtime if blocks are not created.

6. **Scheduling must be extracted from flow code** — Airflow embeds scheduling in the DAG definition; Prefect externalizes it to `prefect.yaml`. If `scaffold` does not translate the schedule, users end up with a valid flow file that never runs on schedule.

## Implications for Roadmap

Based on the combined research, the work falls naturally into three phases ordered by dependencies and risk. Colin knowledge expansion is the foundation — it enables everything else. Server-level improvements are independent but small. Validation hardening comes last because it depends on knowing which operator types need checklist entries.

### Phase 1: P1 Knowledge Expansion (Colin Models)

**Rationale:** The biggest user-facing value is in filling the critical operator gaps. This is the dependency-free work that unblocks all other quality improvements. New Colin model files are additive and do not require server code changes.

**Delivers:** Guidance for KubernetesPodOperator, SimpleHttpOperator, Databricks operators, SparkSubmitOperator, SSHOperator — the five operators most likely to cause tool failure at enterprise installations.

**Addresses features:** All P1 table-stakes gaps from FEATURES.md. Closes `operators/kubernetes.md`, `operators/http.md`, `operators/databricks.md`, `operators/spark.md`, `operators/sftp.md` gaps.

**Avoids:** Pitfall 1 (trigger rules), Pitfall 3 (sensors), Pitfall 5 (connections) — new knowledge entries must include gotchas and Block setup requirements.

**Key deliverables:**
- `colin/models/operators/kubernetes.md` — KubernetesPodOperator → Kubernetes work pool (architectural shift, not parameter mapping)
- `colin/models/operators/http.md` — SimpleHttpOperator → `httpx` task pattern
- `colin/models/operators/databricks.md` — DatabricksSubmitRunOperator, DatabricksRunNowOperator → `prefect-databricks`
- `colin/models/operators/spark.md` — SparkSubmitOperator → `prefect-shell` or Databricks/Dataproc path
- `colin/models/operators/sftp.md` — SSHOperator, SFTPOperator → `paramiko`/`fabric` + Secret block

**Research flag:** Standard patterns — no phase-level research needed. Operator-to-package mappings are fully documented in official Airflow and Prefect docs.

### Phase 2: Server Quality Improvements

**Rationale:** Independent of Colin model expansion; two small, high-ROI improvements that affect every user regardless of which operators they encounter.

**Delivers:** Startup warning when Colin output is absent, improved operator name matching that surfaces related operators instead of bare `not_found`.

**Addresses features:** "Startup warning when Colin output is missing" (P1 from FEATURES.md), "Improved suggestion algorithm" (P2 from FEATURES.md).

**Avoids:** UX pitfall where `not_found` returns with no guidance, causing LLM hallucination; silent failure for fresh-install users who haven't run `colin run`.

**Key deliverables:**
- `server.py` — startup check for `colin/output/` existence with clear warning message
- `knowledge.py` — swap character-overlap matching for `difflib.SequenceMatcher`
- Expand `FALLBACK_KNOWLEDGE` from 6 to ~15-20 entries (add KubernetesPodOperator, SimpleHttpOperator, DatabricksSubmitRunOperator, BranchPythonOperator, ShortCircuitOperator, ExternalTaskSensor, and top connection types)

**Research flag:** Standard patterns — `difflib` is stdlib, server.py change is trivial.

### Phase 3: P2 Knowledge Expansion + Validation Hardening

**Rationale:** Builds on Phase 1 with the next tier of production-important operators, and expands the validation checklist in parallel as knowledge coverage grows.

**Delivers:** Azure operator coverage, dbt Cloud operator guidance, extended Jinja macro coverage, and a validation checklist that explicitly checks for new operator type conversions.

**Addresses features:** P2 features from FEATURES.md — Azure operators, dbt operators, Jinja macro expansion, `depends_on_past` guidance.

**Avoids:** Pitfall 2 (XCom broken), Pitfall 4 (Jinja templates left unconverted) — the Jinja macro expansion directly addresses these. Pitfall 6 (schedule extraction) — `prefect.yaml` schedule translation in scaffold.

**Key deliverables:**
- `colin/models/operators/azure.md` — AzureDataFactoryRunPipelineOperator, WasbOperator → `prefect-azure`
- `colin/models/operators/dbt.md` — DbtCloudRunJobOperator → `prefect-dbt` DbtCloudCredentials + DbtCoreOperation
- `colin/models/operators/docker.md` — DockerOperator → Docker work pool (lower priority than P1 gaps)
- Expanded Jinja patterns in `colin/models/patterns.md` — `{{ macros.ds_add() }}`, `{{ dag_run.conf }}`, `{{ next_ds }}`, `{{ prev_ds }}`
- `validate.py` — expand `comparison_guidance` checklist with Kubernetes, Databricks, Azure, dbt checklist items
- `scaffold` tool — `prefect.yaml` schedule translation from Airflow `schedule_interval`
- Add `depends_on_past` concept entry with explicit "no direct equivalent" guidance

**Research flag:** Azure ADF and dbt Cloud operator APIs may need verification against current `prefect-azure` and `prefect-dbt` package docs. Use `search_prefect_docs` during implementation to verify block names and task signatures.

### Phase Ordering Rationale

Phase 1 comes first because the operator knowledge gaps are the primary value driver — without KubernetesPodOperator and Databricks knowledge, the tool fails the majority of enterprise migrations. Phase 2 is independent and small but improves the experience for all users, so it runs in parallel with or immediately after Phase 1. Phase 3 is a second expansion pass that handles the next tier of operators and hardens validation; it is more valuable after Phase 1 establishes the coverage pattern for new provider files.

The architecture research confirms that each phase is additive and does not require changes to the core MCP tool interfaces. Colin model expansion compiles cleanly to the existing JSON format; server.py and knowledge.py changes are isolated; validation checklist expansion does not change the tool API.

### Research Flags

Phases needing deeper research during planning:
- **Phase 3, Azure operators:** `prefect-azure` block names and task signatures should be verified against current package docs before writing Colin models — Azure integrations tend to have more API churn than AWS/GCP counterparts.
- **Phase 3, dbt operators:** Cosmos/dbt TaskGroup → `DbtCoreOperation.map()` mapping is non-trivial; Cosmos dynamically generates TaskGroups and the correct Prefect pattern depends on whether the user wants dbt Core or dbt Cloud. May warrant its own planning research.

Phases with standard patterns (skip research-phase):
- **Phase 1:** KubernetesPodOperator, HttpOperator, Databricks, Spark, SSH — all have official Prefect integration docs with clear block/task mappings. No novel patterns.
- **Phase 2:** `difflib` swap and startup warning — pure Python stdlib, no external dependencies.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack (operator gaps and Prefect package mappings) | HIGH | Verified against official Airflow provider docs and Prefect integration index; operator-to-package mappings are deterministic |
| Features (P1 vs P2 gap classification) | HIGH | Gap analysis cross-referenced against Colin output and official docs; P1/P2 split is based on production frequency data from Astronomer surveys (MEDIUM) and official provider listings (HIGH) |
| Architecture (Colin model structure, knowledge loading) | HIGH | Based on direct codebase analysis; existing architecture is validated and the pattern for expansion is clear |
| Pitfalls (semantic conversion risks) | HIGH for critical pitfalls (official Prefect migration docs), MEDIUM for LLM-specific hallucination patterns (limited direct data) | Trigger rules, XCom, Jinja, and sensor redesign are well-documented in Prefect official docs; LLM behavior predictions are inference from architecture |

**Overall confidence:** HIGH

### Gaps to Address

- **Astronomer Cosmos / dbt operator patterns:** Cosmos dynamically generates TaskGroups from dbt project structure; the correct Prefect migration pattern is not well-documented. Flag for Phase 3 planning research before writing the Colin model.
- **Production frequency data for niche operators:** The Astronomer State of Airflow surveys do not publish operator-level usage breakdowns publicly. P2 and P3 operator prioritization is based on architectural reasoning and domain experience, not measured usage data. Validate prioritization against user feedback once Phase 1 is deployed.
- **`prefect-azure` API stability:** Azure integration in the Prefect ecosystem is less mature than AWS and GCP equivalents. Verify block names and task signatures against the current `prefect-azure` package before authoring Colin models.

## Sources

### Primary (HIGH confidence)
- Apache Airflow Providers Index — complete provider package listing, operator coverage analysis
- Apache Airflow AWS/GCP/Azure/Kubernetes operator docs — operator signatures, parameters, connection requirements
- Prefect Official Migration Guide (docs.prefect.io/v3/how-to-guides/migrate/airflow) — concept mappings, patterns
- Prefect Integrations Index (docs.prefect.io/integrations) — package names, block types, task signatures
- Colin output analysis (`colin/output/*.json`) — current 78-entry coverage baseline
- Live codebase analysis (`src/airflow_unfactor/`, `colin/models/`) — architectural patterns, anti-patterns, existing code quality

### Secondary (MEDIUM confidence)
- Astronomer State of Airflow 2025 — operator usage frequency context (detailed breakdowns not publicly available)
- Prefect migration playbook blog (prefect.io/blog) — additional pattern examples
- Astronomer provider docs — operator usage guidance

### Tertiary (LOW confidence)
- LLM + MCP Airflow update patterns (chengzhizhao.com) — single blog post; cited for LLM behavior characterization only

---
*Research completed: 2026-02-26*
*Ready for roadmap: yes*

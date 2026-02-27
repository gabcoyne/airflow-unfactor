# Phase 3: P2 Knowledge Expansion - Context

**Gathered:** 2026-02-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Expand translation knowledge to cover Azure operators, dbt Cloud operator, Jinja macros, depends_on_past, and deferrable operator concepts. Make the scaffold tool schedule-aware. Users migrating these DAG types get authoritative, intent-first translation guidance.

</domain>

<decisions>
## Implementation Decisions

### Intent-First Approach (applies to ALL entries)
- Every knowledge entry must include an explicit "what this achieves" section before the mapping
- Frame translations as: "This Airflow concept achieves X. In Prefect, the equivalent concept is Y, achieved via Z."
- Focus on the problem being solved, not mechanical syntax porting
- For concepts with no equivalent, explain the paradigm shift — why the concept doesn't map, not just that it doesn't
- Phase 1 models were mixed on this (Kubernetes was intent-first, HTTP was mechanical). Phase 3 sets the standard.

### Knowledge Entry Depth
- Each Colin model: mapping + code example + credential/block setup
- One .md per operator in colin/models/operators/ (same structure as Phase 1)
- Stick to requirements scope only — no extra Azure operators beyond WasbOperator and AzureDataFactoryRunPipelineOperator

### "No Equivalent" Concepts
- Tone: Honest and opinionated — "No direct equivalent. Here's what we recommend instead..."
- Include both conceptual explanation AND code snippet for workarounds
- depends_on_past and deferrable operators: standalone concept entries (not inline notes on other operators)
- Output format: structured differently from normal mappings — use `equivalent: none` with a `workaround` section so the LLM knows this isn't a drop-in replacement

### Schedule Translation in Scaffold
- Cron strings pass through directly to Prefect's cron schedule
- timedelta intervals convert to Prefect's native IntervalSchedule (not cron equivalents)
- Scaffold accepts schedule as a parameter (LLM extracts it from DAG and passes it in)
- No schedule (None/@once): omit schedule section from prefect.yaml entirely — no comments, no placeholders

### Jinja Macro Scope
- Cover the 5 required macros (ds_add, dag_run.conf, next_ds, prev_ds, run_id) plus ~5 common extras (ds, ts, execution_date, params, var.value)
- Live in a dedicated Jinja/template variables section in patterns.md
- Intent-first: explain what each macro achieves in Airflow, then show how Prefect handles that same need
- For macros with no Prefect equivalent concept (e.g., prev_ds assumes sequential runs): explain the paradigm shift, don't just say "not applicable"

### Claude's Discretion
- Exact list of "common extras" beyond the 5 required Jinja macros
- How to structure the "intent/what this achieves" section in Colin model format
- Whether lookup_concept needs query normalization for Jinja syntax (stripping {{ }})

</decisions>

<specifics>
## Specific Ideas

- "We need to be thinking about what these patterns are trying to achieve, not how to directly port them" — this is the guiding principle for all entries
- Kubernetes model from Phase 1 is the gold standard for intent-first approach (ARCHITECTURE SHIFT framing)
- HTTP model from Phase 1 is an example of what to avoid (mechanical syntax mapping)

</specifics>

<deferred>
## Deferred Ideas

- Review and update Phase 1 knowledge entries (Kubernetes, Databricks, Spark, HTTP, SSH) for intent-first consistency — separate work, not Phase 3 scope

</deferred>

---

*Phase: 03-p2-knowledge-expansion*
*Context gathered: 2026-02-26*

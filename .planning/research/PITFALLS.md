# Pitfalls Research

**Domain:** Airflow-to-Prefect migration tooling (MCP server + LLM-assisted conversion)
**Researched:** 2026-02-26
**Confidence:** MEDIUM — sourced from official Prefect migration docs (HIGH) and WebSearch (verified where possible)

---

## Critical Pitfalls

### Pitfall 1: Trigger Rules Have No Direct Prefect Equivalent

**What goes wrong:**
Airflow's `trigger_rule` parameter (`ALL_DONE`, `ONE_FAILED`, `ALL_FAILED`, `NONE_FAILED`, `ONE_SUCCESS`, etc.) has no declarative counterpart in Prefect. When an LLM converts a DAG, it may silently drop trigger rules or generate code that behaves differently at runtime. A `trigger_rule="all_done"` task in Airflow runs regardless of upstream success or failure — this requires explicit `try/except` and state-checking logic in Prefect, not a parameter.

**Why it happens:**
The mental model is fundamentally different. Airflow uses a declarative graph with operator-level execution control. Prefect uses imperative Python control flow — the "trigger rule" concept simply does not exist as a first-class parameter. LLMs trained on Airflow patterns will try to map `trigger_rule` to something analogous, either hallucinating a Prefect parameter that doesn't exist or dropping the logic entirely.

**How to avoid:**
The knowledge base must include an explicit entry for every `trigger_rule` variant explaining the Prefect imperative equivalent. The `lookup_concept` tool should surface this mapping when the LLM encounters `trigger_rule` in a DAG. Validation (`validate` tool) should flag converted flows where `trigger_rule` was present in the original but no corresponding try/except or state-check is visible in the output.

**Warning signs:**
- Original DAG has `trigger_rule=` in any task definition
- Generated Prefect code contains no try/except blocks around tasks that had non-default trigger rules
- Generated code does not import or use `prefect.states`

**Phase to address:**
Knowledge completeness phase — expand fallback knowledge to explicitly cover all 9 Airflow trigger rule variants with Prefect equivalents.

---

### Pitfall 2: XCom Chains Silently Broken During Conversion

**What goes wrong:**
Airflow XComs are a backend-mediated data store. Tasks call `ti.xcom_push(key, value)` and `ti.xcom_pull(task_ids, key)` explicitly, or implicitly via TaskFlow API return values. In Prefect, tasks return values directly and pass them as function arguments — there is no XCom system. When an LLM converts an XCom-heavy DAG, it may drop the data dependencies, converting XCom pulls to hardcoded values or ignoring them entirely. The resulting flow compiles and runs but produces wrong results or fails at runtime when data is missing.

**Why it happens:**
Explicit XCom calls (`xcom_push`, `xcom_pull`) are recognizable and usually handled correctly. But implicit XComs — where the TaskFlow API auto-captures operator return values — are harder to detect because they look like normal Airflow task calls. The LLM may not realize a data dependency exists if the original DAG uses `{{ ti.xcom_pull(...) }}` inside Jinja template strings embedded in operator arguments.

**How to avoid:**
The knowledge base must explain both explicit and implicit XCom patterns. The `lookup_concept` tool entry for XCom should include Jinja-embedded XCom pulls as a specific sub-pattern. When the LLM reads the DAG source (`read_dag`), it must be guided to look for both `xcom_push/pull` calls and `{{ ti.xcom_pull(...) }}` in template fields.

**Warning signs:**
- Original DAG has `xcom_push`, `xcom_pull`, or `{{ ti.xcom_pull` in any form
- Generated flow passes no arguments between tasks where the original DAG had XCom relationships
- Generated flow uses hardcoded values where the original used dynamic values

**Phase to address:**
Knowledge completeness phase — XCom entry must cover explicit calls, TaskFlow implicit returns, and Jinja-embedded pulls as three distinct patterns.

---

### Pitfall 3: Sensor Operators Require Architectural Redesign, Not Simple Translation

**What goes wrong:**
Airflow sensors (`S3KeySensor`, `HttpSensor`, `ExternalTaskSensor`, `FileSensor`, etc.) are blocking polling operators — they occupy a worker slot and poll until a condition is met or they time out. In Prefect, there is no direct sensor equivalent. The correct Prefect pattern depends on use case: lightweight polling becomes a loop with `time.sleep` inside a task, external task waiting becomes a Prefect flow trigger or automation, and event-driven sensors may require Prefect's event system. An LLM that treats sensors as translatable to a simple Prefect task will produce code that either polls incorrectly, blocks indefinitely, or misses the event entirely.

**Why it happens:**
Sensors look like operators in Airflow code — they have the same constructor signature pattern and integrate into the DAG graph the same way. But their runtime semantics are completely different from compute operators. An LLM that pattern-matches "operator class → task function" will fail to recognize that sensors need architectural rethinking.

**How to avoid:**
Each major sensor type needs a dedicated knowledge entry explaining its correct Prefect pattern (not just "use a loop"). The `lookup_concept` tool must surface sensor-specific knowledge when any `*Sensor` class is detected. The LLM instruction should explicitly flag sensor conversion as requiring a different approach than operator conversion.

**Warning signs:**
- Original DAG imports any class ending in `Sensor`
- Generated flow converts a sensor to a simple `@task` with a single condition check and no retry/polling logic
- Generated flow has no sleep, retry, or event-listening pattern where the original had a sensor

**Phase to address:**
Knowledge completeness phase — add sensor entries for S3KeySensor, HttpSensor, ExternalTaskSensor, FileSensor, and the general sensor pattern.

---

### Pitfall 4: Jinja Templating in Operator Arguments Is Not Python

**What goes wrong:**
Airflow uses Jinja templates inside operator arguments to inject runtime context: `{{ ds }}`, `{{ execution_date }}`, `{{ ti.xcom_pull(...) }}`, `{{ var.value.my_variable }}`, `{{ params.my_param }}`. These are not Python — they are Airflow's template rendering system and only execute inside the Airflow runtime. When an LLM encounters these strings, it may leave them as-is in the generated Prefect code (producing broken string literals), try to interpolate them with Python f-strings (incorrect), or simply remove them without preserving the dynamic value they represented.

**Why it happens:**
Jinja template strings look like Python f-strings to an LLM but are a completely different system. The context variables (`ds`, `execution_date`, `ti`, `var`, `params`) are Airflow-specific and do not exist in a Prefect flow. The correct conversion depends on what the template value represents: execution date becomes a Prefect parameter or `datetime.now()`, variables become environment variables or Prefect variables, XCom pulls become direct function returns.

**How to avoid:**
The knowledge base must include a Jinja templating concept entry that maps each common Airflow context variable to its Prefect equivalent. The LLM must be instructed to identify every `{{ ... }}` pattern in the source DAG and explicitly convert each one — not pass them through, not wrap in f-strings.

**Warning signs:**
- Original DAG has `{{` in any string argument to an operator
- Generated flow contains any `{{` in string literals
- Generated flow uses Python f-strings containing former Airflow context variable names (`ds`, `execution_date`, `ts`, etc.)

**Phase to address:**
Knowledge completeness phase — add explicit Jinja context variable mapping as a concept entry.

---

### Pitfall 5: Airflow Connections and Hooks Require Manual Re-credentialing

**What goes wrong:**
Airflow Connections (stored in the Airflow metadata DB or Secrets Backend) have no automatic migration path to Prefect. Hooks like `PostgresHook(conn_id="my_db")` rely on a connection object stored in Airflow's connection store. In Prefect, credentials are managed via Prefect Blocks (`prefect-postgres`, `prefect-gcp`, etc.) or environment variables. An LLM converting DAGs with hook usage may generate Prefect tasks that reference a connection by ID (which will fail) or generate syntactically correct code that cannot run without manual secrets configuration.

**Why it happens:**
The connection ID is a string in the source DAG. It looks like it could be passed through to Prefect. But `PostgresHook(conn_id="my_db")` is an Airflow-specific abstraction that hits Airflow's connection registry at runtime — the string `"my_db"` means nothing outside Airflow. An LLM that does not deeply understand the hook architecture will pass this string to a Prefect integration incorrectly.

**How to avoid:**
The knowledge base must include entries for the most common hooks (PostgresHook, MySqlHook, S3Hook, GCSHook, HttpHook, etc.) with explicit mappings to their Prefect equivalents and required Block setup. The LLM output should flag every converted connection as requiring manual Block configuration — include this in the scaffold output.

**Warning signs:**
- Original DAG imports any class ending in `Hook`
- Generated Prefect code contains `conn_id` as a string argument without a note about Block setup
- Generated flow imports from `airflow.providers` rather than `prefect_*` packages

**Phase to address:**
Knowledge completeness phase (hooks mapping) and scaffold phase (output includes Block configuration requirements).

---

### Pitfall 6: Scheduling Is Extracted from the Flow, Not Embedded

**What goes wrong:**
Airflow DAGs embed scheduling directly in the DAG definition: `schedule_interval="0 0 * * *"`, `schedule=timedelta(hours=1)`, `start_date=datetime(2024, 1, 1)`. In Prefect, scheduling is external — defined in `prefect.yaml` or via the CLI/UI, not in the flow code itself. An LLM that preserves the schedule inside the Python file will generate code that compiles and runs but is never scheduled unless the user reads the Prefect docs and separately configures a deployment.

**Why it happens:**
The schedule is visible in the DAG source. It seems natural to preserve it. But Prefect's design separates the flow definition from deployment configuration. This is a correct design choice in Prefect, but it means generated flow files will always look "incomplete" compared to the source DAG unless the scaffold step handles the schedule.

**How to avoid:**
The `scaffold` tool output must include scheduling configuration in `prefect.yaml`. When the LLM reads a DAG with a schedule, it should pass the schedule to the scaffold tool so the deployment YAML captures it. The generated flow file should contain a comment noting that scheduling is in `prefect.yaml`.

**Warning signs:**
- Generated `flow.py` contains commented-out schedule or `schedule_interval` variable
- Scaffold output `prefect.yaml` has no `schedules:` section when the original DAG had a schedule
- Generated flow imports `from datetime import timedelta` only for schedule purposes

**Phase to address:**
Scaffold completeness phase — `prefect.yaml` must include schedule translation.

---

### Pitfall 7: Dynamic DAGs and `generate_dags` Patterns Are Difficult to Convert

**What goes wrong:**
Advanced Airflow users generate DAGs dynamically: factory functions that create multiple DAGs from config, `for` loops that create task instances, `expand()` / dynamic task mapping (Airflow 2.3+). These patterns have Prefect equivalents (`.map()`, subflows, parametrized deployments), but the conversion is non-trivial because the source code generates DAG structure at import time — the LLM must understand what the generated structure will look like and convert it to equivalent Prefect constructs.

**Why it happens:**
Dynamic DAGs are metaprogramming in Python. An LLM reading the source code sees the generator function, not the generated DAGs. Converting a factory function that generates 50 DAGs from a config list requires understanding the intent (50 parametrized flows) and producing the right Prefect structure (parametrized deployments or a single flow with parameter dispatch), not literally converting the factory code.

**How to avoid:**
The knowledge base must include entries for dynamic DAG patterns and dynamic task mapping (`expand()`, `partial()`, `.map()`). The LLM should be instructed to identify factory patterns and address them explicitly. The `validate` tool should flag conversions of dynamic DAGs as requiring human review.

**Warning signs:**
- Original DAG source defines a function that returns a DAG object
- Original DAG uses `expand()` or `partial()` with operator calls
- Source file contains a `for` loop at module level that creates operators
- Generated Prefect flow is static when the source was dynamic

**Phase to address:**
Knowledge completeness phase — add dynamic DAG and dynamic task mapping entries.

---

### Pitfall 8: SubDAG / TaskGroup Topology Not Preserved in Subflows

**What goes wrong:**
Airflow's `SubDagOperator` and `TaskGroup` organize tasks visually and logically. `SubDagOperator` (deprecated in Airflow 2.x, removed in Airflow 3.x) created a nested DAG that ran as a child workflow. `TaskGroup` groups tasks visually. Both translate to Prefect subflows (`@flow` calling `@flow`) but the mapping is not direct: SubDAGs had their own scheduler interactions, concurrency limits, and deadlock risks. Converting a SubDAG to a Prefect subflow preserves the logical grouping but changes runtime semantics (subflow state propagation, retry behavior).

**Why it happens:**
Both SubDAGs and TaskGroups look like groupings of tasks. An LLM may convert them equivalently to subflows or simply inline the tasks. The critical difference — SubDAGs ran as separate Airflow DAG runs with separate scheduler state — may be invisible in the source code and lost in conversion.

**How to avoid:**
The knowledge base must distinguish SubDagOperator from TaskGroup and explain their different Prefect equivalents. SubDagOperator conversion should produce a `@flow` subflow; TaskGroup can be a Python function or a subflow depending on complexity.

**Warning signs:**
- Original DAG imports `SubDagOperator`
- Original DAG uses `TaskGroup` context manager
- Generated flow inlines all tasks as flat `@task` functions with no grouping structure

**Phase to address:**
Knowledge completeness phase — add SubDagOperator and TaskGroup entries with distinct conversion guidance.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Only cover 6 fallback operators in knowledge base | Fast to implement | Users hit `not_found` for 80% of real-world operators; LLM generates guesses instead of guided translations | Never — expand fallback coverage |
| Pass Airflow operator args directly to Prefect task params | Low effort | Arguments may be Jinja templates or Airflow-specific types that fail silently at runtime | Never |
| Leave schedule in flow.py as a comment | Preserves info from source | Users forget to configure deployment; flows never run on schedule | MVP only, with explicit warning |
| Skip trigger_rule conversion and just note it | Avoids complex logic | Generated flow may produce incorrect results silently when upstream tasks fail | Never — trigger rules change correctness, not just style |
| Convert all sensors to "polling task with sleep" | Uniform pattern | Long-running sensors block Prefect workers; for ExternalTaskSensor, a polling loop is wrong | For short-lived sensors only (<5 min expected wait) |

---

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Airflow Connections → Prefect Blocks | Pass `conn_id` string to Prefect integration as-is | Identify the hook type, map to specific Prefect Block (e.g., `SqlAlchemyConnector`, `GcsBucket`), include Block setup in scaffold |
| Prefect MCP docs search | Query with Airflow terminology (e.g., "sensor equivalent") | Query with Prefect concepts (e.g., "polling task retry") — the LLM should translate before querying |
| Colin knowledge output | Assume Colin output covers all operators | Colin covers what it compiled from live sources; gaps are common for provider-specific operators |
| `prefect.yaml` generation | Generate schedule in cron syntax only | Airflow supports timedelta, cron, and dataset-based schedules — each needs different Prefect representation |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Converting sensors to blocking tasks | Prefect workers occupied for hours waiting on external events | Use event-driven triggers or polling flows with short timeouts | Any production sensor with >30min expected wait |
| Generating one `@task` per Airflow operator without batching | High task overhead for simple data pipelines | Group trivial sequential operators into a single `@task` | 20+ sequential trivial operators in a single flow |
| Leaving Airflow pool/slot constraints implicit | Converted flow runs unbounded concurrency; overwhelms target systems | Map Airflow pool constraints to Prefect global concurrency limits in scaffold | Any DAG with `pool=` or `pool_slots=` configured |
| Knowledge base lookup for every concept | Slow response when LLM queries for each operator | Batch lookups at start of conversion session | Large DAGs (50+ operators) |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Generated flow compiles but fails at runtime due to missing Block credentials | User thinks conversion succeeded; discovers failure during test run | Scaffold output must list every required Block type and credential as explicit setup steps |
| Knowledge base returns `not_found` without suggestions | LLM has no guidance; may hallucinate Prefect API | Always return partial matches and "search Prefect docs" fallback — never a bare `not_found` |
| Validate tool compares syntax only | User trusts "valid" result but logic is wrong | Validate output must explicitly state it only checks syntax, not semantic correctness — frame it as "review both sources yourself" |
| Generated code uses deprecated Prefect 2.x API | User gets deprecation warnings or errors | Knowledge base must specify Prefect 3.x patterns; Colin compilation should target Prefect 3 docs |
| Scaffold produces directory structure without flow content | User confused what goes where | Scaffold output must include brief inline comments in each file explaining its purpose and what the LLM should put there |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Trigger rules:** Converted flow has tasks with non-default `trigger_rule` in original — verify Prefect equivalent logic is present (try/except, state checks)
- [ ] **XCom dependencies:** Every `xcom_push/pull` or `{{ ti.xcom_pull }}` in the source has a corresponding data flow in the generated flow
- [ ] **Jinja templates:** No `{{ ... }}` strings survive into generated flow — all converted to Python variables, parameters, or environment lookups
- [ ] **Schedule preserved:** Converted `prefect.yaml` includes schedule when original DAG had `schedule_interval` or `schedule`
- [ ] **Connections documented:** Every Airflow hook usage has a corresponding Block setup instruction in scaffold output
- [ ] **Sensor logic intact:** Every `*Sensor` class in original has explicit polling or event logic in converted flow, not a bare condition check
- [ ] **Dynamic task mapping:** Any `expand()` or `partial()` call in original has a `.map()` equivalent in converted flow
- [ ] **Pool constraints:** Any `pool=` or `pool_slots=` in original has a corresponding concurrency limit note in scaffold output
- [ ] **Callbacks converted:** Any `on_failure_callback` or `on_success_callback` in original has Prefect state handler or notification equivalent

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Trigger rules dropped silently | HIGH | Re-read original DAG for all `trigger_rule` usages; manually implement Prefect state-check logic for each; re-validate |
| XCom chain broken | HIGH | Map all XCom keys in original to their consumers; trace data flow graph; add direct function returns to converted flow |
| Jinja templates left in output | MEDIUM | Grep generated flow for `{{`; replace each with its Python equivalent using Airflow context variable mapping |
| Missing schedule in prefect.yaml | LOW | Add schedule section to `prefect.yaml`; re-deploy |
| Hook/connection not found | MEDIUM | Identify Prefect integration package for the hook type; install package; create Block; update flow to use Block |
| Wrong Prefect API version (2.x vs 3.x) | MEDIUM | Identify which calls are 2.x-only; replace with 3.x equivalents using Prefect docs search |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Trigger rules dropped | Knowledge completeness — add all 9 trigger rule variants | Test with DAG containing `trigger_rule="one_failed"` |
| XCom chain broken | Knowledge completeness — explicit XCom and TaskFlow patterns | Test with DAG using both explicit and implicit XComs |
| Jinja templates not converted | Knowledge completeness — Jinja context variable mapping | Test with DAG using `{{ ds }}`, `{{ ti.xcom_pull }}`, `{{ var.value.x }}` |
| Schedule not preserved | Scaffold completeness — `prefect.yaml` schedule translation | Test scaffold output for DAG with cron schedule |
| Connections require manual setup | Scaffold completeness — Block requirements listed | Verify scaffold lists required Blocks for DAG using PostgresHook |
| Sensors require redesign | Knowledge completeness — per-sensor-type entries | Test with DAG using S3KeySensor and ExternalTaskSensor |
| Dynamic DAGs not handled | Knowledge completeness — dynamic task mapping entries | Test with DAG using `expand()` |
| Wrong Prefect version | Knowledge compilation (Colin) — target Prefect 3.x docs | Verify all generated imports are valid Prefect 3.x |

---

## Sources

- Prefect official migration guide: https://docs.prefect.io/v3/how-to-guides/migrate/airflow (HIGH confidence)
- Prefect migration tutorial: https://docs.prefect.io/v3/tutorials/airflow (HIGH confidence)
- Prefect migration playbook blog: https://www.prefect.io/blog/airflow-to-prefect-migration-playbook (MEDIUM confidence)
- Prefect Airflow 2 EOL guide: https://www.prefect.io/compare/airflow-2 (MEDIUM confidence — vendor perspective)
- Airflow trigger rules documentation: https://airflow.apache.org/docs/apache-airflow/stable/ (HIGH confidence)
- Airflow dynamic task mapping: https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/dynamic-task-mapping.html (HIGH confidence)
- Airflow callbacks documentation: https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/logging-monitoring/callbacks.html (HIGH confidence)
- Astronomer trigger rules guide: https://www.astronomer.io/blog/understanding-airflow-trigger-rules-comprehensive-visual-guide/ (MEDIUM confidence)
- Prefect global concurrency limits: https://docs.prefect.io/v3/how-to-guides/workflows/global-concurrency-limits (HIGH confidence)
- LLM + MCP Airflow update patterns: https://chengzhizhao.com/beyond-basic-prompts-llm-mcp-tackling-real-world-challenges-the-airflow-3-0-auto-update-example/ (LOW confidence — single blog post)
- Codebase CONCERNS.md analysis: /Users/gcoyne/src/prefect/airflow-unfactor/.planning/codebase/CONCERNS.md (HIGH confidence — direct codebase audit)

---
*Pitfalls research for: Airflow-to-Prefect migration tooling (airflow-unfactor MCP server)*
*Researched: 2026-02-26*

## Why

The tool claims "Complete Conversion" but has gaps. Investigation revealed these gaps are resolvable—Prefect has primitives for dynamic task mapping, trigger rules, Jinja2 template equivalents, and connection/variable scaffolding. Rather than documenting limitations, we close them. The remaining "limitation" (custom operators) just needs prompting for human refactoring of user-defined code.

## What Changes

### Conversion Feature Completeness

- **Dynamic task mapping**: Convert Airflow `.expand()` to Prefect `.map()` (nearly 1:1 API)
- **TaskGroups**: Convert `@task_group` to `@flow` subflows; handle `.expand()` on groups via wrapper tasks
- **Trigger rules**: Convert `trigger_rule` parameter using `return_state=True`, `allow_failure`, and state checks (`.is_failed()`, `.is_completed()`)
- **Jinja2 templates**: Convert `{{ ds }}`, `{{ params.x }}`, etc. to `runtime.flow_run.scheduled_start_time` + f-strings
- **Connections→Blocks**: Detect hook usage (`PostgresHook(conn_id='x')`), scaffold Prefect Block definitions
- **Variables→Config**: Detect `Variable.get()`, scaffold Prefect Variable/Secret based on name patterns
- **Custom operators**: Detect non-standard operators, extract `execute()` method, prompt user for refactoring guidance

### Interface & Experience

- **Runbook specificity**: Parse DAG-level settings (@dag decorator args, callbacks, SLAs) into actionable runbook
- **Conversion output contract**: Publish canonical JSON schema for MCP tool responses
- **Docs update**: Update claims to reflect actual (now-complete) capabilities; add troubleshooting guide

## Capabilities

### New Capabilities

- `dynamic-task-mapping`: Convert Airflow `.expand()` and `.partial().expand()` patterns to Prefect `.map()`. Detect in AST, map parameters, warn on `map_index_template` (UI-only, no Prefect equivalent).

- `taskgroup-converter`: Convert `@task_group` decorator to `@flow` subflows. When TaskGroup uses `.expand(param=[...])`, generate wrapper `@task` that calls subflow for each value. Preserve task organization in flow structure.

- `trigger-rule-converter`: Convert Airflow `trigger_rule` parameter to Prefect state-based patterns:
  - `all_success` (default): Normal task call
  - `all_done`: Use `return_state=True`, call task regardless of upstream state
  - `all_failed`/`one_failed`/`one_success`/`none_failed`: Use `allow_failure` annotation + state checks
  Generate appropriate wrapper code with educational comments.

- `jinja-template-converter`: Convert Airflow Jinja2 template variables to Prefect runtime context:
  - `{{ ds }}` → `runtime.flow_run.scheduled_start_time.strftime('%Y-%m-%d')`
  - `{{ ds_nodash }}` → `.strftime('%Y%m%d')`
  - `{{ ts }}` → `.isoformat()`
  - `{{ params.x }}` → flow parameters
  - `{{ macros.ds_add(ds, N) }}` → `scheduled_start_time + timedelta(days=N)`
  Detect patterns in string literals, convert to f-strings with runtime imports.

- `connection-to-block`: Detect Airflow connection usage (hooks, `BaseHook.get_connection()`), scaffold Prefect Block definitions:
  - `PostgresHook` → `SqlAlchemyConnector`
  - `S3Hook` → `S3Bucket` / `AwsCredentials`
  - `BigQueryHook` → `BigQueryCredentials`
  Generate Block scaffold + deployment setup instructions (no secrets in code).

- `variable-to-config`: Detect `Variable.get("name")` and `Variable.set()`, scaffold Prefect equivalents:
  - Names containing key/password/secret/token → recommend `Secret`
  - Config with defaults → recommend flow parameter
  - Dynamic read/write → recommend `Variable`
  Generate all three options with recommendations.

- `custom-operator-handler`: Detect operators not in provider mappings, extract `execute()` method body, generate prompt requesting user guidance on refactoring to `@task`. Include original code context for informed refactoring.

- `runbook-generation`: Extract DAG-level settings from both `DAG()` constructor and `@dag` decorator:
  - Schedule, catchup, max_active_runs, tags
  - `default_args` (retries, retry_delay, etc.)
  - Callbacks: `on_success_callback`, `on_failure_callback`, `sla_miss_callback`
  Map to Prefect equivalents (deployment config, state hooks, automations) in runbook.

- `conversion-output-schema`: Canonical JSON schema for MCP tool responses (analyze, convert, validate, explain). Versioned contract for downstream consumers. Include validation examples.

### Modified Capabilities

- (none—existing specs remain unchanged; these are additive capabilities)

## Impact

**Code changes:**
- `src/airflow_unfactor/converters/dynamic_mapping.py`: New—`.expand()` detection and conversion
- `src/airflow_unfactor/converters/taskgroup.py`: New—`@task_group` to `@flow` conversion
- `src/airflow_unfactor/converters/trigger_rules.py`: New—trigger rule to state-based patterns
- `src/airflow_unfactor/converters/jinja.py`: New—Jinja2 template to runtime context
- `src/airflow_unfactor/converters/connections.py`: New—hook detection and Block scaffolding
- `src/airflow_unfactor/converters/variables.py`: New—Variable.get() detection and scaffolding
- `src/airflow_unfactor/analysis/parser.py`: Extend to extract @dag decorator args, callbacks, custom operators
- `src/airflow_unfactor/tools/convert.py`: Integrate new converters, enhance runbook generation
- `schemas/conversion-output.json`: New—JSON Schema for tool responses

**Documentation changes:**
- `docs/index.md`: Update to reflect complete conversion capabilities
- `docs/troubleshooting.md`: New—common issues and resolutions

**Affected beads:**
- `airflow-unfactor-16o`: Dynamic task mapping
- `airflow-unfactor-1xl`: TaskGroups
- `airflow-unfactor-393`: Trigger rules
- `airflow-unfactor-3jz`: Connections→Blocks
- `airflow-unfactor-3va`: Variables→Config
- `airflow-unfactor-3ht` (P1): Now "verify completeness" rather than "document limitations"
- `airflow-unfactor-pji`: Runbook enhancement
- `airflow-unfactor-1bc`: @dag decorator parsing
- `airflow-unfactor-3kd`: Callback/SLA extraction
- `airflow-unfactor-335`: Conversion output contract

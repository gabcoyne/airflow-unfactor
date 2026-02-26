# Phase 1: P1 Knowledge Expansion - Research

**Researched:** 2026-02-26
**Domain:** Colin model authoring — Airflow provider operator → Prefect translation knowledge
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| KNOW-01 | Colin model for KubernetesPodOperator → Kubernetes work pool pattern with architectural shift guidance | KubernetesPodOperator mapping verified in STACK.md; Kubernetes work pool is the correct pattern; `prefect-kubernetes` package confirmed |
| KNOW-02 | Colin model for DatabricksSubmitRunOperator → prefect-databricks DatabricksSubmitRun task | DatabricksSubmitRunOperator → `DatabricksSubmitRun` task mapping documented in STACK.md; `DatabricksCredentials` block pattern confirmed |
| KNOW-03 | Colin model for DatabricksRunNowOperator → prefect-databricks DatabricksRunNow task | DatabricksRunNowOperator → `DatabricksJobRunNow` task mapping documented in STACK.md; same credentials block |
| KNOW-04 | Colin model for SparkSubmitOperator → shell/Databricks/Dataproc execution paths | SparkSubmitOperator → `prefect-shell` + `spark-submit` CLI or managed Spark; three distinct paths verified in STACK.md |
| KNOW-05 | Colin model for HttpOperator/SimpleHttpOperator → httpx task pattern | SimpleHttpOperator → direct `httpx` in `@task`; intentionally no dedicated package; pattern verified in STACK.md |
| KNOW-06 | Colin model for SSHOperator → paramiko/fabric task with Secret block | SSHOperator → `paramiko`/`fabric` in `@task` with `Secret` block for credentials; no dedicated prefect-ssh package confirmed |
</phase_requirements>

## Summary

Phase 1 is a pure Colin model authoring task. It creates five new Markdown files in `colin/models/operators/` — one per Airflow provider package — covering the six operators that cause the most frequent tool failure at enterprise installations. The operator-to-Prefect mappings are fully documented in official Airflow and Prefect docs, so this is an authoring and formatting task, not a research or design task.

The KNOW-02 and KNOW-03 requirements both target the Databricks provider and belong in a single file (`operators/databricks.md`). KNOW-04 (SparkSubmitOperator) and KNOW-06 (SSHOperator) each go in their own files. KNOW-05 (SimpleHttpOperator) goes in `operators/http.md`. KNOW-01 (KubernetesPodOperator) is the highest-stakes entry: without it, LLMs revert to subprocess or docker SDK calls instead of the correct Kubernetes work pool pattern.

The work is additive. No existing Colin model files change, no server code changes, and no test infrastructure changes. Each file follows the established `{% section %}` + YAML frontmatter format used by `aws.md`, `gcp.md`, and the others. After authoring, `colin run` must be executed from the `colin/` directory to compile the new models to JSON and make them available to the MCP server.

**Primary recommendation:** Author five new Colin model files in the order: `kubernetes.md` → `http.md` → `databricks.md` → `spark.md` → `sftp.md`. Run `colin run` once all five are written. Validate via `lookup_concept` for each operator name.

## Standard Stack

### Core

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| Colin model format | `{% section %}` blocks with YAML frontmatter | Knowledge authoring format | Established by existing 8 model files; `colin run` compiles to JSON |
| `prefect-kubernetes` | Latest | KubernetesPodOperator → Kubernetes work pool | Official Prefect integration for Kubernetes; the only non-subprocess path |
| `prefect-databricks` | Latest | DatabricksSubmitRunOperator, DatabricksRunNowOperator | Official Prefect integration; provides `DatabricksSubmitRun` and `DatabricksJobRunNow` tasks |
| `httpx` | Latest | SimpleHttpOperator → HTTP calls in `@task` | Standard Python HTTP library; Prefect does not ship a dedicated HTTP package by design |
| `prefect-shell` | Latest | SparkSubmitOperator → `spark-submit` CLI invocation | `ShellOperation` is the correct pattern for shell-based Spark; already in Colin for BashOperator |
| `paramiko` / `fabric` | Latest | SSHOperator → SSH execution in `@task` | No dedicated `prefect-ssh` package; `paramiko` is the stdlib-adjacent choice |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `prefect` `Secret` block | Core | Store SSH credentials, HTTP API keys, sensitive connection info | Any operator that reads credentials from `conn_id` where no dedicated Prefect block exists |
| `DatabricksCredentials` block | prefect-databricks | Databricks workspace token or OAuth credentials | Replaces `databricks_conn_id` in both Databricks operator types |
| `KubernetesJob` block | prefect-kubernetes | Per-job Kubernetes configuration (image, resources, env) | Advanced per-task Kubernetes customization within a Kubernetes work pool |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `httpx` for SimpleHttpOperator | `requests` | Both are correct; `httpx` is preferred for new Prefect code (async support, httpx is the Prefect docs recommendation) |
| `paramiko` for SSHOperator | `fabric` | `fabric` is higher-level and handles common SSH patterns more cleanly; `paramiko` gives finer control; document both |
| `prefect-shell` for SparkSubmitOperator | `subprocess.run` directly | `ShellOperation` is preferred as it integrates with Prefect logging; `subprocess` is acceptable but loses log streaming |

## Architecture Patterns

### Recommended Project Structure

```
colin/
└── models/
    └── operators/
        ├── core.md          # existing
        ├── aws.md           # existing
        ├── database.md      # existing
        ├── gcp.md           # existing
        ├── sensors.md       # existing
        ├── kubernetes.md    # NEW — KNOW-01
        ├── http.md          # NEW — KNOW-05
        ├── databricks.md    # NEW — KNOW-02, KNOW-03
        ├── spark.md         # NEW — KNOW-04
        └── sftp.md          # NEW — KNOW-06
```

Each new file is a standalone provider-scoped knowledge file. After authoring, `colin run` compiles all five to JSON alongside the existing files.

### Pattern 1: Provider-Scoped Colin Model File

**What:** One `.md` file per Airflow provider package. YAML frontmatter + `{% section OperatorName %}` blocks. Each section has required fields: `operator`, `module`, `source_context`, `prefect_pattern`, `prefect_package`, `prefect_import`, `example` (before/after), `notes`.

**When to use:** Every time operators from a new `apache-airflow-providers-*` package need coverage.

**Example (from existing `aws.md`):**

```markdown
---
name: AWS Provider Operator Mappings
colin:
  output:
    format: json
---

{% section S3CreateObjectOperator %}
## operator
S3CreateObjectOperator

## module
airflow.providers.amazon.aws.operators.s3

## source_context
Creates an object in S3 with provided data. Uses boto3 `put_object`.

## prefect_pattern
S3Bucket.upload_from_path or write_path

## prefect_package
prefect-aws

## prefect_import
from prefect_aws import S3Bucket

## example
### before
```python
upload = S3CreateObjectOperator(task_id="upload", s3_bucket="my-bucket", ...)
```
### after
```python
@task
def upload(key: str, data: str):
    bucket = S3Bucket.load("my-bucket")
    bucket.write_path(key, content=data.encode())
```

## notes
- For file uploads, use upload_from_path
{% endsection %}
```

### Pattern 2: Architectural Shift Entries (KubernetesPodOperator)

**What:** KubernetesPodOperator is not a parameter-for-parameter translation. The Airflow model is "operator spawns a pod per task." The Prefect model is "work pool defines infrastructure; flows deploy to it." The Colin entry must convey this shift, not just list parameter mappings.

**When to use:** Any operator whose translation requires a fundamental change in how infrastructure is declared.

**Key content for `kubernetes.md`:**

```markdown
## notes
- KubernetesPodOperator is an INFRASTRUCTURE concern, not a task concern in Prefect
- There is no per-task pod spawning in Prefect; infrastructure is defined at the work pool level
- For per-task image isolation: deploy each flow/subflow to a separate Kubernetes work pool
  with a custom base job template
- `image` → set in the Kubernetes work pool base job template, not in task code
- `env_vars` → environment variables in the work pool or `KubernetesJob` block
- `container_resources` (requests/limits) → customized via base job template
- `cmds`, `arguments` → override container command in the job template
- Do NOT use subprocess.run() or docker SDK to emulate KubernetesPodOperator
- Do NOT wrap the operator call directly; the entire deployment pattern changes
```

### Pattern 3: No-Package Translations (SimpleHttpOperator, SSHOperator)

**What:** Some Airflow providers have no Prefect integration package equivalent. The correct Prefect pattern is to use the Python library directly inside a `@task`. The Colin entry must be explicit that there is no `prefect-http` or `prefect-ssh` package.

**When to use:** Any operator where `conn_id` credentials should move to `Secret` block and library calls move inline to `@task`.

**Key content for `http.md`:**

```markdown
## notes
- There is NO prefect-http package; use httpx or requests directly inside @task
- http_conn_id → store base URL and credentials in a Secret block or environment variable
- response_check callable → implement as a conditional assertion inside the @task body
- log_response=True → use get_run_logger() to log response content
```

### Anti-Patterns to Avoid

**Wrapping the Airflow operator class:** Never suggest calling `KubernetesPodOperator(...).execute(context)` in the Prefect flow. The LLM must generate native Prefect code, not wrapped Airflow calls.

**Omitting credential migration:** Every operator with a `conn_id` parameter must include guidance on how the connection maps to a Prefect block. Leaving this out produces flows that compile but fail at runtime.

**Over-specifying KubernetesPodOperator:** Do not attempt to provide a parameter-by-parameter mapping for KubernetesPodOperator. The translation is architectural; the LLM needs conceptual guidance, not a lookup table.

**Using subprocess instead of ShellOperation for SparkSubmitOperator:** ShellOperation integrates with Prefect's logging and observability; `subprocess.run` does not.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Databricks job submission | Custom `requests` calls to Databricks REST API | `prefect-databricks` tasks (`DatabricksSubmitRun`, `DatabricksJobRunNow`) | Package handles auth, polling, error translation |
| Kubernetes pod spawning per task | `kubernetes` Python SDK calls in `@task` | Kubernetes work pool + deployment | Work pool manages pod lifecycle, retries, and cleanup |
| SSH command execution | Manual socket-level SSH | `paramiko.SSHClient` or `fabric.Connection` | Handle key negotiation, host verification, channel management |
| HTTP requests with retry | Custom retry loop | `httpx` with `@task(retries=N)` | Prefect retry decorator handles backoff; httpx handles transport |

**Key insight:** In this phase, "don't hand-roll" applies primarily to credential handling. For each operator, the connection credentials must migrate to a Prefect block (`DatabricksCredentials`, `Secret`, etc.) rather than being hardcoded in flow code or read from environment variables directly.

## Common Pitfalls

### Pitfall 1: KubernetesPodOperator → Subprocess Regression

**What goes wrong:** LLM generates `subprocess.run(["docker", "run", ...])` or `kubernetes.client.CoreV1Api().create_namespaced_pod(...)` inside a `@task`.

**Why it happens:** Without explicit guidance, the LLM interprets "run this image" as "call the container runtime directly."

**How to avoid:** The `notes` field in `kubernetes.md` must state explicitly: "Do NOT use subprocess.run() or the kubernetes Python SDK to emulate pod spawning. Use a Kubernetes work pool." Include in `comparison_guidance` checklist.

**Warning signs:** Generated code imports `kubernetes.client` or calls `subprocess.run(["kubectl", ...])`.

### Pitfall 2: Missing Credential Migration

**What goes wrong:** Generated code has `conn_id="databricks_default"` hardcoded as a string, or attempts `os.environ["DATABRICKS_TOKEN"]` directly, instead of loading a `DatabricksCredentials` block.

**Why it happens:** LLMs see `conn_id` in source and look for the nearest analog. Without explicit guidance, they often leave the string reference or switch to environment variable lookup.

**How to avoid:** Every Colin entry for operators with `conn_id` must include an explicit `## notes` item: "`databricks_conn_id` → create a `DatabricksCredentials` block, load with `DatabricksCredentials.load('block-name')`."

**Warning signs:** Generated code contains `conn_id=`, `get_connection(`, or reads `os.environ["..._CONN"]`.

### Pitfall 3: SparkSubmitOperator → Raw spark-submit Without Logging

**What goes wrong:** LLM generates `subprocess.run(["spark-submit", ...])` which loses stdout/stderr in Prefect's log view.

**Why it happens:** `spark-submit` is a CLI tool; `subprocess.run` is the obvious Python equivalent.

**How to avoid:** Specify `ShellOperation` in `prefect_pattern` and `prefect_package` fields. Include example using `ShellOperation` with `stream_output=True`.

**Warning signs:** Generated code uses `subprocess.run`, `subprocess.Popen`, or `os.system`.

### Pitfall 4: SimpleHttpOperator → prefect-http (Does Not Exist)

**What goes wrong:** LLM generates `from prefect_http import HttpTask` or similar. Package does not exist; flow fails at import.

**Why it happens:** LLMs infer package names from the pattern `prefect-{service}`. No exception for HTTP.

**How to avoid:** The `notes` field in `http.md` must state: "There is NO `prefect-http` package. Use `httpx` or `requests` directly."

**Warning signs:** Generated code imports from `prefect_http`, `prefect.http`, or any non-existent HTTP prefect package.

### Pitfall 5: SSHOperator → Secret Block Not Created

**What goes wrong:** The `Secret` block for SSH credentials is referenced in generated code but not created — the user gets a `Block 'secret/ssh-key' not found` error at runtime.

**Why it happens:** LLMs generate the code correctly but don't tell the user what blocks they need to create before running the flow.

**How to avoid:** Every SSH entry `notes` section must include the block creation steps: "Before running: create a `Secret` block named `ssh-private-key` containing the private key content."

**Warning signs:** Generated code calls `Secret.load(...)` but the corresponding block creation steps are not mentioned in the flow's docstring or comments.

## Code Examples

Verified patterns from official Prefect integration docs and codebase analysis.

### KubernetesPodOperator → Kubernetes Work Pool

```python
# Source: Prefect docs + ARCHITECTURE.md research
# Before (Airflow):
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator

process = KubernetesPodOperator(
    task_id="process_data",
    name="process-data-pod",
    namespace="default",
    image="my-registry/data-processor:v1.2",
    cmds=["python", "-c"],
    arguments=["import pipeline; pipeline.run()"],
    env_vars={"ENV": "prod", "BATCH_SIZE": "1000"},
    container_resources=k8s.V1ResourceRequirements(
        requests={"cpu": "500m", "memory": "1Gi"}
    ),
)

# After (Prefect):
# 1. Create a Kubernetes work pool in your Prefect workspace (via UI or CLI)
# 2. Deploy the flow targeting that work pool
# 3. In the base job template: set image, env vars, resource requests
# The @flow or @task itself contains the logic; infrastructure is in the work pool

from prefect import flow, task

@flow(name="process-data")  # Deployed to Kubernetes work pool
def process_data(env: str = "prod", batch_size: int = 1000):
    # Flow logic here — infrastructure defined in work pool, not in code
    import pipeline
    pipeline.run()
```

### DatabricksSubmitRunOperator → prefect-databricks

```python
# Source: prefect-databricks package docs + STACK.md research
# Before (Airflow):
from airflow.providers.databricks.operators.databricks import DatabricksSubmitRunOperator

submit_run = DatabricksSubmitRunOperator(
    task_id="run_notebook",
    databricks_conn_id="databricks_default",
    json={
        "new_cluster": {"spark_version": "13.3.x-scala2.12", "num_workers": 2},
        "notebook_task": {"notebook_path": "/Users/me/my_notebook"},
    },
)

# After (Prefect):
from prefect import flow, task
from prefect_databricks import DatabricksCredentials
from prefect_databricks.jobs import jobs_runs_submit

@task
def run_notebook(notebook_path: str):
    credentials = DatabricksCredentials.load("databricks-default")
    run = jobs_runs_submit(
        databricks_credentials=credentials,
        json={
            "new_cluster": {"spark_version": "13.3.x-scala2.12", "num_workers": 2},
            "notebook_task": {"notebook_path": notebook_path},
        },
    )
    return run
```

### DatabricksRunNowOperator → prefect-databricks

```python
# Source: prefect-databricks package docs + STACK.md research
# Before (Airflow):
from airflow.providers.databricks.operators.databricks import DatabricksRunNowOperator

run_job = DatabricksRunNowOperator(
    task_id="trigger_job",
    databricks_conn_id="databricks_default",
    job_id=12345,
    notebook_params={"date": "{{ ds }}"},
)

# After (Prefect):
from prefect import task
from prefect_databricks import DatabricksCredentials
from prefect_databricks.jobs import jobs_run_now

@task
def trigger_databricks_job(job_id: int, date: str):
    credentials = DatabricksCredentials.load("databricks-default")
    run = jobs_run_now(
        databricks_credentials=credentials,
        job_id=job_id,
        notebook_params={"date": date},
    )
    return run
```

### SimpleHttpOperator → httpx in @task

```python
# Source: Prefect migration docs + STACK.md research
# Before (Airflow):
from airflow.providers.http.operators.http import SimpleHttpOperator

call_api = SimpleHttpOperator(
    task_id="call_api",
    http_conn_id="my_api",
    endpoint="/v1/process",
    method="POST",
    data=json.dumps({"key": "value"}),
    headers={"Content-Type": "application/json"},
    response_check=lambda response: response.status_code == 200,
    log_response=True,
)

# After (Prefect):
import httpx
from prefect import task
from prefect.logging import get_run_logger
from prefect.blocks.system import Secret

@task
def call_api(endpoint: str, payload: dict) -> dict:
    logger = get_run_logger()
    base_url = Secret.load("my-api-base-url").get()  # or env var
    response = httpx.post(
        f"{base_url}{endpoint}",
        json=payload,
        headers={"Content-Type": "application/json"},
    )
    logger.info(response.text)
    response.raise_for_status()
    return response.json()
```

### SparkSubmitOperator → ShellOperation

```python
# Source: STACK.md research + prefect-shell docs
# Before (Airflow):
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

spark_job = SparkSubmitOperator(
    task_id="run_spark",
    application="/opt/spark/jobs/etl.py",
    conn_id="spark_default",
    conf={"spark.sql.shuffle.partitions": "200"},
    deploy_mode="cluster",
    executor_memory="4g",
)

# After (Prefect) — Option 1: spark-submit via ShellOperation:
from prefect_shell import ShellOperation
from prefect import task

@task
def run_spark_job(application: str):
    result = ShellOperation(
        commands=[
            f"spark-submit "
            f"--conf spark.sql.shuffle.partitions=200 "
            f"--deploy-mode cluster "
            f"--executor-memory 4g "
            f"{application}"
        ],
        stream_output=True,
    ).run()
    return result

# After (Prefect) — Option 2: Managed Spark via Databricks (preferred if available):
# Use DatabricksSubmitRun with a spark_python_task instead
```

### SSHOperator → paramiko in @task

```python
# Source: STACK.md research
# Before (Airflow):
from airflow.providers.ssh.operators.ssh import SSHOperator

ssh_task = SSHOperator(
    task_id="run_remote",
    ssh_conn_id="my_ssh_server",
    command="cd /data && python process.py",
)

# After (Prefect):
import paramiko
from prefect import task
from prefect.blocks.system import Secret

@task
def run_remote_command(host: str, username: str, command: str) -> str:
    # Before running: create a Secret block named "ssh-private-key" with key contents
    private_key_str = Secret.load("ssh-private-key").get()
    private_key = paramiko.RSAKey.from_private_key_file(private_key_str)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, username=username, pkey=private_key)

    stdin, stdout, stderr = client.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()
    output = stdout.read().decode()
    client.close()

    if exit_status != 0:
        raise RuntimeError(f"SSH command failed: {stderr.read().decode()}")
    return output
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `KubernetesExecutor` (cluster-wide K8s) | Per-flow Kubernetes work pool with base job template | Prefect 2.x → 3.x | Work pools are more granular and don't require a cluster-wide executor setting |
| `DatabricksSubmitRunOperator` with polling loop | `prefect-databricks` tasks with built-in polling | prefect-databricks 0.2+ | No custom polling loop needed |
| `requests` for HTTP calls | `httpx` (preferred in Prefect docs) | Prefect 2.x adoption | `httpx` supports async, better timeout control |
| Hardcoded credentials in Airflow connections DB | Prefect `Secret` block or integration-specific block | Core to Prefect design | All credential management must be explicit at block-creation time |

**Deprecated/outdated:**
- `KubernetesPodOperator` with `in_cluster=True` → Not a valid Prefect analog; the work pool handles cluster context
- `ssh_conn_id` string references → Must become explicit `paramiko.SSHClient` or `fabric.Connection` calls

## Open Questions

1. **`prefect-databricks` task names in v0.6+**
   - What we know: STACK.md documents `DatabricksSubmitRun` and `DatabricksJobRunNow`; the `jobs_runs_submit` and `jobs_run_now` function names come from the package's generated client
   - What's unclear: The exact function import paths may differ across `prefect-databricks` minor versions
   - Recommendation: Verify import paths against the current package before authoring. Use `search_prefect_docs` to confirm: `lookup_concept("prefect-databricks")` or read package `__init__.py` if available

2. **Kubernetes work pool base job template format**
   - What we know: `image`, `env_vars`, and `resource requests/limits` map to the base job template
   - What's unclear: The exact YAML/JSON structure of the base job template varies across `prefect-kubernetes` versions
   - Recommendation: The Colin entry should describe the concept (infrastructure-in-work-pool), not the exact template syntax. Instruct LLMs to consult Prefect docs for template format.

3. **`paramiko` vs `fabric` recommendation**
   - What we know: Both libraries work; `fabric` is higher-level
   - What's unclear: `fabric` has had API instability in 2.x vs 3.x migrations
   - Recommendation: Document both; suggest `paramiko` as the baseline (more stable API surface) and note `fabric` as a higher-level option

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing, 60 tests passing) |
| Config file | `pyproject.toml` (pytest section) |
| Quick run command | `uv run pytest tests/test_knowledge.py tests/test_lookup.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| KNOW-01 | `lookup_concept("KubernetesPodOperator")` returns `status: found` with Kubernetes work pool guidance | unit (integration) | `uv run pytest tests/test_knowledge.py -k "kubernetes" -x` | ❌ Wave 0 |
| KNOW-02 | `lookup_concept("DatabricksSubmitRunOperator")` returns `status: found` with prefect-databricks guidance | unit (integration) | `uv run pytest tests/test_knowledge.py -k "databricks" -x` | ❌ Wave 0 |
| KNOW-03 | `lookup_concept("DatabricksRunNowOperator")` returns `status: found` with prefect-databricks guidance | unit (integration) | `uv run pytest tests/test_knowledge.py -k "databricks" -x` | ❌ Wave 0 |
| KNOW-04 | `lookup_concept("SparkSubmitOperator")` returns `status: found` with ShellOperation or Databricks guidance | unit (integration) | `uv run pytest tests/test_knowledge.py -k "spark" -x` | ❌ Wave 0 |
| KNOW-05 | `lookup_concept("SimpleHttpOperator")` returns `status: found` with httpx guidance | unit (integration) | `uv run pytest tests/test_knowledge.py -k "http" -x` | ❌ Wave 0 |
| KNOW-06 | `lookup_concept("SSHOperator")` returns `status: found` with paramiko/Secret block guidance | unit (integration) | `uv run pytest tests/test_knowledge.py -k "ssh" -x` | ❌ Wave 0 |

All KNOW-* requirements are tested by loading the compiled Colin output JSON and calling `lookup_concept` for each operator name. Tests should assert `status == "found"` and `source == "colin"` (not "fallback"). This confirms the Colin model compiled and the operator name is recognized.

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_knowledge.py tests/test_lookup.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before planning the next phase

### Wave 0 Gaps

The following test additions are needed before or during implementation:

- [ ] `tests/test_knowledge.py` — add parametrized test: `@pytest.mark.parametrize("operator", ["KubernetesPodOperator", "DatabricksSubmitRunOperator", "DatabricksRunNowOperator", "SparkSubmitOperator", "SimpleHttpOperator", "SSHOperator"])` that loads actual Colin output and asserts each operator is found with `source == "colin"`
- [ ] `tests/fixtures/` — add `operators-kubernetes.json`, `operators-databricks.json`, `operators-http.json`, `operators-spark.json`, `operators-sftp.json` (compiled output; generated by `colin run` after authoring)

The existing test infrastructure (pytest, conftest.py, `tmp_path` fixture pattern) covers all needed mechanics. No new frameworks needed.

## Sources

### Primary (HIGH confidence)

- `/Users/gcoyne/src/prefect/airflow-unfactor/.planning/research/STACK.md` — verified operator-to-package mappings for all six KNOW-* operators
- `/Users/gcoyne/src/prefect/airflow-unfactor/.planning/research/ARCHITECTURE.md` — Colin model file format, build pipeline, tiered lookup architecture
- `/Users/gcoyne/src/prefect/airflow-unfactor/colin/models/operators/aws.md` — canonical reference for Colin model section format
- `/Users/gcoyne/src/prefect/airflow-unfactor/colin/output/operators-core.json` — verified JSON schema produced by `colin run`
- `/Users/gcoyne/src/prefect/airflow-unfactor/colin/colin.toml` — build configuration confirming output format and provider configuration
- Prefect Official Migration Guide (docs.prefect.io/v3/how-to-guides/migrate/airflow) — concept-level mappings for all six operators
- Prefect Integrations Index (docs.prefect.io/integrations) — package names confirmed: `prefect-kubernetes`, `prefect-databricks`, `prefect-shell`

### Secondary (MEDIUM confidence)

- Astronomer State of Airflow 2025 — KubernetesPodOperator production frequency (~64% enterprise installations)
- Apache Airflow Providers Index — verified module paths for all six operators

### Tertiary (LOW confidence)

- `prefect-databricks` exact function signatures (`jobs_runs_submit`, `jobs_run_now`) — not independently verified against current package source; flag for implementation verification

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — package names and operator mappings verified against official Airflow + Prefect docs
- Architecture: HIGH — Colin model format verified against 5 existing model files; JSON output schema verified
- Pitfalls: HIGH for credential migration and KubernetesPodOperator architecture (both well-documented in Prefect migration guide); MEDIUM for `prefect-databricks` exact API surface (needs implementation-time verification)

**Research date:** 2026-02-26
**Valid until:** 2026-04-26 (stable integration packages; verify `prefect-databricks` API if planning > 30 days out)

# Phase 04: Validation Hardening - Research

**Researched:** 2026-02-26
**Domain:** MCP tool output enhancement + pytest fixture authoring
**Confidence:** HIGH

## Summary

Phase 4 has a narrow, well-scoped task: extend the `validate` tool's `comparison_guidance` string to include operator-type-specific checklist items, and author fixture DAGs for the six new operator families (Kubernetes, Databricks, Azure, dbt, HTTP, SSH) so the test suite can verify both the guidance and the fixtures.

The current `comparison_guidance` in `src/airflow_unfactor/tools/validate.py` is a single static string with nine universal checklist items. It has no awareness of which operator types appear in the original DAG. The success criteria require that calling `validate` on a Kubernetes-origin flow returns a Kubernetes-specific checklist item, and likewise for Databricks. This means the tool must inspect the DAG source and inject operator-specific guidance items conditionally.

The test suite already has a clear pattern established by `TestPhase3Integration` in `tests/test_knowledge.py`: use `load_knowledge` against the real `colin/output/` directory, call `lookup()` on operator names, and assert on content strings in the JSON result. Phase 4 needs the same style of integration test class for `validate_conversion`. Fixture DAGs for the six operator types do not currently exist in `tests/fixtures/` — all current fixtures use only `PythonOperator` and `BashOperator`. New fixture files must be authored as minimal but realistic production-style DAGs.

The implementation work splits cleanly into two tasks: (1) modify `validate_conversion` to detect operator types in the source and append conditional guidance, and (2) add fixture DAGs and a `TestPhase4Validation` integration test class. No external libraries are needed. The only dependency is Python's built-in string search (or `re`) for operator-type detection.

**Primary recommendation:** Detect operator families via substring search in the original DAG source, append type-specific guidance lines to `comparison_guidance`, and pair each new operator fixture with a parametrized test asserting the expected guidance item appears in the result.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VALD-01 | Expand validate tool `comparison_guidance` checklist for Kubernetes, Databricks, Azure, dbt, HTTP, SSH operator types | `validate_conversion` currently returns a static 9-item string; must be made conditional on DAG content |
| VALD-02 | Test against real-world production-style DAGs covering all new operator types | Six fixture DAGs must be authored; `TestPhase4Validation` integration class must cover all six |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `re` / `str` | stdlib | Operator-type detection in DAG source | No new dependencies; detection only needs substring presence |
| `pytest` | current (project uses it) | Test framework | Already used throughout; 136 tests pass |
| `pytest.mark.parametrize` | same | Table-driven fixture/guidance tests | Already the pattern in TestPhase3Integration |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `json` | stdlib | Result parsing in tests | Already used in `test_validate.py` |
| `asyncio` | stdlib | Running async `validate_conversion` in sync tests | Already used in `test_validate.py` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Substring / `re` detection | AST parse to find `import` or class instantiation | AST is heavier and adds complexity; per CLAUDE.md "No AST intermediary" |
| Static string | Dynamic template or f-string assembly | f-string per detected operator type is the right middle ground |

**Installation:** No new packages required.

## Architecture Patterns

### Recommended Project Structure

No new source directories needed. Changes touch:

```
src/airflow_unfactor/tools/validate.py   # Add operator detection + conditional guidance
tests/test_validate.py                   # Add TestPhase4Validation class
tests/fixtures/
├── kubernetes_pod_operator.py           # New fixture
├── databricks_submit_run.py             # New fixture
├── azure_data_factory.py                # New fixture
├── dbt_cloud_run_job.py                 # New fixture
├── http_operator.py                     # New fixture
└── ssh_operator.py                      # New fixture
```

### Pattern 1: Conditional Guidance Injection

**What:** Detect operator families by searching the original DAG source for known class names, then append operator-specific checklist items to the base `comparison_guidance` string.

**When to use:** Every call to `validate_conversion` — detection is O(n) string search and negligible cost.

**Example:**

```python
# In validate_conversion, after building base guidance:
extra = []

if "KubernetesPodOperator" in original_source:
    extra.append(
        "10. Kubernetes: verify a Kubernetes work pool is configured; "
        "image, namespace, and env_vars map to the Prefect infrastructure block"
    )

if any(x in original_source for x in ("DatabricksSubmitRunOperator", "DatabricksRunNowOperator")):
    extra.append(
        "11. Databricks: verify prefect-databricks is installed, "
        "DatabricksCredentials block is configured, and job parameters are mapped"
    )

if any(x in original_source for x in ("AzureDataFactoryRunPipelineOperator", "WasbOperator", "WasbDeleteOperator")):
    extra.append(
        "12. Azure: verify prefect-azure is installed and AzureDataFactoryCredentials / "
        "AzureBlobStorageCredentials block is configured"
    )

if "DbtCloudRunJobOperator" in original_source:
    extra.append(
        "13. dbt Cloud: verify prefect-dbt is installed, DbtCloudCredentials block is set, "
        "and job ID and account ID are passed to trigger_dbt_cloud_job_run_and_wait_for_completion"
    )

if any(x in original_source for x in ("SimpleHttpOperator", "HttpOperator")):
    extra.append(
        "14. HTTP: verify httpx is used (no prefect-http package exists), "
        "connection ID maps to base_url, and headers/auth are passed explicitly"
    )

if "SSHOperator" in original_source:
    extra.append(
        "15. SSH: verify paramiko or fabric is used, SSH credentials are in a Prefect Secret block, "
        "and the host/user/key are not hardcoded"
    )

if extra:
    guidance = guidance + "\n" + "\n".join(extra)
```

### Pattern 2: Fixture DAG Style

**What:** Minimal but realistic DAGs for each operator type. Each fixture should include: a DAG definition with `schedule_interval`, at least one operator instance with realistic parameters (not just `task_id="x"`), and a dependency chain of two tasks to exercise dependency checking.

**When to use:** One fixture per operator family. Do not add every parameter variant — just enough to be "production-style" per the success criteria.

**Example — Kubernetes fixture:**

```python
# tests/fixtures/kubernetes_pod_operator.py
from datetime import datetime
from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator

with DAG(
    dag_id="kubernetes_ml_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule_interval="@daily",
    catchup=False,
) as dag:
    train = KubernetesPodOperator(
        task_id="train_model",
        name="train-model-pod",
        namespace="ml-jobs",
        image="my-registry/ml-trainer:latest",
        env_vars={"EPOCHS": "10", "BATCH_SIZE": "32"},
        get_logs=True,
    )
    evaluate = KubernetesPodOperator(
        task_id="evaluate_model",
        name="evaluate-model-pod",
        namespace="ml-jobs",
        image="my-registry/ml-evaluator:latest",
        env_vars={"MODEL_PATH": "/models/latest"},
    )
    train >> evaluate
```

### Pattern 3: Integration Test Class

**What:** A `TestPhase4Validation` class that parametrizes over `(fixture_path, expected_guidance_fragment)` pairs.

**Example:**

```python
# In tests/test_validate.py
import asyncio
import json
from pathlib import Path
import pytest
from airflow_unfactor.tools.validate import validate_conversion

FIXTURES_DIR = Path(__file__).parent / "fixtures"

class TestPhase4Validation:
    """VALD-01 + VALD-02: operator-specific guidance and production-style fixture DAGs."""

    @pytest.mark.parametrize("fixture_name,expected_fragment", [
        ("kubernetes_pod_operator.py", "Kubernetes work pool"),
        ("databricks_submit_run.py", "prefect-databricks"),
        ("azure_data_factory.py", "prefect-azure"),
        ("dbt_cloud_run_job.py", "prefect-dbt"),
        ("http_operator.py", "httpx"),
        ("ssh_operator.py", "Secret block"),
    ])
    def test_operator_specific_guidance(self, fixture_name, expected_fragment):
        """validate_conversion returns operator-specific checklist items."""
        dag_source = (FIXTURES_DIR / fixture_name).read_text()
        flow_stub = "from prefect import flow\n\n@flow\ndef stub(): pass"
        result = json.loads(asyncio.run(validate_conversion(dag_source, flow_stub)))
        guidance = result["comparison_guidance"]
        assert expected_fragment in guidance, (
            f"Expected '{expected_fragment}' in guidance for {fixture_name};\n"
            f"Got: {guidance}"
        )
```

### Anti-Patterns to Avoid

- **Detecting operators via import path only:** `from airflow.providers.cncf.kubernetes...` is correct but some DAGs use `from airflow.contrib.operators.kubernetes_pod_operator import KubernetesPodOperator` (older Airflow 2.x path). Check for the class name `KubernetesPodOperator` directly, not the import path.
- **Hardcoding item numbers in guidance:** If a DAG contains multiple new operator types, item numbers will conflict. Use descriptive labels ("Kubernetes:", "Databricks:") instead of sequential numbers, or append without numbering.
- **Making guidance detection case-sensitive on class names:** Airflow class names are stable and PascalCase — case-sensitive search is fine and faster.
- **Overly complex fixtures:** Fixtures should be readable in 30 seconds. No custom operator classes, no TaskFlow API decorators, no dynamic task mapping in the Phase 4 fixtures.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Operator detection | Custom AST visitor | `str.__contains__` / `re.search` | Per CLAUDE.md convention; raw source is what we have |
| Async test execution | Custom event loop | `asyncio.run()` | Already used in `test_validate.py`; simple and correct |
| Fixture parametrization | Separate test methods per fixture | `pytest.mark.parametrize` | Established pattern in `TestPhase3Integration` |

**Key insight:** The detection problem is simpler than it looks. We do not need to know if the operator is actually imported and used — if the class name appears anywhere in the source, the guidance is relevant. False positives (guidance shown when operator is only in a comment) are harmless.

## Common Pitfalls

### Pitfall 1: Guidance Item Conflicts With Base Checklist

**What goes wrong:** The base checklist items 1-9 use numbered format. If extra items append as "10.", "11.", etc., a DAG with three new operator types produces out-of-order or duplicate numbers.

**Why it happens:** The base string was written for a single, fixed number of items.

**How to avoid:** Append items without numbering, or prefix with the operator family name ("Kubernetes:", "Databricks:") so each item is self-identifying regardless of order.

**Warning signs:** Test assertions on `"10."` in guidance string — these are fragile.

### Pitfall 2: Test Assumes Path, Not Content

**What goes wrong:** `validate_conversion` supports both file paths and inline content. The existing test `test_valid_pair_by_path` uses paths via `tmp_path`. Integration tests for Phase 4 should pass inline content (the fixture file read as a string) so the test does not depend on absolute paths in CI.

**Why it happens:** Copy-paste from the path-based test pattern.

**How to avoid:** Read fixture file to string with `.read_text()`, pass the string directly to `validate_conversion`. Use a minimal stub for the converted flow (syntax valid Python is all that's needed).

**Warning signs:** Tests that write `tmp_path / "dag.py"` when the fixture already exists in `tests/fixtures/`.

### Pitfall 3: SSH Operator Import Path Ambiguity

**What goes wrong:** The colin output file is `operators-sftp.json` and contains `SSHOperator`. The detection string should be `"SSHOperator"`, not `"SFTPOperator"` or anything from the file name. The operators-sftp.json key is `SSHOperator`.

**Why it happens:** The file is named for SFTP but the operator is SSH — easy to mix up.

**How to avoid:** Verify against `colin/output/operators-sftp.json` keys: the key is `SSHOperator`.

**Warning signs:** Guidance fires on `"SFTP"` but misses `"SSHOperator"`.

### Pitfall 4: Databricks — Two Operator Names

**What goes wrong:** Only checking for `DatabricksSubmitRunOperator` and missing `DatabricksRunNowOperator` — or vice versa.

**Why it happens:** Two operators map to one guidance item.

**How to avoid:** Use `any(x in original_source for x in ("DatabricksSubmitRunOperator", "DatabricksRunNowOperator"))`.

**Warning signs:** A fixture using `DatabricksRunNowOperator` passes guidance detection but one using `DatabricksSubmitRunOperator` does not (or vice versa).

### Pitfall 5: Existing Test Regression

**What goes wrong:** `test_comparison_guidance_content` in `TestValidateConversion` asserts specific strings exist in guidance. Adding conditional logic must not break those assertions on the simple `x=1 / y=2` case.

**Why it happens:** The extra lines are only appended when operators are detected; a minimal DAG with no new operators should return unchanged base guidance.

**How to avoid:** Confirm the base 9-item guidance remains unchanged for DAGs with no new operators. Run `uv run pytest tests/test_validate.py -x` after any change.

## Code Examples

Verified patterns from existing codebase:

### Existing validate_conversion return structure

```python
# Source: src/airflow_unfactor/tools/validate.py (current)
return json.dumps(
    {
        "original_source": original_source,
        "converted_source": converted_source,
        "syntax_valid": syntax_result.valid,
        "syntax_errors": syntax_errors,
        "comparison_guidance": (
            "Compare the original Airflow DAG with the generated Prefect flow. Verify:\n"
            "1. All tasks from the DAG are represented in the flow\n"
            ...
            "9. Trigger rules are handled with state inspection"
        ),
    },
    indent=2,
)
```

**Change needed:** Build `guidance` as a variable, append conditional items, then include in dict.

### Existing async test pattern

```python
# Source: tests/test_validate.py (current)
result = json.loads(asyncio.run(validate_conversion(str(dag), str(flow))))
# OR with inline content:
result = json.loads(asyncio.run(validate_conversion(dag_code, flow_code)))
```

### Existing parametrize pattern

```python
# Source: tests/test_knowledge.py (TestPhase3Integration)
@pytest.mark.parametrize("operator_name,expected_content", [
    ("AzureDataFactoryRunPipelineOperator", "ARCHITECTURE SHIFT"),
    ("WasbOperator", "AzureBlobStorageCredentials"),
    ("DbtCloudRunJobOperator", "trigger_dbt_cloud_job_run_and_wait_for_completion"),
])
def test_phase3_operator_lookup(self, operator_name, expected_content):
    ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Static comparison_guidance | Conditional per operator type | Phase 4 (this phase) | LLM gets targeted guidance instead of generic checklist |

**Deprecated/outdated:**

- Nothing in the Python stdlib or pytest ecosystem requires updating for this phase.

## Open Questions

1. **Should HTTP guidance distinguish `SimpleHttpOperator` from `HttpOperator`?**
   - What we know: Both map to the same httpx pattern per `operators-http.json`. The colin output keys are `SimpleHttpOperator` and `HttpOperator`.
   - What's unclear: Whether slightly different guidance (e.g., auth handling) is needed per variant.
   - Recommendation: Use a single shared guidance item for both — the httpx pattern is the same, and per CLAUDE.md "minimum complexity = correct solution."

2. **Should the guidance show block setup commands or just flag the requirement?**
   - What we know: Blocks are environment-specific (out of scope per REQUIREMENTS.md "Automatic block/secret creation").
   - What's unclear: Whether a command snippet (e.g., `prefect block register -m prefect_databricks`) improves LLM guidance.
   - Recommendation: Flag the requirement ("verify prefect-databricks block is configured") without prescribing commands. Keeps guidance stable across Prefect versions.

3. **SparkSubmitOperator: include or not?**
   - What we know: Phase 1 includes `SparkSubmitOperator` (KNOW-04) with `operators-spark.json` output. But the success criteria explicitly list Kubernetes, Databricks, Azure, dbt, HTTP, SSH — Spark is not listed.
   - What's unclear: Whether Spark guidance should be added anyway.
   - Recommendation: Do NOT add Spark guidance in Phase 4. The success criteria are the definition of done; adding Spark would be scope creep. It can be a follow-on.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (current) |
| Config file | none detected — runs with `uv run pytest` |
| Quick run command | `uv run pytest tests/test_validate.py -x -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VALD-01 | `validate` on Kubernetes DAG returns Kubernetes work pool guidance | integration | `uv run pytest tests/test_validate.py::TestPhase4Validation -x -q` | No — Wave 0 |
| VALD-01 | `validate` on Databricks DAG returns prefect-databricks block guidance | integration | same | No — Wave 0 |
| VALD-01 | `validate` on Azure DAG returns prefect-azure guidance | integration | same | No — Wave 0 |
| VALD-01 | `validate` on dbt DAG returns prefect-dbt guidance | integration | same | No — Wave 0 |
| VALD-01 | `validate` on HTTP DAG returns httpx guidance | integration | same | No — Wave 0 |
| VALD-01 | `validate` on SSH DAG returns Secret block guidance | integration | same | No — Wave 0 |
| VALD-02 | Fixture DAGs exist for all six operator types and read without error | fixture | `uv run pytest tests/test_validate.py::TestPhase4Validation -x -q` | No — Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_validate.py -x -q`
- **Per wave merge:** `uv run pytest -q`
- **Phase gate:** Full suite green (136+ tests) before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/fixtures/kubernetes_pod_operator.py` — covers VALD-02 (Kubernetes fixture)
- [ ] `tests/fixtures/databricks_submit_run.py` — covers VALD-02 (Databricks fixture)
- [ ] `tests/fixtures/azure_data_factory.py` — covers VALD-02 (Azure fixture)
- [ ] `tests/fixtures/dbt_cloud_run_job.py` — covers VALD-02 (dbt fixture)
- [ ] `tests/fixtures/http_operator.py` — covers VALD-02 (HTTP fixture)
- [ ] `tests/fixtures/ssh_operator.py` — covers VALD-02 (SSH fixture)
- [ ] `TestPhase4Validation` class in `tests/test_validate.py` — covers VALD-01 + VALD-02
- [ ] Conditional guidance logic in `src/airflow_unfactor/tools/validate.py` — covers VALD-01

## Sources

### Primary (HIGH confidence)

- Codebase: `src/airflow_unfactor/tools/validate.py` — current guidance string and return structure (read directly)
- Codebase: `tests/test_validate.py` — existing test patterns (read directly)
- Codebase: `tests/test_knowledge.py` (TestPhase3Integration) — parametrize pattern to replicate (read directly)
- Codebase: `colin/output/operators-*.json` — confirms operator class names for detection strings (read directly)
- Codebase: `tests/conftest.py` — fixture infrastructure (read directly)
- Project: `.planning/REQUIREMENTS.md` — VALD-01, VALD-02 exact definitions (read directly)

### Secondary (MEDIUM confidence)

- None required — all critical findings come from direct codebase inspection.

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — stdlib only; existing pytest already in use
- Architecture patterns: HIGH — directly derived from existing codebase patterns
- Pitfalls: HIGH — derived from reading current source and tests; not speculative
- Fixture content: MEDIUM — "realistic production-style" is somewhat subjective; fixtures need enough realistic parameters to satisfy the success criteria description

**Research date:** 2026-02-26
**Valid until:** 2026-03-28 (stable domain — no external API dependencies)

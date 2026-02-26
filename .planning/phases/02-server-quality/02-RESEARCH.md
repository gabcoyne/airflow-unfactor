# Phase 2: Server Quality - Research

**Researched:** 2026-02-26
**Domain:** Python stdlib (difflib, logging, pathlib), knowledge.py internals, FastMCP lifespan
**Confidence:** HIGH

## Summary

Phase 2 addresses four tightly scoped improvements to `knowledge.py` and server startup behavior. All four requirements operate entirely within the existing Python stdlib — no new dependencies are needed. The work falls into two categories: (1) observability — emitting warnings when the server can't do its job well (SRVR-01, SRVR-04), and (2) quality of results — better fuzzy matching (SRVR-02) and wider fallback coverage (SRVR-03).

The current `suggestions()` function in `knowledge.py` scores candidates by counting shared characters (`sum(1 for c in lower if c in key_lower)`). This is a set-membership count, not a similarity ratio, and is easily fooled by short common letters. `difflib.SequenceMatcher` computes the Ratcliff/Obershelp ratio — the fraction of matching characters considering longest contiguous runs — which is well-suited to operator name typos ("KubernetesPodOp" → ratio 0.83 with "KubernetesPodOperator"). `difflib.get_close_matches` wraps SequenceMatcher with a configurable cutoff and n-limit, making it a direct replacement for the current manual scoring loop.

The startup warning (SRVR-01) belongs in `main()` in `server.py`, not at import time and not in a lifespan hook. `main()` is the earliest observable moment before `mcp.run()` and gives clear guidance to operators without requiring FastMCP lifecycle machinery. The JSON parse error logging (SRVR-04) is a one-line change in the `except` block of `load_knowledge()` that replaces the silent `continue` with `logger.warning(f"Failed to parse {json_file.name}: {e}")`.

**Primary recommendation:** Make all four changes to `knowledge.py` and `server.py` using only stdlib — no third-party fuzzy-match libraries — and add focused unit tests for each behavior.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SRVR-01 | Startup warning when Colin output directory is missing or empty with instructions to run `colin run` | Place check in `main()` before `mcp.run()`; use `logging.warning()` or `print(..., file=sys.stderr)`; detect via `Path.exists()` and `list(Path.glob("*.json"))` being empty |
| SRVR-02 | Replace character-overlap suggestion algorithm with `difflib.SequenceMatcher` | Drop current `suggestions()` body; use `difflib.get_close_matches(query, candidates, n=5, cutoff=0.4)` — verified to return `["KubernetesPodOperator"]` for input `"KubernetesPodOp"` |
| SRVR-03 | Expand FALLBACK_KNOWLEDGE from 6 to ~15-20 highest-frequency operator entries | Add ShortCircuitOperator, BranchPythonOperator, EmptyOperator/DummyOperator, EmailOperator, TriggerDagRunOperator, ExternalTaskSensor, FileSensor, S3KeySensor, PythonSensor to bring total to ~15 |
| SRVR-04 | Log warnings when Colin JSON files fail to parse (include filename and error type) | Change `except (json.JSONDecodeError, KeyError): continue` to `except (json.JSONDecodeError, KeyError) as e: logger.warning(f"Failed to parse {json_file.name}: {type(e).__name__}: {e}"); continue` |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `difflib` | stdlib | Fuzzy sequence matching via SequenceMatcher / get_close_matches | Ships with Python; no dep; Ratcliff-Obershelp algorithm is well-suited to identifier typos |
| `logging` | stdlib | Warning emission for SRVR-01 and SRVR-04 | Existing pattern in Python ecosystem; structurally better than print() for library code |
| `pathlib.Path` | stdlib | Directory existence and emptiness check | Already used in knowledge.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sys.stderr` | stdlib | Alternative for SRVR-01 if logging feels too heavy for a startup warning | Acceptable for CLI-style servers; logging preferred for consistency |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `difflib.get_close_matches` | `rapidfuzz` / `fuzzywuzzy` | Third-party libs offer Levenshtein distance which is marginally better for short strings, but `difflib` is zero-dependency and sufficient for operator name typos |
| `logging.warning()` | `warnings.warn()` | `warnings.warn()` is for deprecation notices; `logging.warning()` is correct for operational conditions |

**Installation:** No new packages needed. All stdlib.

## Architecture Patterns

### Recommended Project Structure
No structural changes needed. All edits are within:
```
src/airflow_unfactor/
├── knowledge.py     # SRVR-02, SRVR-03, SRVR-04 changes
└── server.py        # SRVR-01 startup warning in main()
```

### Pattern 1: Logger Setup (module-level)
**What:** Define a module-level logger rather than using the root logger. This keeps log messages namespaced and controllable by callers.
**When to use:** In any module that needs to emit warnings.
**Example:**
```python
import logging

logger = logging.getLogger(__name__)

# Then in load_knowledge():
logger.warning("Colin output directory missing or empty: %s. Run `colin run` to compile translation knowledge.", colin_output_dir)
```

### Pattern 2: difflib.get_close_matches Replacement
**What:** Replace the manual scored list with a single `difflib.get_close_matches` call.
**When to use:** Anywhere a "did you mean?" style suggestion is needed over a known vocabulary.
**Example:**
```python
# Source: Python 3.11 stdlib difflib
import difflib

def suggestions(query: str, knowledge: dict[str, Any]) -> list[str]:
    all_keys = list(knowledge.keys()) + list(FALLBACK_KNOWLEDGE.keys())
    seen: set[str] = set()
    unique_keys: list[str] = []
    for k in all_keys:
        if k not in seen:
            seen.add(k)
            unique_keys.append(k)
    return difflib.get_close_matches(query, unique_keys, n=5, cutoff=0.4)
```

Verified behavior:
- `"KubernetesPodOp"` → `["KubernetesPodOperator"]` (ratio 0.83, well above cutoff 0.4)
- `"pythonoperator"` → `["PythonOperator"]` (ratio 0.86)
- `"CompletelyUnknown"` → `[]` (no false positives)

### Pattern 3: Startup Warning in main()
**What:** Check for missing/empty Colin output before starting the MCP server.
**When to use:** In the CLI entry point, after argument validation and before server start.
**Example:**
```python
def main() -> None:
    """Run the MCP server over stdio."""
    import sys
    from pathlib import Path

    if len(sys.argv) > 1:
        print(f"error: unrecognized arguments: {' '.join(sys.argv[1:])}", file=sys.stderr)
        sys.exit(2)

    # SRVR-01: warn if Colin output is missing or empty
    colin_dir = Path("colin/output")
    if not colin_dir.exists() or not list(colin_dir.glob("*.json")):
        import logging
        logging.getLogger("airflow_unfactor").warning(
            "Colin output directory missing or empty (%s). "
            "Run `colin run` to compile translation knowledge. "
            "Falling back to built-in operator mappings.",
            colin_dir,
        )

    mcp.run()
```

### Pattern 4: JSON Parse Warning in load_knowledge()
**What:** Replace `continue` with a logged warning that identifies the failing file.
**Example:**
```python
except (json.JSONDecodeError, KeyError) as e:
    logger.warning("Failed to parse %s: %s: %s", json_file.name, type(e).__name__, e)
    continue
```

`json.JSONDecodeError.msg`, `.lineno`, `.colno` are available but `str(e)` already includes all that context, so `str(e)` is sufficient.

### Anti-Patterns to Avoid
- **Silent failure on `continue`:** The current code swallows parse errors with no log output. Operators cannot diagnose corrupt or hand-edited JSON files.
- **Module-level warning for SRVR-01:** Emitting the warning at import time means it fires during tests even when Colin output is intentionally absent. `main()` is the correct location.
- **Using `warnings.warn()` for operational state:** `warnings.warn()` is for deprecating APIs, not for signaling missing runtime dependencies. Use `logging.warning()`.
- **cutoff too low for `get_close_matches`:** A cutoff below 0.3 produces noisy false-positive suggestions. A cutoff of 0.4 eliminates false positives while preserving the "KubernetesPodOp" → "KubernetesPodOperator" match.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fuzzy string similarity | Custom character-counting scoring | `difflib.get_close_matches` | SequenceMatcher uses Ratcliff-Obershelp; handles contiguous block matching, autojunk filtering — the custom approach counts individual chars and misranks short-letter-overlap coincidences |
| Operator name typo detection | Edit-distance loop | `difflib.get_close_matches(query, keys, n=5, cutoff=0.4)` | One line, no deps, correct behavior verified empirically |

**Key insight:** `difflib` is in stdlib specifically because "did you mean X?" suggestions are a common need. Every hand-rolled character counting approach mishandles edge cases that SequenceMatcher handles internally.

## Common Pitfalls

### Pitfall 1: Startup Warning Fires During Tests
**What goes wrong:** If the warning is emitted at module import time or inside `load_knowledge()`, every test that loads knowledge with an empty directory will produce spurious warning output.
**Why it happens:** `load_knowledge()` is called per-lookup, not only at server startup.
**How to avoid:** Place the SRVR-01 check exclusively in `main()`. Tests call `load_knowledge()` directly and never call `main()`.
**Warning signs:** Test output contains "Colin output directory missing" messages during the existing test suite.

### Pitfall 2: get_close_matches Case Sensitivity
**What goes wrong:** `difflib.get_close_matches("kubernetesPodOp", ["KubernetesPodOperator"])` may not match if case differs.
**Why it happens:** SequenceMatcher is case-sensitive by default.
**How to avoid:** Lowercase both query and candidates before calling `get_close_matches`, then return the original-case candidates.

```python
lower_query = query.lower()
lower_to_orig = {k.lower(): k for k in unique_keys}
lower_keys = list(lower_to_orig.keys())
close = difflib.get_close_matches(lower_query, lower_keys, n=5, cutoff=0.4)
return [lower_to_orig[k] for k in close]
```

### Pitfall 3: FALLBACK_KNOWLEDGE Entries Need Minimal Required Fields
**What goes wrong:** Adding operator entries without `concept_type`, `airflow`, or `prefect_equivalent` fields causes downstream consumers (the LLM) to receive incomplete guidance.
**Why it happens:** There's no schema validation on FALLBACK_KNOWLEDGE entries.
**How to avoid:** Use the existing 6 entries as templates. Each new entry needs at minimum: `concept_type`, `airflow.name`/`airflow.description`, `prefect_equivalent.pattern`, and `translation_rules` list.

### Pitfall 4: JSONDecodeError vs KeyError Distinction
**What goes wrong:** The current `except (json.JSONDecodeError, KeyError)` catches both error types but logs the same message. KeyError is a different failure mode (file parsed but missing a required key).
**Why it happens:** Both are lumped together for convenience.
**How to avoid:** Log both but with `type(e).__name__` included so operators can distinguish parse failures from schema failures. `str(e)` already embeds the failing key name for `KeyError`.

## Code Examples

### Complete suggestions() Replacement

```python
# Source: Python stdlib difflib docs + empirical verification 2026-02-26
import difflib

def suggestions(query: str, knowledge: dict[str, Any]) -> list[str]:
    """Generate suggestions for a not-found query using SequenceMatcher.

    Args:
        query: The query that wasn't found.
        knowledge: The loaded knowledge dict.

    Returns:
        List of similar concept names (original case).
    """
    all_keys = list(knowledge.keys()) + list(FALLBACK_KNOWLEDGE.keys())
    seen: set[str] = set()
    unique_keys: list[str] = []
    for k in all_keys:
        if k not in seen:
            seen.add(k)
            unique_keys.append(k)

    # Case-insensitive fuzzy match using SequenceMatcher (Ratcliff-Obershelp)
    lower_query = query.lower()
    lower_to_orig = {k.lower(): k for k in unique_keys}
    lower_keys = list(lower_to_orig.keys())
    close = difflib.get_close_matches(lower_query, lower_keys, n=5, cutoff=0.4)
    return [lower_to_orig[k] for k in close]
```

### load_knowledge() with Warning Logging

```python
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

def load_knowledge(colin_output_dir: str = "colin/output") -> dict[str, Any]:
    output_path = Path(colin_output_dir)
    if not output_path.exists():
        return {}

    knowledge: dict[str, Any] = {}
    for json_file in output_path.glob("*.json"):
        try:
            data = json.loads(json_file.read_text())
            if isinstance(data, dict):
                if "entries" in data and isinstance(data["entries"], list):
                    for entry in data["entries"]:
                        if "name" in entry:
                            knowledge[entry["name"]] = entry
                else:
                    for key, value in data.items():
                        if isinstance(value, dict):
                            knowledge[key] = value
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(
                "Failed to parse %s: %s: %s",
                json_file.name, type(e).__name__, e
            )
            continue

    return knowledge
```

### New FALLBACK_KNOWLEDGE Entries to Add

Minimum viable entry pattern (from existing entries):

```python
"ShortCircuitOperator": {
    "concept_type": "operator",
    "airflow": {"name": "ShortCircuitOperator", "module": "airflow.operators.python"},
    "prefect_equivalent": {
        "pattern": "@task with conditional return + flow control",
        "description": "Return False from a @task to skip downstream steps using Prefect state handling",
    },
    "translation_rules": [
        "Replace ShortCircuitOperator with a @task that returns a bool",
        "Use conditional logic in the @flow to skip downstream tasks when False",
        "Prefect has no built-in short-circuit; implement as: if not check_task(): return",
    ],
},
"BranchPythonOperator": {
    "concept_type": "operator",
    "airflow": {"name": "BranchPythonOperator", "module": "airflow.operators.python"},
    "prefect_equivalent": {
        "pattern": "Python if/else in @flow",
        "description": "Use standard Python branching inside the @flow function",
    },
    "translation_rules": [
        "Replace BranchPythonOperator with an if/else block in the @flow",
        "The python_callable return value (task_id string) becomes the branch condition",
        "No Prefect equivalent needed — Python control flow handles this natively",
    ],
},
"EmptyOperator": {
    "concept_type": "operator",
    "airflow": {"name": "EmptyOperator", "module": "airflow.operators.empty"},
    "prefect_equivalent": {
        "pattern": "Remove or use pass",
        "description": "EmptyOperator/DummyOperator are placeholders with no equivalent needed",
    },
    "translation_rules": [
        "Remove EmptyOperator nodes — they are pure placeholders",
        "If used for dependency wiring, restructure flow task calls directly",
        "DummyOperator is the Airflow <2.4 name for EmptyOperator",
    ],
},
```

Additional entries for DummyOperator, EmailOperator, TriggerDagRunOperator, ExternalTaskSensor, FileSensor, S3KeySensor, PythonSensor follow the same pattern.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `fuzzywuzzy` (Levenshtein) | `difflib.SequenceMatcher` | stdlib has always had it; fuzzywuzzy added only for Levenshtein distance | difflib is zero-dep and sufficient for operator name typos |

**Deprecated/outdated:**
- `fuzzywuzzy`: Superseded by `rapidfuzz` as third-party option, but neither is needed here — `difflib` handles the use case.

## Open Questions

1. **Cutoff threshold for get_close_matches**
   - What we know: cutoff=0.4 correctly matches "KubernetesPodOp" → "KubernetesPodOperator" (ratio 0.83) and returns empty for "CompletelyUnknown"
   - What's unclear: Whether there are realistic typo inputs where 0.4 is too high (missing a valid suggestion) or too low (false positive). Testing with more examples would validate.
   - Recommendation: Use 0.4 as default; add a test with "ShortCircuitOp" → expect "ShortCircuitOperator" to validate.

2. **FALLBACK_KNOWLEDGE canonical list**
   - What we know: Current 6 entries are PythonOperator, BashOperator, XCom, TaskGroup, DAG, postgres_default
   - What's unclear: Exact target list for "~15-20 highest-frequency" — the requirement says ~15-20 but doesn't specify which.
   - Recommendation: Target 15 entries total. Add: ShortCircuitOperator, BranchPythonOperator, EmptyOperator, DummyOperator (alias), EmailOperator, TriggerDagRunOperator, ExternalTaskSensor, FileSensor, PythonSensor. That brings total to 15. S3KeySensor can be added if 15 feels light.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already installed) |
| Config file | none — pytest auto-discovers tests/ |
| Quick run command | `uv run pytest tests/test_knowledge.py tests/test_lookup.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SRVR-01 | `main()` emits warning when colin/output missing | unit | `uv run pytest tests/test_server.py::TestStartupWarning -x` | Wave 0 (new file) |
| SRVR-01 | `main()` emits warning when colin/output empty dir | unit | `uv run pytest tests/test_server.py::TestStartupWarning -x` | Wave 0 (same file) |
| SRVR-02 | `suggestions("KubernetesPodOp", {})` returns ["KubernetesPodOperator"] | unit | `uv run pytest tests/test_knowledge.py::TestSuggestions -x` | Extend existing |
| SRVR-02 | `suggestions` returns empty list for completely unknown string | unit | `uv run pytest tests/test_knowledge.py::TestSuggestions -x` | Extend existing |
| SRVR-03 | `lookup("ShortCircuitOperator", {})` returns found+fallback | unit | `uv run pytest tests/test_knowledge.py::TestLookup -x` | Extend existing |
| SRVR-03 | `lookup("BranchPythonOperator", {})` returns found+fallback | unit | `uv run pytest tests/test_knowledge.py::TestLookup -x` | Extend existing |
| SRVR-04 | `load_knowledge()` logs warning for invalid JSON, includes filename | unit | `uv run pytest tests/test_knowledge.py::TestLoadKnowledge -x` | Extend existing |
| SRVR-04 | `load_knowledge()` continues loading valid files after a bad one | unit | `uv run pytest tests/test_knowledge.py::TestLoadKnowledge -x` | Extend existing |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_knowledge.py tests/test_lookup.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite (66+ tests) green before marking phase complete

### Wave 0 Gaps
- [ ] `tests/test_server.py` — covers SRVR-01 startup warning behavior; does not exist yet

*(All other tests extend existing `tests/test_knowledge.py` — file already exists with correct structure)*

## Sources

### Primary (HIGH confidence)
- Python 3.11 stdlib `difflib` module — `SequenceMatcher`, `get_close_matches` API verified via `uv run python -c "..."` against project's Python 3.11.14
- Python 3.11 stdlib `logging` module — `getLogger`, `warning()` API verified via live execution
- Python 3.11 stdlib `json.JSONDecodeError` — `.msg`, `.lineno`, `.colno`, `str(e)` fields verified via live execution
- FastMCP 3.0.0b2 — `lifespan` parameter and `main()` pattern verified via `inspect.getsource(FastMCP.__init__)`

### Secondary (MEDIUM confidence)
- Airflow 2.x operator frequency ranking (ShortCircuitOperator, BranchPythonOperator, EmptyOperator being "highest-frequency") — based on training knowledge of common production DAG patterns; not independently verified against a corpus

### Tertiary (LOW confidence)
- `cutoff=0.4` as optimal threshold — verified for the specific SRVR-02 test case; broader coverage not tested

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib only, no version ambiguity
- Architecture: HIGH — all changes are contained within two existing files
- Pitfalls: HIGH — identified through live code inspection and empirical test runs
- Fallback operator list: MEDIUM — frequency ranking is training-data based, not corpus-verified

**Research date:** 2026-02-26
**Valid until:** 2026-04-26 (stable stdlib; FastMCP version pinned in project)

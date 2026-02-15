## Context

airflow-unfactor has completed two development phases:
- **P0** (Feb 12): Core conversion bugs—dependency tracking, XCom handling, Jinja2 detection, code validation
- **P1** (Feb 13): Interface-experience—8 new converters, scaffold tool, comprehensive docs

Current state: 524 tests passing, 17 converters, 7 MCP tools. The tool handles most common Airflow patterns but has one critical gap: the `validate` tool is a stub returning `{"valid": true}` regardless of input.

**Stakeholders:**
- Migration engineers using the tool to convert DAGs
- Prefect team maintaining and extending the tool
- Enterprise teams needing confidence in large-scale migrations

**Constraints:**
- Must maintain backward compatibility with existing MCP tool contracts
- No runtime Airflow dependency (static AST parsing only)
- External MCP integrations are optional and should degrade gracefully

## Goals / Non-Goals

**Goals:**
- Implement behavioral validation to verify converted flows match original DAGs
- Expand provider operator coverage from ~15 to 50+ operators
- Create searchable operator coverage documentation
- Add conversion quality metrics for tracking and improvement

**Non-Goals:**
- Runtime execution comparison (would require Airflow installation)
- 100% operator coverage (long tail of exotic operators)
- IDE/language server integration (future phase)
- GUI or web interface

## Decisions

### Decision 1: Validation Approach — Static Graph Comparison

**Choice:** Compare task graphs structurally (task count, names, dependencies) rather than runtime behavior.

**Alternatives considered:**
1. **Runtime execution comparison** — Execute both DAG and flow, compare outputs
   - Rejected: Requires Airflow installation, complex test fixtures, slow
2. **Symbolic execution** — Trace code paths without execution
   - Rejected: Over-engineered for current needs, high complexity
3. **Static graph comparison** — Parse both files, compare structure
   - Selected: Achievable with existing parser, fast, no dependencies

**Rationale:** Users primarily need confidence that task count matches, dependencies are preserved, and no operators were dropped. Static comparison catches 90% of conversion issues without runtime complexity.

**Implementation:**
```python
# Validation checks (priority order):
1. Task count matches (original operators → converted tasks)
2. Dependency graph isomorphism (same edges, possibly renamed nodes)
3. Data flow preserved (XCom patterns → return/parameter patterns)
4. No dropped operators (all original operators have converted equivalent)
5. Warning coverage (known limitations are flagged)
```

### Decision 2: Provider Operator Expansion — Registry Pattern

**Choice:** Expand `OPERATOR_MAPPINGS` dict with categorized entries, generate docs from registry.

**Alternatives considered:**
1. **External config file (YAML/JSON)** — Load mappings from config
   - Rejected: Adds complexity, harder to include code templates
2. **Database/API lookup** — Query operator info at runtime
   - Rejected: Adds external dependency, offline issues
3. **Expanded Python registry** — Keep current pattern, add more entries
   - Selected: Simple, type-safe, code templates inline

**Rationale:** Current registry pattern works well. Adding ~40 more operators is straightforward. Code templates benefit from being Python (syntax highlighting, type checking).

**Categories to expand:**
| Provider | Current | Target | Priority |
|----------|---------|--------|----------|
| AWS | 3 | 15 | P1 |
| GCP | 3 | 12 | P1 |
| Azure | 0 | 8 | P2 |
| Databricks | 0 | 6 | P2 |
| Snowflake | 1 | 4 | P1 |
| dbt | 0 | 3 | P2 |

### Decision 3: Metrics Collection — Optional Module

**Choice:** Create `metrics/` module with optional export, disabled by default.

**Alternatives considered:**
1. **Built-in logging only** — Log conversion stats to stderr
   - Rejected: Hard to aggregate, no persistence
2. **Required metrics service** — Always export to external system
   - Rejected: Adds deployment complexity, privacy concerns
3. **Optional module with export adapters** — Collect in-memory, optional export
   - Selected: Flexible, no runtime cost when disabled

**Metrics to track:**
```python
@dataclass
class ConversionMetrics:
    dag_id: str
    timestamp: datetime
    operators_total: int
    operators_converted: int
    operators_stubbed: int
    warnings_count: int
    validation_passed: bool
    elapsed_ms: int
```

**Export adapters (future):**
- JSON file (local debugging)
- Prometheus (production monitoring)
- Prefect Cloud (if integrated)

### Decision 4: Operator Coverage Matrix — Generated Documentation

**Choice:** Generate `docs/operator-coverage.md` from `OPERATOR_MAPPINGS` registry at build time.

**Alternatives considered:**
1. **Manual documentation** — Hand-write operator tables
   - Rejected: Falls out of sync with code
2. **Runtime API endpoint** — Query coverage via MCP tool
   - Considered for future, but docs are more discoverable
3. **Generated markdown** — Script creates docs from registry
   - Selected: Single source of truth, always accurate

**Format:**
```markdown
# Operator Coverage Matrix

## Supported Operators (52)
| Operator | Prefect Equivalent | Package | Status |
|----------|-------------------|---------|--------|
| S3CreateObjectOperator | S3Bucket.upload | prefect-aws | ✅ Full |

## Partial Support (12)
...

## Not Supported (known)
| Operator | Reason | Workaround |
|----------|--------|------------|
```

## Risks / Trade-offs

### Risk 1: Static validation misses runtime issues
**Impact:** Medium — Users may trust validation but encounter runtime errors
**Mitigation:**
- Clear documentation that validation is structural, not behavioral
- Recommend running generated tests as true validation
- Validation report includes "confidence score" based on pattern complexity

### Risk 2: Provider operator expansion is unbounded
**Impact:** Low — Could spend forever adding operators
**Mitigation:**
- Prioritize by usage frequency (AWS S3, GCP BigQuery most common)
- Accept "unknown operator" stub for long tail
- Community contributions for exotic operators

### Risk 3: Metrics collection has privacy implications
**Impact:** Low — DAG names/structure could be sensitive
**Mitigation:**
- Disabled by default
- Local-only storage unless explicitly configured
- Anonymization option for aggregate metrics

### Risk 4: Generated docs fall out of sync
**Impact:** Medium — Stale docs erode trust
**Mitigation:**
- CI check that generated docs match registry
- Pre-commit hook to regenerate

## Open Questions

1. **Validation confidence scoring** — How to weight different validation checks? Should a missing task be 100% failure or partial score?

2. **Operator priority list** — Which specific operators should be added first? Need usage data or user feedback.

3. **Metrics export format** — OpenTelemetry? Prometheus? Custom JSON? Depends on target deployment environments.

4. **Test generation integration** — Should `validate` tool also generate/run tests, or stay purely structural?

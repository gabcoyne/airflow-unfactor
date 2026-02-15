# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-02-14

### Added

**Core MCP Server**
- FastMCP-based server with 8 migration tools
- `analyze` - DAG structure analysis with complexity scoring
- `convert` - Full DAG-to-flow conversion with test generation
- `validate` - Behavioral equivalence verification
- `explain` - Airflow concept explanations with Prefect mappings
- `batch` - Directory-wide batch conversion
- `scaffold` - Complete project generation following PrefectHQ/flows patterns

**Pattern Converters**
- TaskFlow API (@dag, @task, @task.bash) conversion
- Dynamic task mapping (.expand() → .map())
- TaskGroup → Prefect subflow conversion
- Trigger rule mapping (all_done, one_failed, etc.) to state-based checks
- Jinja2 template detection with f-string conversion hints
- Sensor detection with polling pattern scaffolds
- Airflow Datasets → Prefect Events analysis

**Operator Support**
- Core operators: PythonOperator, BashOperator, BranchPythonOperator
- 35+ provider operators with conversion mappings:
  - AWS: S3, Lambda, Glue, EMR, Athena, Step Functions
  - GCP: BigQuery, GCS, Dataproc, Dataflow
  - Azure: Blob Storage, Data Factory, Synapse
  - Databricks: Jobs, SQL, Notebooks
  - dbt: Cloud and Core
  - Snowflake, Kubernetes, HTTP, Email, Slack
- Custom operator detection with stub generation

**Connection & Variable Handling**
- Airflow Hook → Prefect Block mapping scaffolds
- Connection patterns → Block configuration guidance
- Variable.get() → Secret/Variable scaffold generation

**Validation System**
- AST-based task graph extraction for both DAG and flow
- Task count verification (excluding DummyOperator/EmptyOperator)
- Dependency preservation checking
- XCom → return value pattern detection
- Confidence scoring (0-100)

**Test Generation**
- Automatic pytest test scaffolds for converted flows
- Import validation
- Task execution order tests
- Return value assertion templates

**Migration Runbooks**
- DAG-specific migration guidance
- Schedule configuration mapping
- Retry and timeout conversion notes
- Connection setup checklists

**Metrics & Observability**
- Operator coverage tracking
- Conversion success/failure rates
- Warning frequency analysis
- JSON export for dashboards

**External MCP Integration**
- Prefect documentation search proxy
- Astronomer migration guidance proxy
- Configurable timeouts and fallback modes

**Interactive Wizard (MCP App)**
- 7-step guided migration wizard UI
- React/TypeScript frontend with shadcn/ui
- Real-time DAG analysis and preview
- Project export as ZIP

**Documentation**
- Comprehensive getting started guide
- 19 markdown documentation pages
- Operator mapping reference
- Pattern-specific conversion guides
- Troubleshooting FAQ
- Enterprise migration playbooks

**CI/CD**
- GitHub Actions for test, lint, typecheck, docs, release
- Multi-Python version testing (3.11, 3.12, 3.13)
- PyPI release workflow with trusted publishing
- Coverage reporting with Codecov

### Changed
- Nothing yet (initial release)

### Fixed
- Nothing yet (initial release)

[0.1.0]: https://github.com/prefecthq/airflow-unfactor/releases/tag/v0.1.0

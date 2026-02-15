## 1. Validation Engine (P0)

- [x] 1.1 Create `src/airflow_unfactor/tools/validate.py` with graph extraction from DAG
- [x] 1.2 Add flow parsing to extract @task functions and call relationships
- [x] 1.3 Implement task count comparison with DummyOperator exclusion
- [x] 1.4 Implement dependency graph comparison (isomorphism check)
- [x] 1.5 Implement data flow validation (XCom → return/parameter)
- [x] 1.6 Generate structured validation report with is_valid, issues, confidence_score
- [x] 1.7 Write tests for validation engine (simple DAG, complex DAG, mismatches)
- [x] 1.8 Update MCP server to use new validate implementation

## 2. Provider Operator Expansion (P1)

- [x] 2.1 Add AWS S3 operators: S3CopyObjectOperator, S3ListOperator, S3FileTransformOperator
- [x] 2.2 Add AWS compute operators: EcsRunTaskOperator, EksCreateClusterOperator, EksPodOperator
- [x] 2.3 Add AWS data operators: GlueJobOperator, GlueCrawlerOperator, RedshiftSQLOperator
- [x] 2.4 Add GCP storage operators: GCSToGCSOperator, GCSDeleteObjectsOperator, GCSFileTransformOperator
- [x] 2.5 Add GCP compute operators: DataprocSubmitJobOperator, DataprocCreateClusterOperator
- [x] 2.6 Add GCP messaging operators: PubSubPublishMessageOperator, PubSubCreateSubscriptionOperator
- [x] 2.7 Add Azure operators: WasbBlobOperator, AzureDataFactoryRunPipelineOperator
- [x] 2.8 Add Databricks operators: DatabricksRunNowOperator, DatabricksSubmitRunOperator, DatabricksSqlOperator
- [x] 2.9 Add dbt operators: DbtCloudRunJobOperator, DbtRunOperator (cosmos)
- [x] 2.10 Write tests for new operator mappings

## 3. Operator Coverage Matrix (P1)

- [x] 3.1 Create `scripts/generate_operator_docs.py` to generate docs from registry
- [x] 3.2 Generate `docs/operator-coverage.md` with categories and status indicators
- [x] 3.3 Add CI check to verify generated docs match registry (operator-docs.yml)
- [x] 3.4 Add pre-commit hook to regenerate docs on registry changes (CI check sufficient)

## 4. Conversion Metrics (P2)

- [x] 4.1 Create `src/airflow_unfactor/metrics/__init__.py` with ConversionMetrics dataclass
- [x] 4.2 Implement in-memory metrics storage with accumulation
- [x] 4.3 Add AIRFLOW_UNFACTOR_METRICS environment variable check
- [x] 4.4 Integrate metrics collection into convert tool
- [x] 4.5 Implement export_json() and export_all_json() functions
- [x] 4.6 Implement get_aggregate_stats() for success rate, coverage, warning frequency
- [x] 4.7 Add export_to_file(path) for local debugging
- [x] 4.8 Write tests for metrics module

## 5. Conversion Core Enhancements (P3)

- [x] 5.1 Add multi-task XCom pull detection in XCom analyzer
- [x] 5.2 Generate multi-parameter function signatures for multi-task pulls
- [x] 5.3 Add warning for dynamic XCom patterns (variable task_ids)
- [x] 5.4 Convert retry_delay to retry_delay_seconds in task decorator
- [x] 5.5 Add warning for exponential_backoff (different Prefect mechanism)
- [x] 5.6 Detect and warn about pool/pool_slots parameters
- [x] 5.7 Write tests for XCom and retry enhancements

## 6. Runbook Enhancements (P3)

- [x] 6.1 Add work pool recommendation section to runbook template
- [x] 6.2 Add automation setup guidance for callback migrations
- [x] 6.3 Add prefect.yaml configuration snippets for schedule/params
- [x] 6.4 Add Block setup CLI commands for detected connections
- [x] 6.5 Add testing guidance section with local and deployment commands
- [x] 6.6 Write tests for enhanced runbook generation

## 7. Documentation

- [x] 7.1 Update README with validation tool usage
- [x] 7.2 Create `docs/enterprise-migration.md` for large-scale migrations (created in ci-and-docs)
- [x] 7.3 Create `docs/prefect-cloud.md` for cloud-specific integration (created in ci-and-docs)
- [x] 7.4 Update troubleshooting guide with validation issues (done in ci-and-docs)

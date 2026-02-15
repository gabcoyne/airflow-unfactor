# Airflow-Unfactor Architecture

## Overview

Airflow-Unfactor is an MCP server that helps convert Airflow DAGs to Prefect flows using LLM-assisted code generation.

**Key Principle**: Instead of deterministic code templating (which is brittle), we provide rich structured analysis payloads that enable LLMs to generate complete, functional, tested Prefect flows.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          MCP Client (LLM)                               │
│                                                                          │
│  1. Call analyze_dag(code) → Get rich structured payload                │
│  2. Call get_prefect_context(topics) → Get Prefect docs/patterns        │
│  3. Generate complete Prefect flow code (LLM does this)                 │
│  4. Call validate_generation(original, generated) → Verify correctness  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     Airflow-Unfactor MCP Server                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ANALYSIS TOOLS (read-only, rich payloads)                              │
│  ├── analyze_dag         → Full DAG structure, operators, dependencies  │
│  ├── analyze_operator    → Deep dive on specific operator type          │
│  ├── analyze_patterns    → XCom, sensors, branching, task groups        │
│  └── analyze_complexity  → Complexity metrics, risk assessment          │
│                                                                          │
│  CONTEXT TOOLS (documentation & patterns)                               │
│  ├── get_prefect_context → Fetch relevant Prefect docs via MCP          │
│  ├── get_deployment_patterns → prefect.yaml structure, work pools       │
│  └── get_operator_mapping → Airflow→Prefect operator equivalents        │
│                                                                          │
│  VALIDATION TOOLS                                                        │
│  ├── validate_generation → Compare structures, verify completeness      │
│  ├── validate_syntax     → Check Python syntax validity                 │
│  └── validate_imports    → Verify Prefect imports exist                 │
│                                                                          │
│  SCAFFOLDING TOOLS (project structure, not code generation)             │
│  ├── scaffold_project    → Generate directory structure                 │
│  └── scaffold_prefect_yaml → Generate prefect.yaml template            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Tool Design Philosophy

### What We Do
- **Parse**: Extract rich, structured information from Airflow DAGs via AST
- **Analyze**: Provide detailed analysis payloads with all context an LLM needs
- **Document**: Surface relevant Prefect documentation and patterns
- **Validate**: Verify that generated code matches expected structure

### What We Don't Do
- **Generate Code**: We don't generate Prefect flow code - the LLM does this
- **Template**: No more deterministic templating with edge cases

## Analysis Payload Structure

The `analyze_dag` tool returns a comprehensive payload:

```json
{
  "dag_id": "example_dag",
  "airflow_version": {
    "detected": "2.7+",
    "features": ["taskflow", "datasets"],
    "confidence": 0.95
  },

  "structure": {
    "operators": [
      {
        "task_id": "extract_data",
        "type": "PythonOperator",
        "line": 25,
        "python_callable": "extract_fn",
        "params": {"source": "s3://bucket/data"},
        "retries": 3,
        "retry_delay": "timedelta(minutes=5)"
      }
    ],
    "dependencies": [
      {"upstream": "extract_data", "downstream": "transform_data"}
    ],
    "task_groups": [...],
    "branching": [...]
  },

  "patterns": {
    "xcom_usage": [
      {"task": "extract_data", "type": "push", "key": "result"}
    ],
    "sensors": [
      {"task": "wait_for_file", "type": "S3KeySensor", "poke_interval": 60}
    ],
    "trigger_rules": [
      {"task": "cleanup", "rule": "all_done"}
    ],
    "dynamic_mapping": [...],
    "connections": ["aws_default", "postgres_conn"],
    "variables": ["env", "config_path"]
  },

  "dag_config": {
    "schedule": "0 * * * *",
    "catchup": false,
    "max_active_runs": 1,
    "tags": ["etl", "production"],
    "default_args": {
      "retries": 2,
      "retry_delay": "timedelta(minutes=5)"
    }
  },

  "complexity": {
    "score": 7,
    "factors": [
      "Has sensors (convert to triggers/polling)",
      "Uses XCom (convert to return values)",
      "Has branching (convert to conditional logic)"
    ]
  },

  "migration_notes": [
    "S3KeySensor: Consider Prefect S3 blocks with polling or event triggers",
    "BranchPythonOperator: Use Python if/else with return task references",
    "Pool 'default_pool': Map to work pool concurrency limits"
  ],

  "original_code": "..."
}
```

## Target Output Structure

Generated Prefect flows should follow the `prefecthq/flows` repository structure:

```
deployments/<workspace>/<flow-name>/
├── flow.py           # Main flow code
├── Dockerfile        # (if custom dependencies)
├── requirements.txt  # Python dependencies

prefect.yaml          # Deployment configuration
```

### prefect.yaml Structure

```yaml
name: flows
prefect-version: 3.0.0

pull:
  - prefect.deployments.steps.git_clone:
      repository: https://github.com/org/repo
      branch: main

definitions:
  docker_build:
    - prefect.deployments.steps.run_shell_script: &git_sha
        id: get-commit-hash
        script: git rev-parse --short HEAD
    - prefect_docker.deployments.steps.build_docker_image: &docker_build
        tag: "{{ get-commit-hash.stdout }}"
        platform: linux/amd64

  work_pools:
    kubernetes_prd: &kubernetes_prd
      name: kubernetes-prd
      job_variables:
        image: "{{ image }}"

  schedules:
    hourly: &hourly
      cron: 0 * * * *

deployments:
  - name: My Flow
    description: |
      Converted from Airflow DAG 'example_dag'.
      Original schedule: 0 * * * *
    entrypoint: deployments/data/my-flow/flow.py:my_flow
    schedules:
      - *hourly
    work_pool: *kubernetes_prd
    build:
      - prefect.deployments.steps.run_shell_script: *git_sha
      - prefect_docker.deployments.steps.build_docker_image:
          <<: *docker_build
          dockerfile: deployments/data/my-flow/Dockerfile
          image_name: registry/my-flow
    push:
      - prefect_docker.deployments.steps.push_docker_image:
          image_name: registry/my-flow
          tag: "{{ get-commit-hash.stdout }}"
```

## External MCP Integration

### Prefect Docs MCP
Call before generating code to get:
- Relevant Prefect patterns for detected features
- Block types for connections
- Deployment configuration options
- Work pool setup guidance

### Integration Flow
```
1. analyze_dag(code)
   → Returns structured payload with detected patterns

2. get_prefect_context(["flows", "tasks", "blocks", detected_features])
   → Calls Prefect MCP, returns relevant documentation

3. LLM generates complete Prefect flow using:
   - Analysis payload (what to convert)
   - Prefect context (how to convert)
   - Target structure (prefecthq/flows patterns)

4. validate_generation(original_dag, generated_flow)
   → Verifies structural completeness
```

## File Organization

```
src/airflow_unfactor/
├── server.py              # FastMCP server entry point
├── tools/
│   ├── analyze.py         # DAG analysis tools
│   ├── context.py         # Prefect docs/pattern tools
│   ├── validate.py        # Generation validation
│   └── scaffold.py        # Project structure generation
├── analysis/
│   ├── parser.py          # AST-based DAG parsing
│   ├── patterns.py        # Pattern detection
│   ├── complexity.py      # Complexity scoring
│   └── version.py         # Airflow version detection
├── mappings/
│   ├── operators.py       # Operator equivalents
│   ├── connections.py     # Connection→Block mappings
│   └── patterns.py        # Pattern conversion guides
└── external_mcp.py        # External MCP client
```

## Migration from Current Architecture

### Removed (deterministic templating)
- `converters/base.py` - Code generation
- `converters/operators/*.py` - Operator templates
- `converters/test_generator.py` - Test code generation

### Kept & Enhanced (analysis)
- `analysis/parser.py` - Enhanced with richer extraction
- `analysis/patterns.py` - New pattern detection
- `analysis/complexity.py` - Risk assessment
- `tools/analyze.py` - Richer payload structure

### New (context & validation)
- `tools/context.py` - Prefect docs integration
- `tools/validate.py` - Generation validation
- `mappings/` - Conversion guidance (not code templates)

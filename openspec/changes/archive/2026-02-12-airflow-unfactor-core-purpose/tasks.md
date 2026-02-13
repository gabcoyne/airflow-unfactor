## 1. Dependency Graph Extraction

- [x] 1.1 Create DependencyGraph class with adjacency list representation
- [x] 1.2 Implement parsing for `>>` and `<<` bitshift operators
- [x] 1.3 Implement parsing for `set_upstream()` and `set_downstream()` methods
- [x] 1.4 Handle fan-out patterns with list syntax `[task_a, task_b]`
- [x] 1.5 Implement topological sort using Kahn's algorithm
- [x] 1.6 Group tasks by execution level for parallel execution hints
- [x] 1.7 Add tests for dependency extraction and topological ordering

## 2. XCom Detection and Conversion

- [x] 2.1 Create XComPullInfo, XComPushInfo, XComUsage dataclasses
- [x] 2.2 Implement AST-based xcom_pull detection with task_ids extraction
- [x] 2.3 Detect variable task_ids patterns and generate warnings
- [x] 2.4 Detect list task_ids patterns and generate warnings
- [x] 2.5 Detect custom key parameters and generate warnings
- [x] 2.6 Convert xcom_push to return statements
- [x] 2.7 Add tests for all XCom detection scenarios

## 3. Jinja2 Template Detection

- [x] 3.1 Create JINJA2_TEMPLATE_MAPPINGS dictionary for Airflow→Prefect hints
- [x] 3.2 Implement detect_jinja2_templates() with regex pattern matching
- [x] 3.3 Add detection for execution context templates (ds, execution_date, ts)
- [x] 3.4 Add detection for task context templates (task.task_id, dag.dag_id)
- [x] 3.5 Add detection for variable/connection templates (var.value, conn)
- [x] 3.6 Generate inline comments with suggested Prefect replacements
- [x] 3.7 Add tests for Jinja2 template detection

## 4. Code Validation

- [x] 4.1 Create validation.py module with ValidationResult dataclass
- [x] 4.2 Implement validate_python_syntax() using ast.parse()
- [x] 4.3 Capture syntax error details: message, line number, column
- [x] 4.4 Integrate validation into conversion pipeline before return
- [x] 4.5 Add validation warnings to conversion result
- [x] 4.6 Add tests for valid and invalid code scenarios

## 5. Converter Result Objects

- [x] 5.1 Create BashConversionResult dataclass with code, warnings, detected_templates
- [x] 5.2 Create PythonOperatorConversionResult dataclass with code, warnings, xcom_usage
- [x] 5.3 Update convert_bash_operator() to return BashConversionResult
- [x] 5.4 Update convert_python_operator() to return PythonOperatorConversionResult
- [x] 5.5 Update tests to use .code attribute from result objects
- [x] 5.6 Aggregate warnings from all converters in flow generation

## 6. Flow Structure Generation

- [x] 6.1 Generate required imports (prefect, subprocess, typing as needed)
- [x] 6.2 Preserve DAG identity in @flow(name=) decorator
- [x] 6.3 Generate tasks in topological order with level grouping comments
- [x] 6.4 Implement data passing for single-upstream dependencies
- [x] 6.5 Implement wait_for pattern for multi-upstream dependencies
- [x] 6.6 Generate if __name__ == "__main__" block for direct execution
- [x] 6.7 Add comprehensive tests for generated flow structure

## 7. Documentation and Specs

- [x] 7.1 Document conceptual mapping: DAG→Flow, Operator→Task, XCom→returns
- [x] 7.2 Document warning categories and severity levels
- [x] 7.3 Document runbook generation requirements
- [x] 7.4 Create design document with architectural decisions
- [x] 7.5 Document open questions for future development

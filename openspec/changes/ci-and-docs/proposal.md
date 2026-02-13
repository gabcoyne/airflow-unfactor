# CI/CD and Documentation Enhancements

## Problem Statement

The airflow-unfactor project has grown significantly with the P0-P3 audit-and-roadmap implementation:
- 666 tests across 23 test files
- 35 operator mappings with provider-specific conversions
- Validation engine, metrics module, and enhanced runbook generation
- New docs/operator-coverage.md generated from registry

However, the CI/CD pipeline and documentation don't fully reflect these capabilities:

1. **Missing CI workflows**: No linting, type checking, or operator docs verification
2. **Outdated documentation**: Index page doesn't mention validation, metrics, or provider operators
3. **Missing documentation pages**: No dedicated pages for validation tool, enterprise migration, or Prefect Cloud integration
4. **Incomplete troubleshooting**: Doesn't cover validation-specific issues

## Proposed Solution

### 1. GitHub Actions Enhancements

Add new workflows and enhance existing ones:

- **Lint workflow**: Run ruff for code quality checks
- **Type check workflow**: Run mypy/pyright for type safety
- **Operator docs workflow**: Verify generated docs match registry (deferred task 3.3)
- **Release workflow**: Automate PyPI publishing on tags

### 2. Documentation Updates

Update existing docs to reflect new features:

- **docs/index.md**: Add validation tool, metrics, provider operators to feature list
- **docs/troubleshooting.md**: Add validation-specific troubleshooting
- **docs/operator-mapping.md**: Reference generated operator-coverage.md

### 3. New Documentation Pages

Create comprehensive guides:

- **docs/validation.md**: How to use the validate tool
- **docs/enterprise-migration.md**: Large-scale migration patterns (deferred task 7.2)
- **docs/prefect-cloud.md**: Cloud-specific features and integration (deferred task 7.3)
- **docs/metrics.md**: How to use the metrics module

## Success Criteria

1. All CI workflows pass on main branch
2. Documentation site builds successfully with new pages
3. Navigation includes new sections
4. Generated operator docs stay in sync with registry

## Non-Goals

- Changes to the conversion logic itself
- New operator mappings (covered by provider-operator-expansion)
- Changes to the docs-site framework/theme

# Proposal: Clean Up Deprecated Template-Based Code

## Problem Statement

The project recently refactored from deterministic template-based conversion to LLM-assisted code generation. The old template code remains in the codebase:

1. `converters/base.py` - Template-based flow generation
2. `converters/test_generator.py` - Placeholder test generation
3. `tools/convert.py` - Deprecated convert tool
4. `tools/batch.py` - Deprecated batch tool

This code is:
- Marked deprecated but still importable
- Confusing for new contributors
- Adding maintenance burden
- Inconsistent with the new architecture

## Proposed Solution

1. **Remove template generation code** from converters/
2. **Keep extraction/analysis code** that feeds the `analyze` tool
3. **Remove deprecated tools** (`convert`, `batch`) from server.py
4. **Update imports** throughout the codebase
5. **Remove unused tests** for deprecated functionality

## Scope

### In Scope
- Remove `converters/base.py` (template generation)
- Remove `converters/test_generator.py` (test scaffolding)
- Remove `tools/convert.py` and `tools/batch.py`
- Remove deprecated tool registrations from `server.py`
- Update `tools/analyze.py` to not depend on removed code
- Remove/update tests for removed functionality

### Out of Scope
- Changing the analysis/extraction logic
- Modifying the new context tools
- UI changes (mcp-app will be updated separately)

## Success Criteria

1. All deprecated template code removed
2. `analyze` tool still works with rich payloads
3. All remaining tests pass
4. No import errors
5. Linting and type checking pass

# Tasks: Clean Up Deprecated Template-Based Code

## Phase 1: Remove Deprecated Tools

- [x] 1.1 Remove `convert` and `batch` tool registrations from `server.py`
- [x] 1.2 Delete `tools/convert.py`
- [x] 1.3 Delete `tools/batch.py`

## Phase 2: Remove Template Generation Code

- [x] 2.1 Delete `converters/base.py` (convert_dag_to_flow)
- [x] 2.2 Delete `converters/test_generator.py`
- [x] 2.3 Clean up `converters/taskflow.py` - has its own `_convert_dag_to_flow` internal function (kept)
- [x] 2.4 Clean up `converters/__init__.py` - removed export of deleted `convert_dag_to_flow`

## Phase 3: Update Dependencies

- [x] 3.1 Update `tools/analyze.py` imports (no changes needed - didn't import convert)
- [x] 3.2 Update `tools/scaffold.py` to not call convert_dag (rewritten for pure scaffolding)
- [x] 3.3 Fix any remaining import errors:
  - [x] Fixed `http_server.py` - removed convert import and /api/convert endpoint
  - [x] Fixed `converters/__init__.py` - removed convert_dag_to_flow export
  - [x] Deleted `.ralph/examples/basic_conversion.py` - used deleted code

## Phase 4: Clean Up Tests

- [x] 4.1 Remove tests for deprecated convert tool (deleted test_convert.py, test_convert_tool.py)
- [x] 4.2 Remove tests for deprecated batch tool (test_conversion_core_p3.py deleted)
- [x] 4.3 Update remaining tests that reference removed code:
  - [x] Updated test_dag_settings_parser.py - removed TestRunbookSpecificity class
  - [x] Updated test_astronomer_fixtures.py - removed conversion tests
  - [x] Rewrote test_http_server.py - removed convert endpoint tests
  - [x] Rewrote test_scaffold.py - updated for new simplified API
- [x] 4.4 Verify all tests pass (603 tests passing)

## Phase 5: Verification

- [x] 5.1 Run full test suite: 603 passed
- [x] 5.2 Run linter (ruff): All checks passed!
- [x] 5.3 Run type checker (pyright): 0 errors, 0 warnings
- [x] 5.4 Verify analyze tool still produces rich payloads (tests pass)

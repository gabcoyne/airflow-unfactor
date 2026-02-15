# Proposal: MCP App Integration & Open Source Polish

## Problem Statement

The airflow-unfactor project has a working MCP App wizard UI but it's not integrated with the main project:

1. **Documentation Gap**: No instructions for using the wizard UI
2. **Architecture Unclear**: TypeScript server expects Python backend at localhost:3001 but Python server doesn't serve those endpoints
3. **CI Missing**: No tests or builds for the mcp-app
4. **Docs Systems Conflict**: Both Jekyll (docs/) and Next.js (docs-site/) exist

Additionally, several open source hygiene items remain:
- External MCP configuration undocumented
- No community links
- Missing benchmarks

## Proposed Solution

### 1. Full MCP App Integration

Integrate the wizard as an optional mode of the main server:

```bash
# Current: Two separate servers
airflow-unfactor           # Python MCP server
cd mcp-app && npm start    # TypeScript wizard server

# Proposed: Single command with optional UI
airflow-unfactor           # MCP tools only (default)
airflow-unfactor --ui      # Also serve wizard UI
```

### 2. Unified Documentation

Consolidate to Jekyll (simpler, standard for GitHub Pages):
- Move any unique content from docs-site to docs/
- Remove docs-site/
- Add wizard documentation to docs/

### 3. CI/CD for MCP App

Add GitHub Actions workflow for:
- TypeScript type checking
- Build verification
- Optional: Playwright e2e tests

### 4. Configuration Documentation

Document how to:
- Configure external MCP endpoints
- Use the wizard standalone vs integrated
- Deploy to production

## Success Criteria

- [ ] `airflow-unfactor --ui` starts server with wizard accessible
- [ ] README includes wizard usage instructions
- [ ] Single docs system (Jekyll)
- [ ] CI builds and tests mcp-app
- [ ] External MCP configuration documented
- [ ] All critical and high-priority audit items resolved

## Out of Scope

- Benchmarking (track separately)
- Additional operator converters (separate effort)
- MCP App feature additions (wizard works as-is)

# Tasks: MCP App Integration

## Phase 1: Python Server HTTP Mode

- [ ] **P1.1** Add aiohttp dependency to pyproject.toml [ui] extra
- [ ] **P1.2** Create `src/airflow_unfactor/http_server.py` with API handlers
- [ ] **P1.3** Add `--ui` and `--port` CLI arguments to main()
- [ ] **P1.4** Write tests for HTTP endpoints
- [ ] **P1.5** Add `src/airflow_unfactor/ui/` directory with placeholder

## Phase 2: UI Build Integration

- [ ] **P2.1** Update mcp-app to use relative API URLs instead of hardcoded localhost
- [ ] **P2.2** Remove mcp-app/server.ts (TypeScript MCP server no longer needed)
- [ ] **P2.3** Create `.github/workflows/build-ui.yml`
- [ ] **P2.4** Add `scripts/build-ui.sh` for local development
- [ ] **P2.5** Update `.gitignore` to track `src/airflow_unfactor/ui/index.html`
- [ ] **P2.6** Build and commit initial UI bundle

## Phase 3: Documentation Consolidation

- [ ] **P3.1** Create `docs/wizard/index.md` - wizard overview
- [ ] **P3.2** Create `docs/wizard/quickstart.md` - getting started
- [ ] **P3.3** Create `docs/configuration/external-mcp.md` - external MCP setup
- [ ] **P3.4** Update README with wizard section
- [ ] **P3.5** Remove `docs-site/` directory (move any unique content first)
- [ ] **P3.6** Update docs/_config.yml header_pages to include wizard

## Phase 4: CI/CD Updates

- [ ] **P4.1** Add mcp-app build verification to test.yml
- [ ] **P4.2** Update release.yml to include UI build step
- [ ] **P4.3** Add UI build artifact to release package

## Phase 5: Open Source Polish

- [ ] **P5.1** Add Prefect community links to docs
- [ ] **P5.2** Add Discord/community badge to README
- [ ] **P5.3** Create CODE_OF_CONDUCT.md
- [ ] **P5.4** Update CONTRIBUTING.md with wizard development instructions
- [ ] **P5.5** Add `make` targets or npm scripts for common workflows

## Phase 6: Testing & Verification

- [ ] **P6.1** Manual test: `airflow-unfactor --ui` serves wizard
- [ ] **P6.2** Manual test: wizard can analyze, convert, validate DAGs
- [ ] **P6.3** Manual test: project export works
- [ ] **P6.4** Run full test suite
- [ ] **P6.5** Verify docs build correctly

## Blocked/Dependencies

- P2.* blocked by P1.* (need HTTP server before UI can call it)
- P4.* blocked by P2.* (need UI build process before CI)
- P6.* blocked by all above

## Estimated Effort

| Phase | Tasks | Effort |
|-------|-------|--------|
| P1    | 5     | Medium |
| P2    | 6     | Medium |
| P3    | 6     | Low    |
| P4    | 3     | Low    |
| P5    | 5     | Low    |
| P6    | 5     | Low    |

Total: ~30 tasks

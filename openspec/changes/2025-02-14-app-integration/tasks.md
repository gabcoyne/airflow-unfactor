# Tasks: MCP App Integration

## Phase 1: Python Server HTTP Mode

- [x] **P1.1** Add aiohttp dependency to pyproject.toml [ui] extra
- [x] **P1.2** Create `src/airflow_unfactor/http_server.py` with API handlers
- [x] **P1.3** Add `--ui` and `--port` CLI arguments to main()
- [x] **P1.4** Write tests for HTTP endpoints
- [x] **P1.5** Add `src/airflow_unfactor/ui/` directory with placeholder

## Phase 2: UI Build Integration

- [x] **P2.1** Update mcp-app to use relative API URLs instead of hardcoded localhost
- [x] **P2.2** Remove mcp-app/server.ts (TypeScript MCP server no longer needed)
- [x] **P2.3** Create `.github/workflows/build-ui.yml`
- [x] **P2.4** Add `scripts/build-ui.sh` for local development
- [x] **P2.5** Update `.gitignore` to track `src/airflow_unfactor/ui/index.html`
- [x] **P2.6** Build and commit initial UI bundle

## Phase 3: Documentation Consolidation

- [x] **P3.1** Create `docs/wizard/index.md` - wizard overview
- [x] **P3.2** Create `docs/wizard/quickstart.md` - getting started
- [x] **P3.3** Create `docs/configuration/external-mcp.md` - external MCP setup
- [x] **P3.4** Update README with wizard section
- [ ] **P3.5** Remove `docs-site/` directory (move any unique content first)
- [x] **P3.6** Update docs/_config.yml header_pages to include wizard

## Phase 4: CI/CD Updates

- [x] **P4.1** Add mcp-app build verification to test.yml
- [x] **P4.2** Update release.yml to include UI build step
- [x] **P4.3** Add UI build artifact to release package

## Phase 5: Open Source Polish

- [ ] **P5.1** Add Prefect community links to docs
- [ ] **P5.2** Add Discord/community badge to README
- [ ] **P5.3** Create CODE_OF_CONDUCT.md
- [ ] **P5.4** Update CONTRIBUTING.md with wizard development instructions
- [ ] **P5.5** Add `make` targets or npm scripts for common workflows

## Phase 6: Testing & Verification

- [x] **P6.1** Manual test: `airflow-unfactor --ui` serves wizard
- [ ] **P6.2** Manual test: wizard can analyze, convert, validate DAGs
- [ ] **P6.3** Manual test: project export works
- [x] **P6.4** Run full test suite (678 passed)
- [ ] **P6.5** Verify docs build correctly

## Blocked/Dependencies

- P2.* blocked by P1.* (need HTTP server before UI can call it) ✅
- P4.* blocked by P2.* (need UI build process before CI)
- P6.* blocked by all above

## Estimated Effort

| Phase | Tasks | Effort |
|-------|-------|--------|
| P1    | 5     | ✅ Done |
| P2    | 6     | ✅ Done |
| P3    | 6     | ⏳ 5/6 |
| P4    | 3     | ✅ Done |
| P5    | 5     | Pending |
| P6    | 5     | ⏳ 2/5 |

Total: ~30 tasks

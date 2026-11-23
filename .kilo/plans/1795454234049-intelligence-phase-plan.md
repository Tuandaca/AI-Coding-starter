# AI-Coding-starter — Next Steps Plan (Intelligence Phase & Scaffold Roadmap)

**Status**: V2.0 Core complete (555 tests passing, READY_FOR_INTELLIGENCE_PHASE)  
**Date**: 2026-11-24  
**Branch**: master (hardening branch `feat/final-resource-hardening` exists but not merged)

---

## Context Summary

| Milestone | Status | Notes |
|-----------|--------|-------|
| M0-M8 (V2.0 Core) | ✅ Done | Portable spec, catalogs, resolver, adapters, migration |
| M9 Codebase Memory | ⏳ Planned | Optional, fail-open, project-local |
| M10 Agent-Reach | ⏳ Planned | Optional research provider |
| M11 Orca / Worktree | ⏳ Planned | Optional orchestration |
| M12 Final Hardening | ✅ Done (branch) | 17 files changed, 555 tests pass |
| Scaffold Roadmap | ⏳ Planned | FULL scaffolds for nextjs-supabase, fastapi-postgres, etc. |
| CI Verification | ⏳ Pending | GitHub Actions configured (Ubuntu + Windows), not executed |

---

## Recommended Next Step: **M9 Codebase Memory Integration**

### Rationale
- First intelligence integration in the staged roadmap (UPGRADE_PLAN.md Section 32)
- Enables project-local code intelligence without external deps
- Fail-open: absence never blocks project creation
- Transient worktree policy already defined (opt-in indexing only)

### Scope
1. **Detection & Health Check**
   - Detect Codebase Memory (CBM) installation
   - Run health check (MCP server reachable)
   - Delegate setup to CBM's `install.sh` / `install.ps1`

2. **Project Policy**
   - `.codebase-memory.json` config per project
   - `cbmignore` for excluded paths
   - Canonical project indexed; transient worktrees ignored by default

3. **Integration Points**
   - Capability Provider Registry entry: `code-intelligence` → preferred: `codebase-memory`, fallback: `source-scan`
   - Optional hook into resolver for context-aware capability suggestions (post-M9)
   - Handoff references branch/worktree via `state.yaml` + `HANDOFF.md`

4. **Safety**
   - No network required for generation (offline-first)
   - No permission-bypass flags
   - CBM indexing does not conflict with Orca/plain git worktrees

---

## Alternative: **Scaffold Roadmap (Incremental FULL Scaffolds)**

### Priority Order (from FINAL_HARDENING_REPORT Section E)
1. `nextjs-supabase` — Highest demand (SaaS, E-commerce, Fullstack)
2. `fastapi-postgres` — AI/RAG, Backend API
3. `dotnet-postgres` — Enterprise, Dashboard
4. `nextjs-dotnet-postgres` — Balanced Fullstack
5. `ai-rag-python` — AI/RAG specific
6. Remaining bundles...

### Approach
- Offline templates in `resources/templates/<bundle-id>/`
- `core/stack_scaffold.py` extended per bundle
- Scaffold support level shown in wizard preview, completion, README
- Each scaffold independently reviewable/mergeable

---

## Alternative: **CI Verification (GitHub Actions)**

### Current Config
- `.github/workflows/ci.yml`: `python -m compileall`, `python -m unittest discover`, `python scripts/ci_consistency_check.py`
- Matrix: `ubuntu-latest` + `windows-latest`, Python 3.11
- Triggers: push/PR to `master` and `feat/final-resource-hardening`

### Action Required
- Push hardening branch to GitHub
- Verify Ubuntu + Windows runs pass
- Merge to master after green CI

---

## Decision Required

**Choose one primary focus for the next implementation cycle:**

| Option | Effort | Value | Risk |
|--------|--------|-------|------|
| **M9 Codebase Memory** | Medium | Code intelligence for generated projects | Low (fail-open, optional) |
| **Scaffold: nextjs-supabase** | High | Runnable SaaS apps out of box | Medium (template maintenance) |
| **CI Verification** | Low | Confidence in cross-platform builds | Low (config already done) |

### My Recommendation: **M9 Codebase Memory**

Reason: Unlocks intelligence layer for all project types, aligns with staged roadmap, low risk (optional/fail-open), enables future Advisor/LLM layer.

---

## Implementation Plan (if M9 chosen)

### Tasks
1. **Provider Registry Entry** (`core/capability_provider_registry.py` - new)
   - Register `codebase-memory` as provider for `code-intelligence`
   - Health check: MCP server ping
   - Fallback: `source-scan` (grep/ast-based)

2. **Detection Module** (`core/cbm_integration.py` - new)
   - `detect_cbm()` → executable path or None
   - `health_check(path)` → bool
   - `get_project_policy(project_dir)` → dict (reads `.codebase-memory.json`)

3. **Setup Delegation**
   - Call CBM's `install.sh` / `install.ps1` with project dir
   - Write `.codebase-memory.json` with `cbmignore` defaults
   - Opt-in transient worktree indexing flag

4. **Wizard Integration** (`new_project.py`)
   - Post-generation: if CBM detected, offer to initialize
   - Add to `resources.lock` as optional capability provider

5. **Tests**
   - Unit: detection, health check, policy parsing
   - Integration: mock CBM install, verify project policy written
   - Negative: CBM absent → generation succeeds, no error

### Acceptance Criteria
- [ ] CBM detected when installed, gracefully skipped when absent
- [ ] Health check passes for valid install
- [ ] Project policy written with canonical project indexed, transient worktrees ignored
- [ ] Generation works offline without CBM (fail-open)
- [ ] No permission-bypass flags introduced
- [ ] All existing tests still pass (555+)

---

## Open Questions

1. **M9 vs Scaffold Priority**: Does the team want runnable SaaS apps (scaffold) or code intelligence (M9) first?
2. **CBM Version Pinning**: Should we pin to a specific CBM release/commit in `upstream-sources.yaml`?
3. **Transient Worktree Default**: Confirm "ignored by default, opt-in per worktree" is the desired policy?
4. **CI Execution**: Should we push the hardening branch now to verify GitHub Actions, or wait for next feature?

---

## Next Action

**Please confirm the primary focus** (M9 / Scaffold / CI) and I'll finalize the detailed implementation plan with exact file changes, test cases, and validation steps.
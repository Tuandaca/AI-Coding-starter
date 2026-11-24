# AI-Coding-starter — Codebase Audit & Next Steps Plan

**Audit Date**: 2026-11-24  
**Current State**: V2.0 Core + M9/M10/M11 Intelligence Integrations complete (618 tests passing)  
**Branch**: master (up to date with origin/master)

---

## 1. Current State Summary

### ✅ Completed Milestones (V2.0 Core + V2.1 Intelligence)

| Milestone | Status | Description |
|-----------|--------|-------------|
| M0-M8 (V2.0 Core) | ✅ Complete | Portable spec, catalogs, resolver, adapters, migration path |
| M9 Codebase Memory | ✅ Complete | Optional code intelligence (cbm_integration.py, capability provider) |
| M10 Agent-Reach | ✅ Complete | Optional research-web provider (agent_reach_integration.py) |
| M11 Orca/Worktree | ✅ Complete | Optional orchestration (orca_integration.py) |
| M12 Hardening | ✅ Complete | Cross-platform setup, security scan, license notices |

### 🧪 Test Status
- **Total tests**: 618 (all passing)
- **Core tests**: ~555 (V2.0)
- **Intelligence tests**: 27 (M9 CBM) + 18 (M10 Agent-Reach) + 18 (M11 Orca) = 63

### 🏗️ Architecture Status

```
Capability Provider Registry (core/capability_provider_registry.py)
├── code-intelligence: codebase-memory (10) → source-scan (100)
├── orchestration: orca (10) → git-worktree (50)
└── research-web: agent-reach (10) → runtime-native (100)
```

All three intelligence integrations follow the same pattern:
1. Detection module (`detect_*()` with PATH + common install locations)
2. Health check (`health_check()` — CBM: TCP port 8765, Agent-Reach: exec presence, Orca: `orca --version`)
3. Provider info for `resources.lock` (`get_*_provider_info()`)
4. Post-generation hook (`maybe_initialize_*()` — fail-open, non-blocking)
5. Integration into `new_project.py` at two points: resources.lock entry + post-generation init

---

## 2. Gap Analysis — What's Missing / Needs Attention

### 🔴 Critical Gaps

| Area | Issue | Impact |
|------|-------|--------|
| **Scaffold Roadmap** | Only `react-static` has "full" scaffold support; 11 bundles are "metadata-only" | Users get AI metadata but no runnable application code for SaaS, AI, backend, etc. |
| **CI Verification** | GitHub Actions configured but not verified on Ubuntu + Windows | No confidence in cross-platform builds |
| **Agency Specialist Catalog** | Imported (268 agents in agency-agents.yaml) but NOT integrated into resolver/wizard | Specialist agents unavailable for project activation |

### 🟡 Medium Gaps

| Area | Issue | Impact |
|------|-------|--------|
| **Orca Detection** | Registry health check only uses `shutil.which("orca")`; integration module uses `orca --version` (10s timeout) | Inconsistency between registry and integration module health checks |
| **Version Management** | No VERSION file in repo (ci_consistency_check.py expects one) | CI check will fail on VERSION check |
| **Resource Templates** | No offline templates for the 11 metadata-only bundles | Can't generate functional apps for Next.js+Supabase, FastAPI+PostgreSQL, etc. |
| **Migrate Project** | `migrate_project.py` exists but not fully tested/integrated | V1→V2 migration path incomplete |

### 🟢 Minor Gaps

| Area | Issue | Impact |
|------|-------|--------|
| **Documentation** | README.md may not reflect V2.1.1 features | Users unaware of new capabilities |
| **Analytics** | analytics.py tracks usage but dashboard may need updates | Limited visibility into new project types |
| **Windows Setup** | setup.bat/setup.sh unified but not recently tested | Potential Windows/POSIX drift |

---

## 3. Recommended Next Steps (Priority Order)

### Phase 1: Scaffold Roadmap — HIGH PRIORITY
**Objective**: Deliver functional application scaffolds for top-demand bundles

| Bundle | Project Types | Priority | Effort |
|--------|---------------|----------|--------|
| `nextjs-supabase` | SaaS, E-commerce, Full-stack, Realtime | 🔴 Critical | High |
| `fastapi-postgres` | Backend API, AI RAG, AI Agent, SaaS | 🔴 Critical | High |
| `dotnet-postgres` | Backend API, Dashboard, Business Website | 🟡 High | High |
| `nextjs-dotnet-postgres` | SaaS, E-commerce, Full-stack, Dashboard | 🟡 High | High |
| `ai-rag-python` | AI RAG, AI Agent | 🟡 High | Medium |
| `expo-supabase-mobile` | Mobile Application | 🟢 Medium | Medium |
| `nestjs-postgres` | Backend API, SaaS, Dashboard | 🟢 Medium | Medium |
| `tauri-react-sqlite` | Desktop Application | 🟢 Medium | Medium |

**Implementation Approach** (per `core/stack_scaffold.py` pattern):
1. Add template files to `BUNDLE_TEMPLATES` in `stack_scaffold.py`
2. Add gitignore templates to `GITIGNORE_TEMPLATES`
3. Update `SCAFFOLD_SUPPORT` from "metadata-only" to "full"
4. Add tests for each new scaffold

### Phase 2: CI Verification — HIGH PRIORITY
**Objective**: Verify GitHub Actions pass on Ubuntu + Windows

1. Push current master to trigger CI
2. Monitor and fix any failures
3. Ensure 618 tests pass on both platforms
4. Add CI badge to README

### Phase 3: Agency Specialist Integration — MEDIUM PRIORITY
**Objective**: Activate specialist agents from the imported Agency catalog (268 agents, 18 divisions)

1. Define specialist filter (coding specialists only, small bounded set)
2. Create execution/team packs (startup-mvp, production-feature, bug-fix, etc.)
3. Integrate into resolver/wizard for capability-aware specialist activation
4. Ensure bounded activation (core team always, specialists as-needed)

### Phase 4: Migration & Polish — MEDIUM PRIORITY
1. Complete `migrate_project.py` for V1→V2 enhancement
2. Update README with V2.1.1 features
3. Add VERSION file
4. Fix Orca health check inconsistency (registry vs integration module)

---

## 4. Detailed Implementation Plan — Phase 1 (Scaffold Roadmap)

### Task 1.1: nextjs-supabase Scaffold
- **Files**: `core/stack_scaffold.py`
- **Templates needed**: package.json, tsconfig.json, next.config.js, src/app/layout.tsx, src/app/page.tsx, src/lib/supabase.ts, tailwind.config.ts, postcss.config.js, .env.example, .gitignore additions
- **Test**: `tests/test_stack_scaffold.py` — verify scaffold generates valid Next.js project structure

### Task 1.2: fastapi-postgres Scaffold
- **Files**: `core/stack_scaffold.py`
- **Templates needed**: pyproject.toml/requirements.txt, main.py, database.py, models/, schemas/, api/routes/, alembic.ini, Dockerfile, .gitignore additions
- **Test**: Verify scaffold generates valid FastAPI project structure

### Task 1.3: dotnet-postgres Scaffold
- **Files**: `core/stack_scaffold.py`
- **Templates needed**: .csproj, Program.cs, appsettings.json, Controllers/, Models/, Data/, Migrations/, Dockerfile, .gitignore additions
- **Test**: Verify scaffold generates valid ASP.NET Core project structure

### Task 1.4: Remaining Bundles
- Follow same pattern for each bundle
- Prioritize by demand: nextjs-dotnet-postgres → ai-rag-python → expo-supabase-mobile → nestjs-postgres → tauri-react-sqlite → nextjs-vercel → vue-lite

---

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Template maintenance burden | High | Medium | Keep templates minimal; use battle-tested starter templates; document update process |
| CI failures on Windows | Medium | High | Test locally on Windows before push; use GitHub Actions matrix |
| Agency catalog integration complexity | Medium | Medium | Start with small specialist set (10-15); defer full 268 agents |
| Scaffold test coverage gaps | Medium | Medium | Add integration tests that verify generated projects can `npm install && npm run build` |

---

## 6. Validation Criteria

### Phase 1 Complete When:
- [ ] `nextjs-supabase` scaffold generates runnable Next.js + Supabase app
- [ ] `fastapi-postgres` scaffold generates runnable FastAPI + PostgreSQL app
- [ ] `dotnet-postgres` scaffold generates runnable ASP.NET Core + PostgreSQL app
- [ ] All new scaffolds have "full" support level in `SCAFFOLD_SUPPORT`
- [ ] README honestly reports scaffold support level per bundle
- [ ] 618+ tests still pass

### Phase 2 Complete When:
- [ ] GitHub Actions pass on ubuntu-latest + windows-latest
- [ ] All 618 tests pass in CI
- [ ] CI badge added to README

### Phase 3 Complete When:
- [ ] Specialist catalog filtered to coding specialists (~10-15 agents)
- [ ] Team packs defined and validated
- [ ] Resolver activates specialists based on project type/capabilities
- [ ] No project loads >N specialists (bounded)

---

## 7. Open Questions

1. **Scaffold Template Source**: Should we adapt templates from popular starter repos (create-next-app, fastapi-starter, etc.) or write minimal custom templates?
2. **Template Update Strategy**: How to handle upstream template updates (Dependabot-style PRs? Manual review)?
3. **Agency Specialist Scope**: Which divisions count as "coding specialists"? (engineering, security, testing, data, devops?)
4. **VERSION File**: What versioning scheme? (SemVer? Date-based like catalog_version?)

---

## 8. Recommended Immediate Action

**Start with Phase 1 Task 1.1: nextjs-supabase scaffold**

Rationale:
- Highest demand (SaaS, E-commerce, Full-stack, Realtime)
- Most complex — validates the scaffold infrastructure
- Unblocks the most project types
- Next.js + Supabase is well-documented with many reference templates

**Estimated effort**: 1-2 implementation sessions for the first scaffold, then faster for subsequent ones using established patterns.

---

## 9. File Inventory for Reference

### Core Integration Files (M9-M11)
- `core/cbm_integration.py` — 304 lines
- `core/agent_reach_integration.py` — 129 lines
- `core/orca_integration.py` — 140 lines
- `core/capability_provider_registry.py` — 185 lines
- `core/stack_scaffold.py` — 390 lines (ONLY react-static has full scaffold)

### Test Files (M9-M11)
- `tests/test_cbm_integration.py` — 27 tests
- `tests/test_agent_reach_integration.py` — 18 tests
- `tests/test_orca_integration.py` — 18 tests

### Catalog Files (10 files)
- `catalog/upstream-sources.yaml` — 5 sources (bundled, agency, agent-reach, orca, cbm, openmontage)
- `catalog/stack-bundles.yaml` — 12 bundles (1 full, 11 metadata-only)
- `catalog/project-types.yaml` — 15 project types
- `catalog/capabilities.yaml`, `catalog/runtime-capabilities.yaml`, etc.

### Entry Points
- `new_project.py` — 2470 lines (main wizard with M9/M10/M11 hooks at lines ~1850-1926 and ~2085-2109)
- `migrate_project.py` — V1→V2 migration
- `analytics.py` — Analytics dashboard

---

**Next Step**: Confirm Phase 1 priority and begin `nextjs-supabase` scaffold implementation.
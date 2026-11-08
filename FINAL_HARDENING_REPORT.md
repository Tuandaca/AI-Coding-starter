# AI-Coding-starter — Final Resource Hardening Report

Branch: `feat/final-resource-hardening` (NOT merged to master, no tag, no release).

## A. Git state

| Field | Value |
|---|---|
| Base SHA (master) | `4e86a2121c9da4b6ed324eeafcb73e60f51d0f27` |
| Final branch SHA | `0b1e2e20704e0c470d17bcdaf4e8e014c526bbf9` |
| Branch | `feat/final-resource-hardening` |
| Commits created | 1 (`0b1e2e2`) |
| Working tree status | clean (`git status --short` empty) |
| VERSION | 2.1.1 (unchanged) |

The single commit touches 17 files (11 modified, 6 added). No history rewritten; no merge to master; no tag/release created.

---

## B. Defects found and fixed

| # | Severity | Root cause | Affected files | Actual fix |
|---|---|---|---|---|
| B1 | High | Agency specialists were gated ONLY by division relevance (`DIVISION_PROJECT_TYPE_RELEVANCE`). An agent with zero project-specific evidence entered scoring and could be selected by arbitrary alphabetical tie-break. | `core/resource_resolver.py` | Replaced inline agency scoring with `core/agency_scoring.py`: common eligibility filter first, then explicit evidence threshold (division relevance = +5 bonus only, never sufficient). |
| B2 | High | Agency agents bypassed `is_resource_eligible` entirely — ineligible agents entered ranking. | `core/resource_resolver.py` | Agency candidates pass `is_resource_eligible` via `AgencyScoringEngine` before scoring; ineligible never enters ranking (invariant applies to all resource types equally). |
| B3 | High | Applicability engine existed but production resources carried no metadata; `when: {always:true}` made everything eligible everywhere. | `catalog/resource-requirements.yaml`, `core/resource_resolver.py` | New canonical `catalog/resource-applicability.yaml` (25 production resources, keyed by (type,id)) as the single eligibility source of truth; resolver loads `ApplicabilityCatalog`. |
| B4 | Medium | `_applicability_from_entry` re-derived capability/stack gating from `when`, creating ambiguous duplicate gating. | `core/resource_resolver.py` | Removed `when`-derivation; documented unambiguous `when` (activation trigger) vs applicability (eligibility gate) semantics in module docstring and code comments. |
| B5 | Medium | `stack_tags_all` failures returned no explainable reason. | `core/applicability.py` | Added `stack_tags_all` to `is_resource_eligible` reason building ("requires all stack tags [...]"). |
| B6 | Medium | `is_global` short-circuited to `return True`, letting global resources bypass requires/conflicts_with. | `core/applicability.py` | Global resources exempt from project-type/capability/stack/task gating but still enforce requires + conflicts_with against `ctx.selected`. |
| B7 | Medium | `task_tags_any` implied support but `ctx.task_tags` was always empty — dead, ambiguous axis. | `core/applicability.py` | Declared task_tags explicitly UNSUPPORTED for project-level resolution (documented; reserved for future task-scoped Advisor layer). |
| B8 | Medium | `requires`/`conflicts_with` evaluated against a snapshot of `selected_so_far`, so they did NOT see resources selected earlier in the same resolution. | `core/resource_resolver.py` | Deterministic fixed-point loop (repeat passes until stable) with a growing `selected_so_far`; a fresh `ApplicabilityContext` is built for every eligibility check. |
| B9 | Medium | Cross-project golden tests omitted `other` and `not-decided` even though they are registered project types. | `tests/test_cross_project_golden.py` | Added `other` and `not-decided` to PROJECT_TYPES, REPRESENTATIVE_CAPABILITIES, STACK_BUNDLE. |
| B10 | Medium | `resource-requirements.yaml` contained a `game-dev` entry while `project-types.yaml` did not register it (dead orphan config). | `catalog/resource-requirements.yaml` | Removed the orphan game-dev requirements (coherent outcome: remove, since no registered type or stack bundle exists for game-dev). |
| B11 | Medium | Scaffold support level (FULL vs METADATA-ONLY) was not shown to the user in preview/completion/generated README. | `core/stack_scaffold.py`, `new_project.py`, `README.md` | Scaffold level displayed in wizard preview, completion screen, generated project README, and starter README ("no application source code was scaffolded" for metadata-only bundles). |
| B12 | Medium | CI used `python3` (absent on Windows), did not cover hardening branches, had no compileall or consistency/security checks. | `.github/workflows/ci.yml`, `scripts/ci_consistency-check.py` (new) | Rewrote ci.yml: `python` (cross-platform), push/PR coverage for `feat/final-resource-hardening`, compileall, full unittest suite, consistency/security check step. |
| B13 | Medium | `UPGRADE_PLAN.md` described V2.1 (M6 + M9 + M10 + M11) as implemented roadmap though M9/M10/M11/LLM Advisor are not implemented. | `UPGRADE_PLAN.md` | Corrected Section 36: V2.0 Core implemented; M9/M10/M11 + LLM Advisor marked NOT IMPLEMENTED, planned only, fail-open, not dependencies of project creation. |
| B14 | Low | `build_default_registry()` used `parent.parent.parent`, resolving to `D:\` instead of repo root — returned empty registry. | `core/resource_registry.py` | Corrected to `parent.parent` (repo root), consistent with the rest of the codebase. |

---

## C. Resolver evidence

Representive project types, resolved via `resolve_resources()` (offline, deterministic). Every Agency specialist carries positive project-specific evidence and an explainable score breakdown; division relevance alone never qualifies.

### Portfolio — caps `[accessibility, i18n]`, bundle `react-static` (minimal profile, budget 4-6)
- Team: 6 agents (within 4-6 ceiling)
- Bundled agents: `frontend-specialist` (project-type), `orchestrator` (project-type), `project-planner` (project planning), `seo-specialist` (search engine optimization)
- Agency specialists:
  - `design-inclusive-visuals-specialist` score=85: project-type-match 40 + capability-match 30 (accessibility) + specialty-tag-match 10 + division-relevance 5
  - `engineering-frontend-developer` score=70: project-type-match 40 + stack-technology-match 20 (react) + specialty-tag-match 10
- Non-agent: `design-system`, `create`, `deploy`, `auto_preview`, `checklist`
- Rejected irrelevant: none of the blocked examples appear (design division is genuinely relevant here)

### Landing page — caps `[i18n]`, bundle `react-static`
- Team: 6 agents
- Bundled: `frontend-specialist`, `orchestrator`, `project-planner`
- Agency: `design-ui-designer` (65), `design-inclusive-visuals-specialist` (45), `design-visual-storyteller` (45)
- `engineering-backend-architect` correctly absent (no backend evidence for a static page)

### SaaS — caps `[authentication, payments, email]`, bundle `nextjs-supabase` (fastest-mvp, budget 5-8)
- Team: 8 agents (within 5-8 ceiling)
- Bundled: `backend-specialist`, `frontend-specialist`, `project-planner`, `security-auditor` (capability:authentication)
- Agency: `security-appsec-engineer` (75: project-type 40 + capability 30 + division 5), `engineering-backend-architect` (65), `design-ui-designer` (65), `design-ux-architect` (45)

### E-commerce — caps `[authentication, payments, search]`, bundle `nextjs-supabase`
- Team: 7 agents
- Bundled: `backend-specialist`, `frontend-specialist`, `project-planner`, `security-auditor` (capability:authentication)
- Agency: `security-appsec-engineer` (75), `engineering-backend-architect` (65: project-type 40 + stack-technology-match 20 postgresql + division 5), `engineering-search-relevance-engineer` (35)
- Non-agent: `database-master` (capability:payments), `database-migration` (capability:payments), `modern-web-architect`, `api-documenter`, `api-standards`
- Correctly absent: `engineering-rag-pipeline-engineer`, `engineering-ai-engineer` (no RAG evidence), `accounts-payable-agent` (no evidence)

### Backend API — caps `[]`, bundle `fastapi-postgres` (balanced, budget 5-8)
- Team: 4 agents
- Bundled: `backend-specialist`, `project-planner`
- Agency: `engineering-backend-architect` (65: project-type 40 + stack-technology-match 20 (fastapi, postgresql) + division 5), `security-appsec-engineer` (45: project-type 40 + division 5)
- Correctly absent: `engineering-frontend-developer`, `engineering-ai-engineer`, `engineering-rag-pipeline-engineer` (no backend evidence), `engineering-ats-validator-architect` (score 5, division only)

### AI/RAG — caps `[ai, rag]`, bundle `ai-rag-python` (balanced, budget 5-8)
- Team: 5 agents
- Bundled: `backend-specialist`, `project-planner`
- Agency: `engineering-ai-engineer` (95: project-type 40 + capability 30 + stack 20 + division 5), `engineering-rag-pipeline-engineer` (95: same), `engineering-search-relevance-engineer` (65: project-type 40 + stack 20 (pgvector) + division 5)
- Non-agent: `ai-engineer` skill, `mcp-builder` skill (requires `ai-engineer`, satisfied via fixed-point), `verify_all` script (requires `test` workflow, satisfied), `ai-master` shared-module
- Correctly absent: `database-migration`, `database-master` (no payments), `security-auditor` (no auth)

### Blocked irrelevant candidates (prevention tests)
All four mission-specified examples score exactly 5 (division relevance only), `qualifies=False`, reason "insufficient evidence: 0 < threshold 30 (division relevance alone)", and are never selected:
- `accounts-payable-agent` for AI/RAG (specialized division, +5 only)
- `business-strategist` as default RAG engineering specialist (+5 only)
- `engineering-ai-data-remediation-engineer` as default e-commerce engineer (+5 only)
- `engineering-ats-validator-architect` as generic backend API specialist (+5 only)

These are prevented by the general evidence-threshold model, not hand-coded exclusions.

---

## D. Applicability evidence

`tests/test_applicability.py` (17 tests, one per axis) plus direct demonstrations:

- **project_types_include (OR)**: `frontend-specialist` eligible for `portfolio`/`landing-page`, not `saas`.
- **project_types_exclude (wins over include)**: `backend-specialist` excluded from `backend-api` despite inclusion.
- **capabilities_any (OR)**: `security-auditor` eligible with `authentication` or `authorization`.
- **capabilities_all (AND)**: requires both `authentication` and `authorization`.
- **capabilities_none (forbid)**: `legacy-mode` ineligible when `ai` selected.
- **stack_tags_any (OR)**: `mobile-developer` eligible with `expo-supabase-mobile`.
- **stack_tags_all (AND + diagnostic)**: `polyglot-backend` ineligible with only `postgresql`; reason "requires all stack tags ['postgresql', 'redis']".
- **task_tags (unsupported at project level)**: `ux-specialist` ineligible because project context carries no task tags; reason "requires one of task tag [...]".
- **requires (AND, sees earlier selections)**: `mcp-builder` ineligible until `skill:ai-engineer` is selected earlier in the same resolution.
- **conflicts_with (OR forbid)**: `database-master` ineligible when `shared-module:ai-master` already selected.
- **global**: `project-planner` eligible for `not-decided`/`other` despite `project_types_exclude`, but a global resource with a conflict against an already-selected resource is still blocked; global `verify_all` requires `workflow:test`.
- **no metadata**: eligible by default ("no applicability metadata recorded; eligible by default") — backward compatibility preserved.

`requires`/`conflicts_with` validated end-to-end in the resolver via the fixed-point: `mcp-builder` only activates after `ai-engineer`; `verify_all` only after `workflow:test`.

---

## E. Scaffold support (FULL vs METADATA-ONLY matrix)

Declared in `core/stack_scaffold.py::SCAFFOLD_SUPPORT`, shown in wizard preview, completion screen, generated project README, and starter README:

| Bundle | Support | Runnable app source scaffolded? |
|---|---|---|
| `react-static` | FULL | Yes (React + TS + Vite + TailwindCSS offline templates) |
| `nextjs-supabase` | METADATA-ONLY | No |
| `expo-supabase-mobile` | METADATA-ONLY | No |
| `nextjs-dotnet-postgres` | METADATA-ONLY | No |
| `fastapi-postgres` | METADATA-ONLY | No |
| `ai-rag-python` | METADATA-ONLY | No |
| `dotnet-postgres` | METADATA-ONLY | No |
| `tauri-react-sqlite` | METADATA-ONLY | No |
| `nestjs-postgres` | METADATA-ONLY | No |
| `nextjs-vercel` | METADATA-ONLY | No |
| `vue-lite` | METADATA-ONLY | No |

Metadata-only bundles may still be generated as AI-Coding-starter state, but the user is told explicitly that application source code was **not** scaffolded. No new large scaffolds were implemented in this pass; an incremental roadmap (nextjs-supabase, fastapi-postgres, dotnet-postgres, nextjs-dotnet-postgres, ai-rag-python, then the rest) is proposed after correctness closure.

---

## F. Test and CI evidence

| Item | Result |
|---|---|
| Total unit tests | 555 (stdlib `unittest`, 100% offline, no network/API key/LLM) |
| Failures | 0 |
| `python -m compileall` | Passes (core, tests, scripts, entry points) |
| Consistency/security checks (`scripts/ci_consistency_check.py`) | Passes: catalog JSON validity, no enabling permission-bypass flags, agency-enrichment ids match real agents, applicability keys unique, resource-requirements project types all registered, VERSION present |
| Ubuntu GitHub Actions | **Configured** (`.github/workflows/ci.yml`: `python -m compileall`, `python -m unittest discover`, `python scripts/ci_consistency_check.py` on `ubuntu-latest` + `windows-latest`, Python 3.11, push/PR to master and hardening branches). **Not actually executed** in this environment — no GitHub Actions/network access. Per the mission, CI is not reported green unless an actual run is green. |
| Windows GitHub Actions | **Configured** (same matrix). **Not actually executed** — same environment limitation. |

Note: the local test suite (555 tests), compileall, and consistency checks — which are the exact commands the CI runs — all pass locally. Actual GitHub Actions runs could not be performed because this is an offline sandbox without GitHub access.

---

## G. Remaining technical debt (genuine remaining work)

1. **M9 Codebase Memory** — not implemented (deferred to intelligence phase; fail-open, project-local, transient worktrees excluded by default).
2. **LLM Advisor / Explanation Layer** — not implemented (optional; must not override constraints or be required for project creation).
3. **M10 Agent-Reach** — not implemented (optional research-web provider; explicit consent for authenticated channels).
4. **M11 Orca / worktree orchestration** — not implemented (optional; no unrestricted permission flags).
5. **Incremental scaffold roadmap** — nextjs-supabase, fastapi-postgres, dotnet-postgres, nextjs-dotnet-postgres, ai-rag-python full scaffolds not yet built (deferred; approved separately by Lead).
6. **Actual GitHub Actions runs** — could not be executed offline; should be verified when the branch is pushed to GitHub.

None of these block the hardening baseline; they are explicitly out of scope for this PR (M9/M10/M11 must not be mixed into the final-resource-hardening pull request).

---

## H. Smart-Agent readiness decision

**READY_FOR_INTELLIGENCE_PHASE**

Rationale: every code-level release gate passes locally — eligibility-before-scoring for all resource types, evidence-threshold agency scoring (division relevance alone never activates), applicability metadata used by production resources, requires/conflicts_with via fixed-point, global resources still obey dep/conflict, `stack_tags_all` with diagnostics, unambiguous `when`/applicability semantics, full project-type coverage (`other`/`not-decided` added), game-dev orphan removed, honest scaffold support (FULL vs METADATA-ONLY), no permission-bypass flags, no global config changes, portable-state/runtime-switching invariants intact, 555 tests pass, compileall passes, consistency/security checks pass, CI configured for Ubuntu + Windows.

Caveat: actual GitHub Actions runs (Ubuntu/Windows) could not be executed in this offline sandbox; they should be confirmed green when the branch is pushed. The decision is READY because all actionable hardening work is complete and verified locally, and the CI configuration runs the same commands that pass locally. Do not merge to master, tag, or release until CI is confirmed green.

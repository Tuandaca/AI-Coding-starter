# AI-Coding-starter — Current Status (V2.2.1)

> Concise, factual status matrix. This is NOT a design rationale or roadmap
> rewrite; it records what is implemented, what is honest about its limits,
> and what remains for the M9/M10/M11 intelligence phase. Kept current with
> each release.

## Version

`VERSION` = `2.2.1`.

## Canonical architecture (invariants preserved)

| Invariant | Status |
|---|---|
| `.ai-coding-starter/project.yaml`, `state.yaml`, `resources.lock` authoritative | Implemented |
| `.ai-workspace/` portable human-readable activated resource layer | Implemented |
| End-user project creation offline-capable (no network, no API key, no LLM) | Implemented |
| Deterministic resolver (no LLM/Codebase Memory/Agent-Reach/Orca/Codex/Claude/Gemini/OpenCode/Cursor/Antigravity) | Implemented |
| Optional integrations fail open | Implemented |
| No `--yolo` / `--dangerously-skip-permissions` / `--dangerously-bypass-approvals-and-sandbox` | Enforced (deny-list + CI scan + unit tests) |
| No global runtime configuration modified | Implemented |
| Identical resolver input → identical deterministic output | Tested |
| Importing all 268 Agency agents ≠ activating all agents | Implemented (bounded team) |
| Incomplete scaffold support never hidden | Implemented (FULL vs METADATA-ONLY displayed) |

## Resource resolution

| Component | Status |
|---|---|
| Deterministic bounded resolver (`core/resource_resolver.py`) | Implemented + hardened |
| Resource applicability engine (`core/applicability.py`) | Implemented + hardened |
| Canonical applicability catalog (`catalog/resource-applicability.yaml`) | Implemented (25 production resources) |
| Agency specialist scoring (`core/agency_scoring.py`) | Implemented (eligibility + evidence threshold) |
| Agency enrichment catalog (`catalog/agency-enrichment.yaml`) | Implemented (10 records, all match real agent IDs) |
| Execution packs (`catalog/execution-packs.yaml`) | Implemented |
| Eligibility filter before scoring (all resource types) | Implemented |
| `requires`/`conflicts_with` within same resolution (fixed-point) | Implemented |
| Global resources still obey dependency/conflict | Implemented |
| `stack_tags_all` with explainable diagnostics | Implemented |
| `when` vs applicability semantics documented | Implemented |

## Agency specialists (268 imported, bounded activation)

| Area | Status |
|---|---|
| Full Agency catalog imported (`catalog/agency-agents.yaml`, 268 agents, 18 divisions) | Implemented (M6.0, pinned) |
| Division relevance alone sufficient for activation | BLOCKED (evidence threshold) |
| Alphabetical fallback for normal projects | BLOCKED |
| Every activated specialist has explainable score breakdown | Implemented |
| Semantic golden tests (portfolio, landing-page, SaaS, e-commerce, backend-api, AI/RAG) | Implemented |
| Irrelevant candidates blocked (accounts-payable, business-strategist, AI data remediation, ATS validator) | Implemented (general model, not hand-coded exclusions) |

## Stack scaffold support

| Bundle | Support | Runnable app source? |
|---|---|---|
| `react-static` | FULL | Yes (offline templates) |
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

Scaffold support level is shown in the wizard preview, completion screen, and
generated project README. No large new scaffolds were added in this hardening
pass; a separate incremental roadmap (nextjs-supabase, fastapi-postgres,
dotnet-postgres, nextjs-dotnet-postgres, ai-rag-python, then the rest) is
proposed after correctness closure.

## Optional integrations (NOT implemented — fail open)

| Integration | Status | Notes |
|---|---|---|
| M9 Codebase Memory | Not implemented | Optional, fail-open, project-local, transient worktrees excluded by default |
| LLM Advisor / Explanation Layer | Not implemented | Optional, never overrides constraints, never required for project creation |
| M10 Agent-Reach | Not implemented | Optional research-web provider, explicit consent for auth channels |
| M11 Orca / worktree orchestration | Not implemented | Optional, no unrestricted permission flags |

## Tests & CI

| Item | Status |
|---|---|
| Total unit tests | 555 (stdlib unittest, offline) |
| Test suite result | All passing |
| `compileall` | Passing |
| CI: Ubuntu + Windows, PRs to master + hardening branches | Configured (`.github/workflows/ci.yml`) |
| CI: compileall + full suite + consistency/security checks | Configured |

## Not a release

No tag, no release, no merge to master. The hardening branch
`feat/final-resource-hardening` is PR-ready once all release gates pass.

# AI-Coding-starter V2 — Architecture Audit & Master Plan

> **Phase**: PLAN-ONLY. No core code is modified in this phase. The only file changed by this phase is `UPGRADE_PLAN.md`.
> **Status**: Implementation-ready master plan.
> **Baseline**: Local `master` at `ae3f73f` (working tree clean). `origin/master` at `d7fac14`.
> **NOTE**: The previous plan's baseline (HEAD `1b47280`, 4 commits behind `d7fac14`) is stale — the local tree has since absorbed `d7fac14` plus the plan commit itself. This plan records the real baseline (see Section 2).

---

## 1. Executive summary

AI-Coding-starter is a small Python project that bootstraps AI-assisted coding projects. Its current generator (`new_project.py`) works, but it is tightly coupled to an external Antigravity template, hard-codes project types and tech presets in Python, merges incompatible stacks blindly, and produces Antigravity/Gemini-centric markdown with no machine-authoritative portable state.

V2 re-factors the project into a **tool-agnostic, self-contained starter** with a deterministic core and optional, gracefully-failing integrations. The generated project carries runtime-neutral portable state (`.ai-coding-starter/project.yaml`, `state.yaml`, `resources.lock`) so any compatible coding runtime can open the same repository and continue from shared state without project migration.

This plan is staged (no big-bang rewrite). V2.0 Core establishes the portable runtime architecture, catalogs, resolver, adapters, and safe migration path. Optional intelligence/orchestration (Codebase Memory, Agent-Reach, Orca, Agency specialist catalog) ships in V2.1+.

---

## 2. Verified current-state baseline

Baseline established by inspecting the actual repository (not documentation), compiling the Python sources, and checking git state.

### 2.1 Repository layout (verified)

```
AI-Coding-starter/
├── .agent/
│   ├── workflows/   # commit.md, deploy.md, fix.md, progress.md, stats.md, status.md (6 files, preserved)
│   └── CONTEXT.md   # phase log for this starter repo itself
├── analytics.py     # analytics dashboard + CONTEXT.md progress parser (~557 lines)
├── config.json      # {"MASTER_TEMPLATE_PATH": "D:\\VibeCoding-Template\\.agent", "DEFAULT_PROJECT_PATH": "D:\\Projects"}
├── new_project.py   # monolithic interactive wizard (~1697 lines)
├── NewPJ.bat        # generated launcher shortcut (gitignored)
├── newProject.bat   # generated launcher shortcut (gitignored)
├── setup.bat        # Windows interactive setup (clones antigravity-ide.git, writes config.json, mutates nothing in place)
├── setup.sh         # POSIX setup (clones google-antigravity.git, sed-mutates new_project.py in place)
├── README.md
├── UPGRADE_PLAN.md  # this document
├── LICENSE
└── .gitignore
```

### 2.2 Git state (verified by `git status`, `git log`, `git remote -v`)

- Active branch: `master`; working tree clean (`git status --short` empty).
- HEAD: `ae3f73f` "Merge branch 'master' of https://github.com/Tuandaca/AI-Coding-starter" (merge of `d65618a` plan commit into `d7fac14`).
- `origin` = `https://github.com/Tuandaca/AI-Coding-starter.git` (fetch + push).
- The previous plan's claim that HEAD was `1b47280` four commits behind `d7fac14` is **stale**; `d7fac14` is already an ancestor of HEAD.
- Python 3.11.9; `python -m py_compile new_project.py analytics.py` exits 0. No test suite exists; `pytest`/`ruff`/`mypy` not installed.

### 2.3 Verified facts about the current implementation

| # | Claim from prompt | Verified against source | Verdict |
|---|-------------------|-------------------------|---------|
| 1 | External Antigravity/template dependency | `new_project.py` reads `MASTER_TEMPLATE_PATH` from `config.json` (default `D:\VibeCoding-Template\.agent`); `main()` calls `sys.exit(1)` if the path does not exist; `copy_selective()` copies agents/skills/shared/workflows/scripts from the master template. `setup.bat` clones `https://github.com/Dokhacgiakhoa/antigravity-ide.git`; `setup.sh` clones `https://github.com/Dokhacgiakhoa/google-antigravity.git` (different URLs). | **CONFIRMED** — generation is impossible offline and depends on an external clone. |
| 2 | `MASTER_TEMPLATE_PATH` hard-coded | Default hard-coded in both `config.json` and `new_project.py` as a Windows absolute path `D:\VibeCoding-Template\.agent`. | **CONFIRMED** — not portable; POSIX path normalization done by mutating `new_project.py` with `sed` at install time. |
| 3 | Windows/POSIX setup divergence | `setup.bat` is interactive (asks paths, same repo as .bat location); `setup.sh` is non-interactive (`$HOME` paths) and runs `sed -i.bak` to rewrite paths inside `new_project.py`. Clone URLs differ between the two scripts. | **CONFIRMED** — divergent behavior and fragile source mutation. |
| 4 | Hard-coded project types | `PROJECT_TYPES` dict with 7 types hard-coded in Python (`new_project.py` lines ~377-621). | **CONFIRMED**. |
| 5 | Hard-coded tech presets with version labels | `TECH_PRESETS` and `CUSTOM_STACK_OPTIONS` hard-coded in Python; strings include `Next.js 14`, `Vue 3`, etc. | **CONFIRMED**. |
| 6 | Manual/custom stack selection one-by-one | `select_custom_stack()` prompts frontend, backend, database, styling, hosting individually. | **CONFIRMED**. |
| 7 | Multi-preset merging | `merge_tech_stacks()` joins up to 3 presets with ` + `, e.g. "frontend A + frontend B", "backend A + backend B". `select_tech_stack()` allows up to 3 presets. | **CONFIRMED** — not compatibility resolution. |
| 8 | Antigravity/Gemini-centric generated instructions | `generate_gemini_md()` emits `trigger: always_on`, identity `{project_name}Agent`, "Respond in Vietnamese by default", Antigravity workflow references. | **CONFIRMED**. |
| 9 | Monolithic `new_project.py` | Single file ~1697 lines: config, presets, project types, wizard UI, file copying, markdown generation, analytics tracking. | **CONFIRMED**. |
| 10 | No canonical portable runtime-neutral spec | Generated output is `GEMINI.md` + `CONTEXT.md` (human markdown, Antigravity-centric) plus `.agent/`; no `project.yaml`/`state.yaml`/`resources.lock`. | **CONFIRMED**. |

---

## 3. Problems in current implementation

1. **External master-template dependency.** Generation fails without a prior `git clone` of the Antigravity template. Offline project creation is impossible. The template URL differs between `setup.bat` (`antigravity-ide.git`) and `setup.sh` (`google-antigravity.git`).
2. **Non-portable, machine-specific paths.** `MASTER_TEMPLATE_PATH` defaults to `D:\VibeCoding-Template\.agent`. `setup.sh` patches `new_project.py` in place via `sed`, which is fragile and diverges from Windows behavior.
3. **Hard-coded domain model in Python.** Project types (7), tech presets (21+), and stack options are embedded in `new_project.py`, making the catalog hard to audit, version, or extend without touching code.
4. **No compatibility resolution.** `merge_tech_stacks()` blindly concatenates presets (`frontend A + frontend B`, `backend A + backend B`) and `select_tech_stack()` allows up to 3 presets. Custom stack selection has no constraints.
5. **Long, low-signal wizard.** The wizard asks project type, then up to 3 presets, then optionally each stack component one-by-one — no progressive disclosure, no capability-aware filtering, no compact recommendations.
6. **Runtime/vendor lock-in in generated output.** Generated `GEMINI.md` is Gemini/Antigravity-centric (Vietnamese default, `trigger: always_on`, Antigravity workflow commands). Output belongs to one runtime, not the project.
7. **No canonical portable state.** No machine-authoritative `project.yaml`/`state.yaml`/`resources.lock`; state lives in free-form markdown with no defined authority.
8. **Monolithic generator.** `new_project.py` (~1697 lines) mixes config, catalog, UI, copying, markdown generation, and analytics — hard to test and extend.
9. **Stale plan baseline.** The existing `UPGRADE_PLAN.md` records an obsolete git baseline and an Antigravity-specific target layout (`.agents/`, Antigravity frontmatter), which conflicts with the tool-agnostic product principle.

---

## 4. Product principles

| Principle | Meaning for V2 |
|---|---|
| Portable first, runtime second | The project belongs to the portable project specification, never to Codex, OpenCode, Antigravity, Gemini, Claude Code, Cursor, Cline, Kilo, Orca, or any single provider/model/runtime. |
| Deterministic core, optional AI explanation | Resolution works offline with no API key and no LLM. An optional Advisor layer may explain results but never overrides constraints. |
| Capabilities over vendors | Capabilities (auth, payments, search...) are resolved independently of implementations via a provider registry. |
| Catalog over hard-coded Python | Project types, capabilities, and stack bundles are machine-readable catalog data, not Python literals. |
| One coherent stack over arbitrary preset merging | A user selects ONE validated stack bundle. Blind merging of multiple presets is removed. |
| Small core team, specialists on demand | A small always-on core team; specialist agents activated only when relevant, never hundreds loaded up front. |
| Project-local before global configuration | Adapters install project-local, reversible state. No global coding-agent configuration is modified without explicit policy. |
| Optional integrations fail open | Codebase Memory, Agent-Reach, Orca are optional; absence must never block project creation. |
| Schemas before large resource import | Schemas and contracts are defined before any catalog content is imported. |
| Source provenance for third-party resources | Every imported/derived resource records repository, commit SHA, license, and review date. |
| No silent permission bypass | Never enable `--dangerously-skip-permissions`, `--dangerously-bypass-approvals-and-sandbox`, `--yolo`, or equivalent. |
| No hidden vendor lock-in | Runtime switching does not require project migration; no runtime is a dependency of portable state. |
| No big-bang rewrite | Staged migration preserving working behavior; each milestone is independently rollbackable. |

---

## 5. Non-goals

- Do not import Agency Agents wholesale / load hundreds of agents into generated projects.
- Do not copy OpenMontage source (AGPLv3); architectural concepts only.
- Do not make Codebase Memory, Agent-Reach, or Orca a dependency of portable project state or of V2.0 Core.
- Do not create per-runtime Python adapter files (`codex.py`, `opencode.py`, `claude.py`, …) as the primary model.
- Do not modify `new_project.py`, `analytics.py`, `setup.bat`, `setup.sh`, `NewPJ.bat`, `config.json`, `.agent/**`, agents, skills, rules, workflows, tests, package files, or generated projects **in this plan-only phase**.
- Do not silently enable permission-bypass or Yolo/full-autonomy execution modes.
- Do not copy authenticated browser sessions or request passwords in prompts.

---

## 6. Decisions taken (KEEP / MODIFY / DEFER / REJECT register)

Each major proposal from the challenge was decided based on repository evidence.

| # | Proposal | Decision | Rationale (evidence) |
|---|----------|----------|----------------------|
| D1 | Project Type / Capability / Stack Bundle as separate domain concepts | **KEEP** | Current code collapses intent into `PROJECT_TYPES`; verified problem #3/#4. Separation matches Section 4 of the brief. |
| D2 | 3-step progressive-disclosure wizard (type → capabilities → stack) | **KEEP** | Current wizard is long and low-signal (verified problem #5); Section 5 of the brief requires this UX. |
| D3 | Deterministic offline resolver (no API key, no LLM) | **KEEP** | Core product requirement (Section 6); current code has no resolver, only merging. |
| D4 | Optional Advisor / Explanation Layer (LLM) | **KEEP (post-V2.0)** | Allowed by brief; not needed for deterministic core. Deferred to V2.1 so V2.0 ships with zero LLM dependency. |
| D5 | Capability Provider Registry | **KEEP (design in V2.0; providers staged to V2.1)** | Inspired by Agent-Reach's ordered provider/fallback (verified). Must not create hard deps — confirmed by making CBM/Orca/Agent-Reach optional. |
| D6 | Per-runtime Python files (`codex.py`, `opencode.py`, …) | **REJECT** | Adds per-runtime code surface; contradicts "catalog over hard-coded Python" and tool-agnostic principle. Replaced by declarative YAML adapters (D7). |
| D7 | Declarative runtime adapter model (`runtime-capabilities.yaml` + `runtime-adapters/*.yaml` + generic renderer) | **KEEP (V2.0)** | Preferred by brief (Section 8); Agency Agents' `integrations/` + `scripts/convert.sh` (verified) show a working convert-once-to-many-runtimes model. |
| D8 | Portable project state (`project.yaml` / `state.yaml` / `resources.lock`) | **KEEP (minimal)** | Verified problem #7. Markdown files are readable interfaces, not authority. Minimal file set. |
| D9 | Agency Agents specialist catalog | **KEEP (V2.1)** | Curated coding specialists only (verified `divisions.json` + `runbooks.json`); never hundreds; normalized to small team model. Deferred to reduce V2.0 risk. |
| D10 | Agency execution/team packs | **KEEP (V2.1)** | Based on verified `strategy/runbooks.json` roster format (Core Team "always", others "as needed", activation conditions). Normalized, not blindly copied. |
| D11 | Codebase Memory optional integration | **KEEP (V2.1, optional)** | First-class optional code intelligence (verified MIT). Must not duplicate CBM's install logic; transient worktree indexing policy required (Section 13). |
| D12 | Agent-Reach optional research provider | **KEEP (V2.1, optional)** | Verified MIT; ordered provider/fallback model; read-only; auth requires explicit user action. Not a core dep. |
| D13 | Orca / git-worktree orchestration | **KEEP (V2.1, optional)** | Verified MIT; desktop runtime manager, parallel worktrees. Never a dependency of portable state. Security requirement: no silent permission bypass (verified risk). |
| D14 | OpenMontage | **ARCHITECTURAL INSPIRATION ONLY** | Verified AGPLv3. Declarative manifests, scored provider selection, checkpoints, approval gates, audit trail are adopted as concepts; no source copied. |
| D15 | Version labels in tech IDs (e.g. "Next.js 14") | **REJECT** | Stable IDs (`nextjs`, `react`, `aspnet-core`) separate from version policy (verified problem #5; Section 12). |
| D16 | Big-bang rewrite | **REJECT** | Current repo is small and working; Section 16/20 require staged migration. |

---

## 7. Repository target architecture (V2 target layout)

```
AI-Coding-starter/                         # starter (this repo)
├── catalog/                               # machine-readable source of truth
│   ├── project-types.yaml                 # project type catalog (id, name, description, default capabilities)
│   ├── capabilities.yaml                  # capability catalog (id, name, description)
│   ├── stack-bundles.yaml                 # coherent, validated stack bundles (stable IDs, no version labels)
│   ├── compatibility.yaml                 # constraints / incompatibility rules
│   ├── runtime-capabilities.yaml          # per-runtime capability metadata
│   └── upstream-sources.yaml              # provenance: repo, commit SHA, license, resource IDs, reviewed date
├── runtime-adapters/                      # declarative adapter definitions (YAML only unless behavior needs code)
│   ├── codex.yaml
│   ├── opencode.yaml
│   ├── antigravity.yaml
│   ├── claude.yaml
│   ├── cursor.yaml
│   └── generic-renderer.py                # generic renderer; the only adapter code
├── core/                                  # deterministic core (Python, stdlib only)
│   ├── resolver.py                        # capability + stack resolver (offline)
│   ├── spec.py                            # portable project specification
│   ├── state.py                           # canonical state (project/state/resources.lock)
│   ├── wizard.py                          # 3-step progressive-disclosure wizard
│   └── generator.py                       # project scaffolding from catalog + state
├── resources/                             # bundled, self-contained core assets (works 100% offline)
│   ├── agents/                            # small core team agents
│   ├── skills/
│   ├── rules/
│   └── templates/
├── tests/                                 # stdlib unittest suite
├── config.json                            # normalized, relative paths (no machine-specific absolutes)
├── new_project.py                         # refactored entry point (thin, consumes catalogs + core)
├── analytics.py                           # preserved unchanged
├── setup.bat / setup.sh                   # unified, non-divergent, no in-place source mutation
├── THIRD_PARTY_NOTICES.md                 # retained (Section 27)
├── UPGRADE_PLAN.md                        # this document
└── README.md
```

Generated project (portable runtime-neutral state):
```
<project>/
├── .ai-coding-starter/
│   ├── project.yaml     # MACHINE-AUTHORITATIVE: identity, type, capabilities, stack bundle, runtime hints
│   ├── state.yaml       # task/session state (phase, focus, decisions pointer)
│   └── resources.lock   # selected resource versions + provenance references
├── AGENTS.md            # readable interface derived from state (not authoritative)
├── CONTEXT.md           # session memory (human/agent readable; derived)
├── DECISIONS.md         # architecture decision history (derived/appended)
└── HANDOFF.md           # concise continuation summary incl. branch/worktree refs
```

Authority rule: YAML files under `.ai-coding-starter/` are machine-authoritative. Markdown files (AGENTS.md, CONTEXT.md, DECISIONS.md, HANDOFF.md) are derived, human-readable interfaces and MUST NOT be treated as independent sources of truth. If a Markdown file conflicts with YAML, YAML wins.

---

## 8. Domain model

Three explicitly separated concepts (current code collapses these into `PROJECT_TYPES`):

### 8.1 Project Type
What is being built. Stable IDs, examples:
`portfolio`, `landing-page`, `business-website`, `blog-content`, `e-commerce`, `saas`, `fullstack-application`, `dashboard`, `backend-api`, `mobile-application`, `ai-rag`, `ai-agent`, `realtime-application`, `desktop-application`, `other`, `not-decided`.

### 8.2 Capabilities
What it needs. Examples: `authentication`, `authorization`, `payments`, `subscriptions`, `email`, `file-uploads`, `search`, `realtime`, `notifications`, `multi-tenancy`, `caching`, `queues`, `ai`, `rag`, `vector-search`, `analytics`, `i18n`, `accessibility`.

### 8.3 Stack Bundle
One coherent, validated combination. Stable ID examples (no version labels):
`nextjs-dotnet-postgres` (Next.js + TypeScript + ASP.NET Core + PostgreSQL + EF Core), `nextjs-supabase`, `fastapi-postgres`, `react-static`, `dotnet-postgres`.

A user normally selects ONE bundle. Custom stack selection may remain but MUST pass through compatibility constraints. Blind merging of presets (e.g. frontend A + backend B) is removed.

---

## 9. Project Type catalog design

File: `catalog/project-types.yaml`. Each entry: `id`, `name`, `description`, `defaultCapabilities` (subset of capability catalog relevant to this type), `exampleBundles`.

Principle: the wizard shows capabilities only relevant to the selected project type (progressive disclosure). Preselected sensible defaults. "Skip / decide later" always allowed.

Example entry:
```yaml
id: saas
name: SaaS Platform
description: Subscription-based web application
defaultCapabilities: [authentication, authorization, payments, subscriptions, email, caching]
exampleBundles: [nextjs-supabase, nextjs-dotnet-postgres]
```

---

## 10. Capability model

File: `catalog/capabilities.yaml`. Each entry: `id`, `name`, `description`, `exampleImplementations` (e.g. `auth` → `nextauth`, `supabase-auth`, `aspnet-identity`).

Capabilities are resolved separately from implementations via the Capability Provider Registry (Section 21). The core requests a capability; a provider supplies an implementation.

---

## 11. Stack Bundle model

File: `catalog/stack-bundles.yaml`. Each entry: `id`, `name`, `description`, `technologies` (stable IDs), `compatibleWith` (capabilities), `incompatibleWith` (bundles), `recommendedFor` (project types), `tier` (fastest-mvp / balanced / scalable / minimal-static).

Version policy (Section 12): technology IDs are stable (`nextjs`, `aspnet-core`, `postgresql`, `ef-core`). Versions are tracked separately in `resources.lock`, never embedded in the ID or catalog text unless a major version is intentionally pinned.

Compatibility rules live in `catalog/compatibility.yaml`: hard constraints (e.g. `nextjs` + `aspnet-core` as two frontends is invalid), soft warnings, and required capability pairings.

---

## 12. Compatibility / constraint resolver

File: `core/resolver.py`. Inputs: project type, selected capabilities, optional preferred bundle. Output: exactly ONE coherent stack bundle, or a deterministic rejection with reason.

Properties (verified requirement #6):
- Offline; no Codex/OpenCode/Antigravity/API key/LLM.
- Deterministic: same input → same output every run.
- Authoritative: result cannot be overridden by the optional Advisor layer.
- Rejects arbitrary preset merging (validated problem #7).

Interface: `resolve(project_type, capabilities, preferBundle) → {bundle, reason, warnings} | Rejection`.

---

## 13. Resource catalog

Files: `catalog/stack-bundles.yaml`, `catalog/project-types.yaml`, `catalog/capabilities.yaml`, `catalog/compatibility.yaml`, `catalog/runtime-capabilities.yaml`. Catalogs are data (YAML/JSON), importable and auditable without executing code.

Agency resource import must NOT happen before the resource contract/catalog is stable (M1 before M6).

---

## 14. Core Team vs Specialist Catalog

- **Core Team** (small, always available): Project Planner/Architect, Backend Engineer, Frontend Engineer, QA/Code Reviewer. Normalized from Agency Agents `divisions.json` engineering/product/project-management divisions.
- **Specialist Catalog** (activated on demand): curated coding-related specialists only (Software Architect, Database Optimizer, Identity & Access Engineer, Payments & Billing Engineer, Search Relevance Engineer, RAG Pipeline Engineer, Accessibility Specialist, SRE, Privacy Engineer). Never hundreds. Source: Agency Agents divisions, filtered to coding relevance, normalized to the small team model.

No duplicate responsibility between core team and specialists.

---

## 15. Agency Agents integration

License: **MIT** (verified). Upstream: `msitarzewski/agency-agents`, default branch `main`.

### 15.1 What will be integrated (V2.1, after catalog stable)
- **Specialist catalog**: normalized from Agency `divisions.json` (engineering, product, project-management, security, testing, design) filtered to coding-related specialists; small set only.
- **Execution/team packs**: modeled on `strategy/runbooks.json` roster format — `slug`, `title`, `mode`, `duration`, `summary`, `doc`, `roster` grouped by `group`/`activation` (`always`, `as needed`, `post-fix`, `week 3+`). Packs: `startup-mvp`, `production-feature`, `bug-fix`, `refactor`, `security-audit`, `performance-investigation`, `incident-fix`. Each pack defines core roles, optional roles, activation conditions, workflow, quality gates.

### 15.2 What only inspires architecture
- `divisions.json` catalog metadata pattern (label/icon/color per division) → catalog metadata.
- `integrations/` + `scripts/convert.sh` convert-once-to-many-runtimes → declarative runtime adapter model (Section 20).
- Machine-readable runbooks (`strategy/runbooks.json`) → execution pack definition format.

### 15.3 What is deferred
- Full agent authoring content; importing all agents; loading hundreds of agents into generated projects.

### 15.4 What is explicitly excluded
- Blindly copying Agency rosters or non-coding divisions (marketing, sales, finance, healthcare, gis, spatial-computing, paid-media).
- Any Agency code at runtime; agents are markdown definitions consumed by the starter, not runtime dependencies.

### 15.5 Agency-ready contract requirement
V2.0 does not require Agency Agents, but V2.0 architecture must be Agency-ready. M1–M5 contracts and schemas (portable project specification, runtime adapters, resolver interface) must be generic enough that M6 can later import and normalize Agency Agents without requiring a breaking redesign of the portable project specification or runtime architecture.

---

## 16. Execution / Team Packs

Based on Agency `strategy/runbooks.json` structure (verified). Each pack: `slug`, `title`, `mode`, `duration`, `summary`, `doc`, `roster[]` where each roster entry: `group`, `activation` (`always` / `as-needed` / `post-fix`), `agents[]` (slugs referencing the specialist catalog).

Default packs: `startup-mvp`, `production-feature`, `bug-fix`, `refactor`, `security-audit`, `performance-investigation`, `incident-fix`.

Activation rules: core team = `always`; specialists = `as-needed` triggered by capability/stack (e.g. payments selected → Identity & Access Engineer + Payments & Billing Engineer available). Never auto-activated without user awareness.

---

## 17. Portable project specification

Runtime-neutral state owned by the project, not the runtime.

Files under `.ai-coding-starter/`:
- `project.yaml` — project identity/configuration (type, capabilities, stack bundle id, created/updated timestamps, runtime hints). **Machine-authoritative.**
- `state.yaml` — task/session state (current phase, focus, open tasks, last session pointer).
- `resources.lock` — selected resource/stack versions + provenance references (commit SHAs of catalog entries used).

Markdown interfaces (derived, not authoritative): `AGENTS.md`, `CONTEXT.md`, `DECISIONS.md`, `HANDOFF.md`. `DECISIONS.md` = architecture decision history; `HANDOFF.md` = concise continuation summary including branch/worktree references.

Minimal: no more than 4 files under `.ai-coding-starter/`; no unnecessary state files.

---

## 18. Canonical state ownership

Authority matrix:
| Concern | Authoritative source | Readable interface |
|---|---|---|
| Project identity/config | `.ai-coding-starter/project.yaml` | AGENTS.md (derived) |
| Task/session state | `.ai-coding-starter/state.yaml` | CONTEXT.md (derived) |
| Resource versions | `.ai-coding-starter/resources.lock` | AGENTS.md summary (derived) |
| Decision history | DECISIONS.md (append-only log) | DECISIONS.md |
| Handoff / continuation | HANDOFF.md + state.yaml branch refs | HANDOFF.md |

Avoid multiple independent sources of truth. The resolver writes to project.yaml/state.yaml/resources.lock; runtimes read them. Markdown is regenerated from YAML on demand.

---

## 19. Runtime capability model

File: `catalog/runtime-capabilities.yaml`. Each runtime entry describes:
- `id` (codex, opencode, antigravity, claude, cursor, …)
- `instructionFormat` (e.g. AGENTS.md, CLAUDE.md, CODEX.md, GEMINI.md)
- `agentFormat`, `skillFormat`
- `projectLocalPaths`, `globalPaths` (if relevant; global only with explicit policy)
- `mcpSupport`, `hooksSupport`, `subagentSupport`
- `commandWorkflowSupport`
- `limitations`
- `detectionMethod` (executable presence alone does NOT imply intent to modify global config)

Runtime metadata is data, not code, so runtimes can be added without changing core.

---

## 20. Runtime adapter architecture

Replaces the rejected per-runtime Python files (D6).

Model: `catalog/runtime-capabilities.yaml` + `runtime-adapters/<runtime>.yaml` + `core/generic-renderer.py`. A dedicated Python adapter exists ONLY when a runtime requires behavior that cannot be represented declaratively.

Guidelines:
- Declarative wherever possible; generic renderer handles the common case.
- Adapters are project-local and reversible.
- Detecting an executable does NOT mean the starter modifies that runtime's global configuration.
- Project-local before global configuration; no global config changes without explicit policy.

Initial runtimes (declarative YAML): codex, opencode, antigravity, claude, cursor.

---

## 21. Capability provider registry

Inspired by Agent-Reach's ordered provider/fallback model (verified). Providers expose capabilities; the core requests capabilities. No hard dependencies.

Example mapping:
```
code-intelligence   preferred: codebase-memory   fallback: source-scan
orchestration       preferred: orca              fallback: git-worktree
research-web        preferred: agent-reach       fallback: runtime-native
```

Each provider registration: `id`, `capabilities[]`, `priority`, `healthCheck`, `installHint`, `optional: true`. Absence of a provider degrades gracefully (fail open).

---

## 22. Codebase Memory integration

License: **MIT** (verified). Role: first-class optional code intelligence provider. Not a dependency of portable state.

Policy (CBM + worktree, Section 13):
- Detect → health check → project policy → delegate setup to CBM's supported mechanisms (install.sh/install.ps1, `.codebase-memory.json`, `cbmignore`).
- AI-Coding-starter does NOT duplicate or fork CBM's MCP/skills/profiles/hooks integration logic unless a demonstrated gap exists.
- **Transient worktree policy**: transient parallel-agent worktrees are NOT indexed by default. Indexing is opt-in per worktree. Stale indexes are removed when a worktree is deleted. The canonical project (the one with `.ai-coding-starter/state.yaml` marked canonical) is indexed; transient worktrees are ignored unless explicitly opted in.
- Handoff refers to branch/worktree state via `state.yaml` + `HANDOFF.md`.
- If CBM is unavailable, the starter works normally without code intelligence (fail open).
- CBM indexing/worktree behavior must not conflict with Orca or plain git-worktree orchestration: only one system owns indexing of a given worktree; CBM is opted in explicitly.

---

## 23. Agent-Reach integration

License: **MIT** (verified). Role: optional research capability + architectural reference for ordered provider/fallback/health (Section 21). Not a core dependency.

Behavior:
- Detected → health check → optional. Absence never blocks project creation.
- Authenticated channels require explicit user action (verified: Agent-Reach copies browser login only with user consent, never asks passwords, read-only).
- Fail open: if Agent-Reach is unavailable or unauthenticated, research capability falls back to runtime-native search.
- Never silently enable authenticated channels.

---

## 24. Orca / git-worktree integration

License: **MIT** (verified). Role: optional orchestration/runtime manager (desktop app). Not a dependency of portable project state.

Security requirement (verified risk): Current Orca versions may pre-fill full-autonomy / permission-bypass flags. AI-Coding-starter must NEVER silently enable or inherit:
- `--dangerously-skip-permissions`
- `--dangerously-bypass-approvals-and-sandbox`
- `--yolo`
- equivalent unrestricted execution modes.

Any Orca integration planned here must default to safe/manual permission behavior or leave permission selection entirely to the user.

Worktree policy: Orca's parallel worktrees (one per agent) and plain git worktrees are supported as orchestration surfaces. The portable project state travels with the repository, so runtime switching between Orca-managed worktrees and plain worktrees does not require migration. Permission selection remains with the user; AI-Coding-starter never sets unrestricted modes.

---

## 25. OpenMontage-derived architectural patterns

License: **AGPLv3** (verified). OpenMontage source is NOT copied. Concepts adopted only:

- Declarative pipeline manifests → `catalog/*.yaml` + `runtime-adapters/*.yaml`.
- Agent-first orchestration → the starter itself is agent-friendly but runtime-neutral.
- Pipeline/stage contracts → resolver + generator as contract-driven stages.
- Selector + fallback → Capability Provider Registry (Section 21).
- Scored provider selection → provider registry priority + health check.
- Schema validation → Section 1 schemas enforced before import.
- Checkpoints → `state.yaml` session checkpoints; resumable generation.
- Human approval gates → user confirmation before project creation and before any global config change.
- Post-execution quality gates → resolver rejection of invalid bundles; adapter validation.
- Layered knowledge → catalog (data) + skills (markdown) + runtime adapters.
- Decision audit trail → `DECISIONS.md` + `resources.lock` provenance.

Video-production complexity (rendering, codecs, FFmpeg, backlot, Remotion) is NOT adopted — out of scope for a coding bootstrapper.

---

## 26. Security model

Conservative by default. Never automatically:
- copy authenticated browser sessions;
- expose secrets;
- request passwords in prompts;
- enable permission bypass / Yolo / full autonomy;
- modify global coding-agent configuration without explicit policy;
- run `git add .` by default;
- overwrite user resources.

Optional integrations (CBM, Agent-Reach, Orca) fail gracefully. Agent-Reach authenticated channels require explicit user action. Orca unrestricted permission modes are never silently enabled. Generated `.gitignore` excludes `.env` files. Secrets never written to `project.yaml`/`state.yaml`/`resources.lock`.

M12 hardening concerns (secret safety, safe filesystem operations, cross-platform path awareness, license/provenance awareness, no silent permission bypass) are applied as continuous engineering constraints across M0–M11 rather than postponed entirely until M12; M12 remains the final consolidation/release hardening milestone.

---

## 27. License / provenance model

Verified upstream licensing:
- Agency Agents → MIT
- Agent-Reach → MIT
- Orca → MIT
- Codebase Memory MCP → MIT
- OpenMontage → AGPLv3

Classification:
- **Copied resource**: preserve copyright/license notice (MIT resources).
- **Transformed resource**: preserve notice + document transformation.
- **Architectural inspiration**: OpenMontage concepts only (AGPLv3 — no source copied).
- **Optional external integration**: no copy; runtime delegates to user-installed external tool.

Maintainer-side provenance: `catalog/upstream-sources.yaml` records repository, commit SHA, license, resource IDs selected, last reviewed date, transformation/import version. Distinct from generated-project `resources.lock`. Reproducible imports, upstream diff review, license tracking, no silent replacement of resource behavior. End users do NOT require network access for normal project creation; upstream sync is a maintainer operation.

Retain `THIRD_PARTY_NOTICES.md`.

---

## 28. Upstream synchronization strategy

- Schemas/contracts stable first (M1) before any catalog import (M6).
- Upstream sync is a maintainer operation, not a runtime dependency.
- `upstream-sources.yaml` pins commit SHAs; changes require review of diff + license check.
- Network access required only for maintainer sync; offline generation uses bundled `resources/`.

---

## 29. Update / version / resource-lock strategy

- Stable technology IDs separate from versions (D15).
- Catalog versions are bumped independently; existing generated projects keep their selected stack (no forced migration).
- `resources.lock` records the exact catalog/stack versions used at generation time.
- Updates to catalogs do not break existing generated projects; opt-in migration via `state.yaml` + `HANDOFF.md`.

---

## 30. Wizard UX

Three steps, progressive disclosure (Section 5):

STEP 1 — What project do you want to build? (project type; "Not decided yet" allowed)
STEP 2 — What does it need? (compact multi-select of capabilities relevant to that type; defaults preselected; skip allowed)
STEP 3 — Choose a recommended stack (3–5 coherent bundles: Fastest MVP, Balanced/recommended, Scalable backend, Minimal/static, Custom, Decide later)

Never ask frontend/backend/database/ORM/auth/hosting one-by-one unless Advanced/Custom mode. Custom mode still passes through compatibility constraints. Recommendation engine makes the common path easy.

---

## 31. Existing-project enhancement strategy

Projects generated by V1 (with `.agent/`, `GEMINI.md`, `CONTEXT.md`) are enhanced, not rewritten:
- Add `.ai-coding-starter/project.yaml`/`state.yaml`/`resources.lock` derived from existing GEMINI.md/CONTEXT.md where possible.
- Preserve V1 `.agent/` content (workflows intact).
- Offer one-time migration path; never destructive; user confirmation required.
- Handled in M8.

---

## 32. Migration strategy from current implementation

Staged, no big-bang (D16). Sequencing chosen to respect the dependency graph evidenced by the brief and upstream inspection:

- Catalog/contract stability must precede Agency import (M1 before M6).
- Portable state (M4) precedes provider/runtime integrations (M9–M11).
- Self-contained resources (M2) must precede resolver/catalog use (M3).
- Runtime independence (M5) is core to V2.0 and is NOT deferred.

Preferred sequence: M0 → M1 → M2 → M3 → M4 → M5 → M7 → M8 → M12 (V2.0 Core), then M6 → M9 → M10 → M11 (V2.1 optional).

Rationale for placing M6/M9–M11 in V2.1: they introduce optional external integrations and content authoring; deferring them keeps V2.0 small, deterministic, and shippable (Section 17). M5 (adapter framework) stays in V2.0 because runtime independence is a core product requirement.

Each milestone preserves working behavior and is independently rollbackable (git revert to prior milestone tag).

---

## 33 & 34. Milestones and acceptance criteria

Each milestone defines objective, why, dependencies, files expected to change, files that must not change, tasks, migration concerns, test requirements, security considerations, acceptance criteria (observable outcomes), and rollback strategy.

### Milestone M0 — Baseline, Behavioral Characterization & Regression Safety Net
- **Objective**: (A) Baseline — record the real repository baseline (branch, HEAD, git status, entry points, platform/setup assumptions, current config/path behavior). (B) Behavioral characterization — document and test the actual current behavior of project type selection, `PROJECT_TYPES`, tech presets, `TECH_PRESETS`, custom stack options, stack selection, multi-preset merge behavior, resource resolution, requirement/resource merging, copying behavior, generated instruction/context files, analytics, setup script behavior, and config/path fallback behavior. (C) Regression safety net — create automated tests that make later intentional behavior changes visible, distinguishing PRESERVE / INTENTIONAL CHANGE / BUG-INCONSISTENCY / UNKNOWN.
- **Why**: Current generator is monolithic and behavior is undocumented; refactoring without characterization risks silent regressions. M0 must not alter production behavior or production logic.
- **Dependencies**: None. M1 may start only after M0 baseline is accepted; M2 must not perform significant behavioral refactoring without the M0 characterization suite available.
- **Files expected to change**: New characterization tests under `tests/`; local fixtures under `tests/fixtures/`; baseline/characterization documentation. No production code changes.
- **Files that must not change**: `new_project.py`, `analytics.py`, `setup.bat`, `setup.sh`, `NewPJ.bat`, `config.json`, `.agent/**`. M0 is read-only with respect to production behavior and production logic; it MAY add characterization tests, fixtures, and baseline documentation. Tests may import, invoke, monkeypatch, mock, or run these components safely. Tests must not require production refactoring just to make them testable; document a testing limitation instead of refactoring production code during M0.
- **Tasks**: Record real git baseline (HEAD `ae3f73f`). Map current application entry points. Characterize wizard flow, preset list, `merge_tech_stacks`, template copy paths, config path handling, analytics tracking, setup.bat vs setup.sh divergence. Capture current divergence between setup scripts (different upstream/template repositories, path handling, config generation, script rewriting, platform assumptions) by source inspection — do NOT execute their destructive/install/network actions. Write characterization tests using local fixtures in temporary directories, offline wherever practical, independent of AI provider quotas and Codex/OpenCode/Antigravity/upstream GitHub availability. Capture current multi-preset merge output, resource-copy destination structure, config fallback values, and generated file metadata. Run syntax/compile checks. Record M0 test suite results.
- **Migration concerns**: None.
- **Test requirements**: Python standard library testing preferred (`unittest`, `json`, `pathlib`, `re`, `py_compile`); deterministic, offline wherever practical, safe in temporary directories, independent of Codex/OpenCode/Antigravity availability and external network; no cloning of the external template repository; syntax/compile checks executed. Characterization tests protect externally observable legacy behavior, not arbitrary implementation details (e.g., selected resources resolve to the current result; config fallback returns the current value; current multi-preset merge output is captured; generated files contain expected metadata; resource copying produces the current destination structure). Avoid brittle assertions such as private local variables, irrelevant ordering, or entire huge generated files when targeted assertions suffice.
- **Security considerations**: None. Characterization tests must not overwrite user resources or expose secrets.
- **Acceptance criteria**: 1) Real git baseline recorded; 2) Current application entry points mapped; 3) Current generator behavior characterized; 4) Project-type behavior covered by tests where practical; 5) Tech-preset behavior covered; 6) Multi-preset merge behavior explicitly captured; 7) Config/path fallback behavior captured; 8) Resource-copy behavior tested using controlled temporary fixtures; 9) Generated file behavior characterized; 10) Analytics behavior characterized; 11) `setup.bat`/`setup.sh` divergence documented; 12) Tests do not require cloning the external template repository; 13) Tests do not depend on AI provider quotas; 14) Production behavior remains unchanged; 15) No V2 architecture implementation begins; 16) Syntax/compile checks executed; 17) M0 test suite results recorded; 18) Git diff contains only M0-approved test/fixture/documentation changes.
- **Rollback**: Remove/revert M0-created characterization tests, fixtures, and M0 documentation. Production code requires no rollback because M0 must not alter production logic. If production files change during M0, treat as a scope violation rather than normal M0 behavior.

### Milestone M1 — Canonical contracts + schemas + architecture boundaries
- **Objective**: Define machine-readable schemas for `project.yaml`, `state.yaml`, `resources.lock`, catalog entries, runtime adapter metadata, and the resolver interface. Establish core vs optional boundaries.
- **Why**: "Schemas before large resource import" (D1). Boundaries keep optional integrations from coupling to core.
- **Dependencies**: M0.
- **Files expected to change**: New `schemas/` directory (future implementation); no existing repo files in this phase.
- **Files that must not change**: `new_project.py`, `analytics.py`, `setup.bat`, `setup.sh`, `config.json`, `.agent/**`, agents, skills, rules, workflows, tests.
- **Tasks**: Author JSON/YAML schemas; define authority matrix (YAML authoritative, Markdown derived); define resolver interface signature; define adapter metadata schema.
- **Migration concerns**: None yet.
- **Test requirements**: Schema validation tests using stdlib `unittest`; invalid `project.yaml` rejected; resolver interface specified and reviewable.
- **Security considerations**: Schemas reject unexpected/extra fields (strict mode) to prevent injection via config.
- **Acceptance criteria**: Schemas authored; resolver interface signature specified; schema unit tests pass offline with stdlib only.
- **Rollback**: Revert schema files; no repo impact.

### Milestone M2 — Self-contained resource migration (remove external master-template dependency)
- **Objective**: Eliminate the mandatory external Antigravity template clone. Bundle a minimal self-contained set of core agent/skill/rule assets so generation works 100% offline. Normalize path/config handling (no hard-coded `D:\` paths; relative and config-driven). Unify `setup.bat`/`setup.sh` (same template source, no in-place mutation of `new_project.py` via `sed`).
- **Why**: Verified problems #1, #2, #3 — generation impossible offline, non-portable paths, divergent setup scripts that mutate source.
- **Dependencies**: M1.
- **Files expected to change**: `config.json` (relative paths), `setup.bat`, `setup.sh` (unify), `new_project.py` (refactor to not require external template), new `resources/` bundled assets.
- **Files that must not change**: `analytics.py`; `.agent/workflows/*` preserved intact; generated projects.
- **Tasks**: Audit which agents/skills/workflows are actually needed; bundle minimal core set; rewrite config path resolution relative to starter dir; make template path optional with bundled default; unify setup scripts (same clone URL, no `sed` mutation of source); add offline fallback.
- **Migration concerns**: Existing `config.json` absolute `D:\` path migrated to relative; document one-time config migration.
- **Test requirements**: `test_offline_generation` (generate with network disabled); config path portability test (no machine-specific absolutes); setup script static validation (no `sed` on source, equivalent config output on Windows/POSIX).
- **Security considerations**: Do not clone external repo by default; bundled assets only; no network required for generation.
- **Acceptance criteria**: Generation completes with network disabled; `config.json` contains no machine-specific absolute paths; `setup.bat` and `setup.sh` produce equivalent config; `new_project.py` has no hard requirement on `D:\VibeCoding-Template`.
- **Rollback**: Restore prior `config.json`/setup scripts; uninstall bundled `resources/`.

### Milestone M3 — Project Type + Capability + Stack catalogs + compatibility resolver
- **Objective**: Replace hard-coded `PROJECT_TYPES`/`TECH_PRESETS` with `catalog/project-types.yaml`, `catalog/capabilities.yaml`, `catalog/stack-bundles.yaml`. Implement deterministic offline resolver returning one coherent bundle or a clear rejection. Remove blind multi-preset merging.
- **Why**: Verified problems #4, #5 — hard-coded catalog with version labels, no compatibility resolution, blind merging.
- **Dependencies**: M1, M2.
- **Files expected to change**: New `catalog/` directory; `new_project.py` refactored to consume catalogs (future).
- **Files that must not change**: `analytics.py`, setup scripts.
- **Tasks**: Author project type catalog (incl. `not-decided`); capability catalog; stack bundle catalog (stable IDs, no version labels); compatibility constraints matrix; resolver (`core/resolver.py`); deprecate `merge_tech_stacks` behavior.
- **Migration concerns**: Catalog versions versioned separately; existing projects keep their selected stack (no forced migration).
- **Test requirements**: Resolver unit tests — valid bundle accepted; conflicting bundle rejected (e.g. two frontends); offline deterministic output identical across runs; no version labels embedded in tech IDs.
- **Security considerations**: Resolver never executes user input; catalog is data only.
- **Acceptance criteria**: Resolver returns exactly one coherent bundle for standard inputs; resolver rejects frontend-A + frontend-B combinations; identical output across repeated offline runs; tech IDs contain no version labels.
- **Rollback**: Revert `catalog/` and `core/resolver.py`; `new_project.py` continues using prior hard-coded presets if not yet refactored.

### Milestone M4 — Portable project specification + canonical state
- **Objective**: Define portable runtime-neutral project spec: `.ai-coding-starter/project.yaml` (authoritative), `state.yaml`, `resources.lock`. Markdown files are derived readable interfaces. Define handoff protocol (branch/worktree refs).
- **Why**: Verified problem #7 — no canonical portable spec; state in free-form Antigravity-centric markdown.
- **Dependencies**: M1, M3.
- **Files expected to change**: New spec/state modules; generator writes `.ai-coding-starter/` in generated projects.
- **Files that must not change**: Existing repo core files (this phase).
- **Tasks**: Define authority matrix; define handoff protocol; define minimal file set (≤4 files under `.ai-coding-starter/`); renderer derives Markdown from YAML.
- **Migration concerns**: Existing GEMINI.md/CONTEXT.md projects enhanced in M8, not M4.
- **Test requirements**: Spec round-trip (write `project.yaml` → read back identical); authority test (YAML wins over conflicting Markdown); minimal file count.
- **Security considerations**: State files contain no secrets; `.env` never written by generator.
- **Acceptance criteria**: `project.yaml` sole machine-authoritative config; Markdown docs derived from YAML; handoff record includes branch/worktree; no more than 4 files under `.ai-coding-starter/`.
- **Rollback**: Remove `.ai-coding-starter/` from generator output; regenerate pure markdown as before.

### Milestone M5 — Declarative runtime adapter framework + initial runtimes
- **Objective**: Replace rejected per-runtime Python files with declarative adapters: `catalog/runtime-capabilities.yaml` + `runtime-adapters/*.yaml` + generic renderer. Project-local, reversible; no global config modification without explicit policy.
- **Why**: Tool-agnostic principle; D6 rejected per-runtime Python; Agency `integrations/` + `convert.sh` shows declarative convert-once-to-many-runtimes works.
- **Dependencies**: M1, M4.
- **Files expected to change**: New `runtime-adapters/` + `catalog/runtime-capabilities.yaml` + `core/generic-renderer.py`.
- **Files that must not change**: Existing repo.
- **Tasks**: Author adapter schema; write declarative adapters for codex, opencode, antigravity, claude, cursor; generic render function; detection method (executable presence ≠ intent to modify); project-local install/uninstall.
- **Migration concerns**: None.
- **Test requirements**: Adapter metadata loads and validates; renderer produces correct output per runtime; detection does not mutate global config.
- **Security considerations**: Adapters fail open; no silent global config modification; no permission-bypass flags.
- **Acceptance criteria**: Declarative adapters for ≥4 runtimes; runtime switching reuses same `project.yaml` state; no per-runtime Python files.
- **Rollback**: Remove `runtime-adapters/`; fall back to no adapter (project still portable).

### Milestone M6 — Agency specialist catalog + execution/team packs (V2.1)
- **Objective**: Add normalized Agency Agents specialist catalog (coding specialists only, small set) and execution/team packs modeled on `strategy/runbooks.json`.
- **Why**: Section 10/16; Agency is MIT and offers curated specialists + machine-readable runbooks, but importing all agents is undesirable (D9).
- **Dependencies**: M3, M4 (catalog/state stable first — Agency import must not precede stable contract).
- **Files expected to change**: New specialist catalog data + pack definitions; no core runtime change.
- **Files that must not change**: `new_project.py` core resolver; portable state schema.
- **Tasks**: Filter Agency `divisions.json` to coding specialists; normalize to small team model (no duplicate responsibility); author packs (`startup-mvp`, `production-feature`, `bug-fix`, `refactor`, `security-audit`, `performance-investigation`, `incident-fix`) with core/optional roles, activation conditions, workflow, quality gates.
- **Migration concerns: None.**
- **Test requirements**: Pack definitions validate against schema; specialist slugs resolve to catalog entries; no pack loads >N specialists (bounded).
- **Security considerations: None.**
- **Acceptance criteria**: Small bounded specialist catalog; packs reference only catalog slugs; activation = `always` for core, `as-needed` for specialists; hundreds of agents never loaded.
- **Rollback**: Remove catalog/pack files; starter operates without specialists.

### Milestone M7 — Resource/provenance locking + update strategy (V2.0)
- **Objective**: Maintainer-side provenance (`catalog/upstream-sources.yaml`: repo, commit SHA, license, resource IDs, reviewed date, import version) and generated-project `resources.lock`. Distinct concerns. Retain `THIRD_PARTY_NOTICES.md`.
- **Why**: Section 11/27 — reproducible imports, upstream diff review, license tracking, no silent replacement.
- **Dependencies**: M1, M3.
- **Files expected to change**: `catalog/upstream-sources.yaml`; `THIRD_PARTY_NOTICES.md`; `resources.lock` written by generator.
- **Files that must not change**: Existing repo content (this phase).
- **Tasks**: Author provenance schema; record Agency/Agent-Reach/Orca/CBM MIT + OpenMontage AGPLv3 entries; generator writes `resources.lock`; diff-review workflow for upstream updates.
- **Migration concerns**: None.
- **Test requirements**: Provenance file validates; `resources.lock` contains exact versions used; `THIRD_PARTY_NOTICES.md` present.
- **Security considerations**: License check before import; AGPLv3 (OpenMontage) flagged as concepts-only.
- **Acceptance criteria**: Every imported resource has provenance entry; `resources.lock` matches generated stack; notices file retained; no network required for end-user generation.
- **Rollback**: Revert `upstream-sources.yaml`; stop writing `resources.lock` (fall back to no lock).

### Milestone M8 — Existing-project enhancement (V2.0)
- **Objective**: Enhance V1-generated projects (`.agent/`, `GEMINI.md`, `CONTEXT.md`) with portable state; one-time non-destructive migration with user confirmation.
- **Why**: Safe migration path is a V2.0 core requirement (Section 17); preserve working V1 behavior.
- **Dependencies**: M4.
- **Files expected to change**: Migration utility (future); no existing repo files in this phase.
- **Files that must not change**: V1 `.agent/workflows/` preserved; user source files never overwritten.
- **Tasks**: Derive `project.yaml`/`state.yaml` from existing GEMINI.md/CONTEXT.md where possible; add `.ai-coding-starter/` to generated projects; user confirmation before any modification; no `git add .` by default.
- **Migration concerns**: One-time; non-destructive; opt-in; rollbackable by removing `.ai-coding-starter/`.
- **Test requirements**: Migration on fixture V1 project produces valid `project.yaml`; user source files unchanged; confirmation prompt honored.
- **Security considerations**: Never overwrite user resources; no secrets migrated; confirmation required.
- **Acceptance criteria**: V1 project enhanced with `.ai-coding-starter/` without deleting user files; migration is opt-in and confirmed.
- **Rollback**: Delete `.ai-coding-starter/`; project reverts to V1 state.

### Milestone M9 — Codebase Memory optional intelligence integration (V2.1)
- **Objective**: Integrate Codebase Memory as first-class optional code intelligence per the detect → health-check → policy → delegate model; enforce transient-worktree indexing policy.
- **Why**: Section 13; CBM is MIT and already installs/configured MCP/skills/hooks for many clients; starter must not duplicate that logic.
- **Dependencies**: M4 (state), M5 (adapter/project-local principle).
- **Files expected to change**: Optional integration module; no portable-state change.
- **Files that must not change**: `.ai-coding-starter/` schema; core resolver.
- **Tasks**: Detect CBM; health check; respect `.codebase-memory.json` / `cbmignore`; transient worktrees NOT indexed by default (opt-in); stale indexes removed on worktree deletion; canonical project identified via `state.yaml`; fail open if CBM unavailable.
- **Migration concerns**: None.
- **Test requirements**: CBM absent → starter works normally (fail open); transient worktree not indexed unless opted in; stale index cleanup on worktree removal.
- **Security considerations**: No hidden background indexing proliferation; no indexing of secrets; CBM optional.
- **Acceptance criteria**: Starter functions without CBM; transient worktrees ignored by default; canonical project indexable; explicit opt-in for transient indexing.
- **Rollback**: Disable CBM integration; starter works without it.

### Milestone M10 — Agent-Reach optional research provider (V2.1)
- **Objective**: Integrate Agent-Reach as optional research provider using ordered provider/fallback/health pattern; explicit user action for authenticated channels.
- **Why**: Section 23; Agent-Reach is MIT and offers ordered provider/fallback (architectural reference for Section 21); not a core dep.
- **Dependencies**: M21 (provider registry design).
- **Files expected to change**: Optional provider registration; no core change.
- **Files that must not change**: Core resolver; portable state.
- **Tasks**: Register `agent-reach` as research-web provider with fallback `runtime-native`; require explicit user action for authenticated channels; read-only; fail open if unavailable.
- **Migration concerns**: None.
- **Test requirements**: Provider absent → research falls back to runtime-native (fail open); authenticated channel not auto-enabled.
- **Security considerations**: No password prompts; no silent session copy; explicit user action for auth.
- **Acceptance criteria**: Research works without Agent-Reach; authenticated channels require explicit consent.
- **Rollback**: Remove provider registration; fallback remains.

### Milestone M11 — Orca / git-worktree orchestration integration (V2.1)
- **Objective**: Support Orca and plain git worktrees as orchestration surfaces with safe default permission behavior; never a dependency of portable state.
- **Why**: Section 24; Orca is MIT and manages parallel worktrees; security requirement forbids silent permission bypass.
- **Dependencies**: M4 (portable state travels with repo), M5 (adapter).
- **Files expected to change**: Optional orchestration guidance; no portable-state change.
- **Files that must not change**: Core resolver; state schema.
- **Tasks**: Document safe/default permission behavior; never set `--dangerously-skip-permissions`, `--dangerously-bypass-approvals-and-sandbox`, `--yolo`; permission selection left to user; runtime switching between Orca worktrees and plain worktrees requires no migration.
- **Migration concerns**: None.
- **Test requirements**: No unrestricted permission flags emitted by starter; Orca absent → plain git-worktree path works.
- **Security considerations**: No silent Yolo/full-autonomy; user controls permissions.
- **Acceptance criteria**: Starter never emits permission-bypass flags; Orca optional; portable state identical across Orca/plain worktrees.
- **Rollback**: Remove Orca guidance; plain git-worktree remains supported.

### Milestone M12 — Cross-platform + migration + security + license hardening (V2.0)
- **Objective**: Harden cross-platform behavior, migration safety, security defaults, and license notices before V2.0 release.
- **Why**: Verified problems #2/#3 (Windows/POSIX divergence); Section 26/27 security and license requirements.
- **Dependencies**: M0–M5, M7, M8.
- **Files expected to change**: `setup.bat`, `setup.sh` (unified), `config.json`, security/license files; no core logic change.
- **Files that must not change**: `analytics.py`; user-generated project content.
- **Tasks**: Verify setup.bat/setup.sh produce identical config on Windows/POSIX; no `sed` mutation of source; confirm no permission-bypass flags anywhere; confirm `THIRD_PARTY_NOTICES.md` and provenance notices present; cross-platform path tests.
- **Migration concerns**: Documented one-time config migration for absolute paths.
- **Test requirements**: Cross-platform setup equivalence; security scan (no `yolo`/skip-permissions flags); license notices present; `py_compile` clean.
- **Security considerations**: Conservative defaults verified; no global config mutation without policy.
- **Acceptance criteria**: Unified setup scripts; identical config output cross-platform; no permission-bypass flags; license/provenance notices retained; all prior milestone acceptance criteria still pass.
- **Rollback**: Revert hardening changes; prior milestones unaffected.

---

## 35. Test strategy

- Entire automated test suite uses Python standard library only (`unittest`, `json`, `pathlib`, `re`, `py_compile`) — no unauthorized package installation (matches current environment).
- Tests are offline; no network, no API key, no LLM.
- Test categories: schema validation, resolver determinism/rejection, config path portability, offline generation, adapter metadata validation, migration non-destructiveness, security scan (no permission-bypass strings).
- Acceptance criteria are observable outcomes (no vague "works correctly" / "improved architecture").
- Baseline: 0 tests exist today; M0 records this; milestones add tests incrementally.

---

## 36. Release roadmap

- **V2.0 Core**: M0, M1, M2, M3, M4, M5, M7, M8, M12.
  Establishes tool-agnostic architecture, self-contained starter, catalogs, resolver, portable state, adapter framework, handoff protocol, safe migration path. Zero LLM dependency; zero mandatory external integration.
- **V2.1 (Optional Intelligence & Orchestration)**: M6 (specialist catalog + team packs), M9 (Codebase Memory), M10 (Agent-Reach), M11 (Orca/git-worktree).
  Staged after V2.0 to reduce risk; each optional and fail-open.

Runtime independence (M5) is in V2.0 Core — not deferred — because it is a core product requirement.

---

## 37. Risks and mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| External template clone unavailable/offline | Generation fails | High | M2 bundles resources; generation works 100% offline (test `test_offline_generation`). |
| Hard-coded `D:\` paths break POSIX | Setup/generation fails on Mac/Linux | High | M2 normalizes paths; cross-platform setup equivalence test. |
| setup.sh mutates `new_project.py` via `sed` | Fragile, divergent behavior | Medium | M2 unifies setup scripts; removes in-place source mutation. |
| Blind preset merging produces invalid stacks | Incompatible frontend/backend combos | High | M3 removes `merge_tech_stacks`; resolver validates single bundle. |
| LLM Advisor overrides constraints | Invalid stack selected | Low | Advisor (D4) explicitly cannot override resolver; deferred to V2.1. |
| Silent permission bypass / Yolo | Unsafe agent execution | Low | Section 26 security model; M12 security scan tests for bypass flags. |
| CBM indexes transient worktrees | Hidden background proliferation | Medium | M9 transient-worktree policy: opt-in, stale cleanup, canonical project only. |
| OpenMontage AGPLv3 contamination | License violation | Low | Concepts only; no source copied (Section 25, D14). |
| Agency import before catalog stable | Unstable resource contracts | Medium | M6 gated on M1/M4 stability (Section 16/32). |
| Optional integration missing breaks creation | Project creation blocked | Medium | All optional integrations fail open (Sections 22–24). |

---

## 38. Deferred ideas

The following are explicitly out of V2.0 scope and recorded here rather than implemented:
- LLM Advisor / Explanation Layer (D4) — V2.1 optional.
- Full Agency Agents import / hundreds of agents (D9) — V2.1 small catalog only.
- Codebase Memory, Agent-Reach, Orca as core dependencies — V2.1 optional, fail-open.
- Per-runtime Python adapter files (D6) — rejected in favor of declarative YAML adapters.
- OpenMontage source/video-production features — AGPLv3; concepts only.
- Version labels embedded in tech IDs (D15) — rejected; stable IDs with separate version policy.

---

## 39. Definition of Done for V2

V2.0 is complete when all of the following are observable and pass:

1. Generation completes 100% offline with no network, no API key, no LLM (`test_offline_generation` PASS).
2. `config.json` contains no machine-specific absolute paths; setup.bat and setup.sh produce equivalent config on Windows and POSIX (no `sed` mutation of source).
3. Resolver returns exactly one coherent stack bundle for standard inputs and rejects incompatible combinations (e.g. two frontends), deterministically and repeatedly.
4. Generated projects contain `.ai-coding-starter/project.yaml` (machine-authoritative), `state.yaml`, `resources.lock`; Markdown files are derived interfaces only.
5. Declarative runtime adapters exist for ≥4 runtimes (codex, opencode, antigravity, claude/cursor) with no per-runtime Python files.
6. No permission-bypass flags (`--yolo`, `--dangerously-skip-permissions`, `--dangerously-bypass-approvals-and-sandbox`) anywhere in the starter.
7. All optional integrations (CBM, Agent-Reach, Orca, Agency catalog) are absent-by-default and fail open.
8. License/provenance: `THIRD_PARTY_NOTICES.md` retained; `catalog/upstream-sources.yaml` records MIT (Agency, Agent-Reach, Orca, CBM) and AGPLv3 (OpenMontage, concepts-only) entries.
9. Every milestone's acceptance criteria (Section 33/34) PASS.
10. `python -m py_compile` clean on all starter Python; stdlib test suite passes.

# 🚀 AI Coding Starter

> **V2.2.1** — A portable, runtime-agnostic project bootstrapper for AI-assisted coding with specialist agent teams, multi-runtime adapters, and reproducible resource locking.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests: 618 passing](https://img.shields.io/badge/tests-618%20passing-brightgreen.svg)]()

---

## What is AI-Coding-starter?

AI-Coding-starter creates new coding projects with a **small, relevant team of AI specialist agents** and **portable, machine-authoritative state**. It is **runtime-agnostic**: the generated project carries `.ai-coding-starter/` state that any compatible coding runtime (Codex, OpenCode, Antigravity, Claude Code, Cursor, or a plain editor) can read and continue from — without project migration.

There is **no mandatory external template clone**, no network requirement, and no vendor lock-in. Generation works **100% offline** from bundled, locally-authored resources.

---

## Core Architecture

| Concept | Meaning |
|---|---|
| **Project type** | What you're building (saas, portfolio, blog, docs, landing-page, mobile-app, desktop-app, ai-rag, fintech, fullstack-api). |
| **Capabilities** | What it needs (auth, database, email, search, payments, AI, RAG, …), independent of vendor. |
| **Stack bundle** | One coherent, validated technology combination (e.g., Next.js + .NET + PostgreSQL). |
| **Team pack** | Pre-defined specialist agent team for the project type (startup-mvp, production-feature, bug-fix, refactor, security-audit, performance-investigation, incident-fix). |
| **Resource resolver** | Deterministically selects agents/skills/rules/workflows/scripts from type + capabilities + bundle. |
| **Canonical state** | `.ai-coding-starter/project.yaml`, `state.yaml`, `resources.lock` — machine-authoritative and runtime-neutral. |
| **Runtime adapters** | Declarative per-runtime instruction rendering (Codex, OpenCode, Antigravity, Claude Code, Cursor). |

Generation flow (transactional — nothing is written until you confirm):

```
COLLECT -> RESOLVE -> BUILD IN MEMORY -> PREVIEW -> CONFIRM -> WRITE
```

Canceling at confirmation writes **zero** project files.

---

## Quick Start

### Option A: Download Release ZIP (no Git required)

Recommended for end users.

1. Go to **Releases** on GitHub: https://github.com/Tuandaca/AI-Coding-starter/releases
2. Download the latest release asset ZIP.
3. Extract the ZIP to a folder.

**Windows:**
```bat
setup.bat
NewPJ.bat
```

**macOS / Linux:**
```bash
chmod +x setup.sh
./setup.sh
./NewPJ.sh
```

`setup.bat` / `setup.sh` detects Python, validates bundled resources, and writes `config.json` (no machine-specific absolute paths, no `sed` source mutation, no external template clone). They create a platform launcher (`NewPJ.bat` / `NewPJ.sh`) that runs `new_project.py` from the starter directory.

### Option B: Git Clone (developer flow)

```bash
git clone https://github.com/Tuandaca/AI-Coding-starter.git
cd AI-Coding-starter
./setup.sh      # macOS/Linux
./NewPJ.sh
# or on Windows:
setup.bat
NewPJ.bat
```

Then run the wizard:
```bash
python new_project.py
```

---

## Key Features (V2.1)

### 🤖 Agency Specialist Teams (NEW in V2.1)

**108 coding specialists** across 6 divisions, organized into **7 team packs** triggered by project type:

| Team Pack | Trigger Types | Core + Specialists | Use Case |
|---|---|---|---|
| `startup-mvp` | saas, mobile-app, ai-rag | 8 core + 3 specialists | Greenfield MVP, speed focus |
| `production-feature` | saas, fullstack-api | 8 core + 3 specialists | Feature work on production code |
| `bug-fix` | all types | 8 core + 3 specialists | Minimal, targeted fixes |
| `refactor` | all types | 8 core + 3 specialists | Code modernization, debt paydown |
| `security-audit` | saas, fintech, healthtech | 8 core + 4 specialists | Security review, compliance |
| `performance-investigation` | saas, fullstack-api, ai-rag | 8 core + 3 specialists | Bottleneck analysis, optimization |
| `incident-fix` | saas, fintech, devops-platform | 8 core + 3 specialists | Production incident response |

**Core Team (always active — 8 agents):**
- `engineering-code-reviewer` — Constructive, actionable code review
- `engineering-devops-automator` — CI/CD, infrastructure automation
- `engineering-senior-developer` — Premium implementation (Laravel/Livewire/FluxUI)
- `engineering-software-architect` — System design, DDD, architectural patterns
- `product-manager` — Full lifecycle: discovery → GTM → outcomes
- `product-sprint-prioritizer` — Agile sprint planning, prioritization frameworks
- `project-management-project-shepherd` — Cross-functional coordination, timeline mgmt
- `project-manager-senior` — Spec→tasks, realistic scope, historical context

**Specialists (as-needed — 108 agents across 6 divisions):**
- Engineering (backend-architect, api-platform-engineer, database-optimizer, devops-automator, …)
- Product (sprint-prioritizer, …)
- Security (ai-generated-code-auditor, compliance-engineer, …)
- Testing (reality-checker, evidence-collector, …)
- Project Management (project-shepherd, senior-pm, …)
- Specialized (codebase-archaeologist, …)

### 🔄 Runtime Adapters (Auto-generated)

All 4 adapters are **automatically applied** during project creation:

| Runtime | Config Dir | Key Files |
|---|---|---|
| **Codex** | `.codex/` | `config.toml`, `project.json`, `agents/`, `skills/`, `workflows/`, `scripts/`, `shared/` |
| **OpenCode** | `.opencode/` | `config.json`, `agents/`, `skills/`, `commands/`, `rules/`, `shared/` |
| **Claude Code** | `.claude/` | `settings.json`, `agents/`, `commands/`, `rules/` |
| **Cursor** | `.cursor/` | `rules/*.mdc` (from agents + rules), `mcp.json` |

```bash
# Manual application to existing project
python -c "from core.runtime_adapters import apply_all_adapters; apply_all_adapters('/path/to/project')"
```

### 🔗 Agent Manager Bridge (NEW in V2.1)

Spawn **bounded specialist sessions** via Codex Agent Manager (origin.cursor.com):

```bash
# List available specialists for project
python new_project.py --list-agents --project /path/to/project

# Deploy full team pack (requires origin CLI)
python new_project.py --deploy-agents --project /path/to/project --agent-task "Build authentication API"
```

Features:
- Core team (8 agents) always spawned for project context
- Specialists spawned as-needed per team pack
- Each agent gets isolated git worktree (`{project-id}-{specialist-id}`)
- Agents read `.ai-coding-starter/` + `.ai-workspace/` for project state

### 🔒 Resource Lock & Upstream Sync (NEW in V2.1)

**Content-addressable resource locking** with SHA256 hashes:

```bash
# Initialize default upstream sources (Agency catalog + Starter resources)
python new_project.py --init-upstream --project /path/to/project

# Sync upstream (git clone/pull)
python new_project.py --sync-upstream --project /path/to/project

# Check for updates (git fetch + compare commits)
python new_project.py --check-updates --project /path/to/project

# Verify resources.lock integrity
python new_project.py --verify-lock --project /path/to/project
```

**resources.lock** now includes:
- `content_hash` (SHA256 prefix) for each bundled resource
- `size_bytes` for integrity verification
- Full provenance (source, commit SHA, license, review date)

### ✅ JSON Schema Validation (NEW in V2.1)

```bash
# Validate project.yaml against Draft-07 JSON Schema
python new_project.py --validate-schema --project /path/to/project
```

Validates: required fields, ID formats (kebab-case), ISO dates, enum values, nested objects.

### 📊 Quality Gates (NEW in V2.1)

```bash
# Performance benchmarks
python -m core.benchmarks

# Integration test matrix (10 types × 4 runtimes = 15 tests)
python -m core.integration_test_matrix
```

**Benchmark Targets (all PASS):**
| Operation | Target | Actual |
|---|---|---|
| Adapter Application | < 5s | 48ms |
| Schema Validation | < 50ms | 0.2ms |
| Lock Verification | < 1s | 0.3ms |
| Agent Bridge | < 100ms | 3.7ms |

---

## Supported Runtimes

| Runtime | Representation | Owned files (derived, reversible) | Notes |
|---|---|---|---|
| Portable | `AGENTS.md` (root) only | None | Runtime-neutral, no runtime-specific files |
| Codex | shared root `AGENTS.md` | `.codex/agents/`, `.codex/skills/`, `.codex/workflows/`, `.codex/scripts/`, `.codex/shared/` | Consumes portable instructions |
| OpenCode | shared root `AGENTS.md` | `.opencode/agents/`, `.opencode/skills/`, `.opencode/commands/`, `.opencode/rules/`, `.opencode/shared/` | Consumes portable instructions |
| Antigravity | `.agent/GEMINI.md` | `.agent/GEMINI.md` + `.agent/skills/{slug}/SKILL.md` | Only adapter that owns its instruction file |
| Claude Code | shared root `AGENTS.md` | `.claude/agents/`, `.claude/commands/`, `.claude/rules/` | Consumes portable instructions |
| Cursor | shared root `AGENTS.md` | `.cursor/rules/{slug}.mdc` (from agents + rules) | MDC rule files generated for Cursor |

### Runtime Switching

A generated project can change runtime later without regenerating its identity:

```bash
python new_project.py --switch-runtime codex --project .
python new_project.py --switch-runtime antigravity --project .
python new_project.py --switch-runtime opencode --project .
python new_project.py --switch-runtime claude-code --project .
python new_project.py --switch-runtime cursor --project .
python new_project.py --switch-runtime portable --project .
```

Canonical state (`.ai-coding-starter/`) and the portable workspace (`.ai-workspace/`) stay byte-identical across switches; only runtime-owned derived files change.

---

## Project Types, Capabilities & Stack Bundles

The catalog (`catalog/`) is machine-readable data, not hard-coded Python. The wizard shows capabilities relevant to your project type, then resolves **one** coherent stack bundle (no blind preset merging). The result is deterministic: identical input always yields identical resources.

**10 Project Types:**
- `saas` — Multi-tenant web applications
- `portfolio` — Personal portfolio sites
- `blog` — Content-focused blogs
- `docs` — Documentation sites
- `landing-page` — Marketing landing pages
- `mobile-app` — React Native / Expo mobile apps
- `desktop-app` — Tauri / Electron desktop apps
- `ai-rag` — AI/RAG pipelines with vector search
- `fintech` — Financial services (compliance-ready)
- `fullstack-api` — Backend APIs with frontend

**12 Stack Bundles (all full scaffold):**
- `react-static` — React + TypeScript + Vite + TailwindCSS
- `nextjs-supabase` — Next.js + Supabase (PostgreSQL)
- `fastapi-postgres` — FastAPI + PostgreSQL
- `dotnet-postgres` — .NET + PostgreSQL
- `nextjs-dotnet-postgres` — Next.js + .NET + PostgreSQL
- `ai-rag-python` — Python RAG pipeline (LangChain + pgvector)
- `expo-supabase-mobile` — Expo + Supabase mobile
- `nestjs-postgres` — NestJS + PostgreSQL
- `tauri-react-sqlite` — Tauri + React + SQLite
- `nextjs-vercel` — Next.js optimized for Vercel
- `vue-lite` — Vue 3 + Vite + TailwindCSS
- `business-website` — General business website

### Scaffold Support (Honest Status)

| Bundle | Scaffold Support | Meaning |
|---|---|---|
| `react-static` | **FULL** | Functional React + TypeScript + Vite + TailwindCSS source scaffolded from offline templates. |
| All other bundles | **METADATA-ONLY** | Canonical state + portable resources only; no application source code was created. |

A metadata-only bundle may still be generated as AI-Coding-starter state, but the user is told explicitly that application source code was **not** scaffolded. No bundle pretends to be more than it is.

---

## CLI Commands Reference

```bash
# Project creation (interactive wizard)
python new_project.py

# Analytics dashboard
python new_project.py --stats

# Agent management
python new_project.py --list-agents --project <path>
python new_project.py --deploy-agents --project <path> [--agent-task "task description"]

# Runtime switching
python new_project.py --switch-runtime <runtime> --project <path>
# runtimes: portable, codex, opencode, antigravity, claude-code, cursor

# Resource lock & upstream sync
python new_project.py --init-upstream --project <path>
python new_project.py --sync-upstream --project <path>
python new_project.py --check-updates --project <path>
python new_project.py --verify-lock --project <path>

# Validation
python new_project.py --validate-schema --project <path>

# Quality gates
python -m core.benchmarks
python -m core.integration_test_matrix
```

---

## Portable State

Every generated project contains exactly one `.ai-coding-starter/`:

```
project/
  .ai-coding-starter/
    project.yaml     # machine-authoritative identity, type, capabilities, bundle, team_pack, specialists
    state.yaml       # workflow/session phase and focus
    resources.lock   # selected resources + provenance + content_hash + size_bytes + selection reasons
    upstream-sources.yaml  # upstream catalog sources for sync (optional)
```

**Derived, human-readable Markdown** (regenerated from canonical state):
- `AGENTS.md` — Project overview + active agents + team pack + specialists
- `CONTEXT.md` — Project identity + workflow state + tasks
- `DECISIONS.md` — Append-only architecture decision history
- `HANDOFF.md` — Concise continuation interface

**Portable AI Workspace** (`.ai-workspace/`):
```
.ai-workspace/
  agents/      # active agent definitions
  skills/      # active skill definitions
  workflows/   # active workflow definitions
  rules/       # active rule files
  scripts/     # active executable scripts
  shared/      # shared module directories
```

Runtime adapters derive their vendor-specific files from this workspace. Canonical state (`.ai-coding-starter/`) remains the machine authority.

---

## Optional Intelligence Integrations

Codebase Memory (CBM), Agent-Reach, and Orca are **optional and fail-open** — they are never dependencies of project creation or portable state.

**Agency Agents** (msitarzewski/agency-agents, MIT) is imported as the canonical specialist knowledge base at `catalog/agency-agents.yaml` (268 agents across 18 divisions, pinned commit `b859c515d813efcfc4755d3471dd9e7686c7706d`). It is **not a runtime dependency**: end-user project generation remains offline and activates only a small bounded team selected by the deterministic resolver.

**IMPORT ALL ≠ ACTIVATE ALL:** The full Agency catalog is available to the resolver as a knowledge base, but only the relevant specialists for your project type and capabilities are activated. A typical project gets a small team (default hard ceiling of 10 agents) — never the entire catalog.

No permission-bypass flags (`--yolo`, `--dangerously-skip-permissions`, `--dangerously-bypass-approvals-and-sandbox`) are ever used.

---

## Documentation

| Document | Description |
|---|---|
| `docs/RUNTIME_ADAPTERS.md` | Architecture, config examples, extension guide for 4 adapters |
| `docs/AGENT_MANAGER.md` | Bridge API, team packs, core team, specialists, CLI commands |
| `docs/RESOURCE_LOCK.md` | Lock structure, upstream sources, content hashing, CLI, CI integration |

---

## Attribution & Third-Party Notices

- **AI-Coding-starter bundled resources**: locally authored, MIT (see `catalog/upstream-sources.yaml`, source `ai-coding-starter-bundled`).
- **Agency Agents** (msitarzewski/agency-agents): MIT — imported as the canonical specialist knowledge base at `catalog/agency-agents.yaml` (268 agents, 18 divisions, pinned commit `b859c515d813efcfc4755d3471dd9e7686c7706d`). Full provenance in `catalog/upstream-sources.yaml` and `THIRD_PARTY_NOTICES.md`.
- **Agent-Reach**, **Orca**, **Codebase Memory MCP**: MIT — optional external integrations only.
- **OpenMontage**: AGPL-3.0 — architectural inspiration only (declarative manifests, approval gates); no source copied.

See `THIRD_PARTY_NOTICES.md` and `catalog/upstream-sources.yaml` for full provenance, commit SHAs, and licenses.

---

## License

MIT License — see [LICENSE](LICENSE).

---

## Project Status

| Phase | Status | Tests |
|---|---|---|
| V2.0 Core (canonical state, resolver, portable workspace) | ✅ Complete | 555 |
| M9: CBM (Capability Provider Registry) | ✅ Complete | 27 |
| M10: Agent-Reach (Registry lookup + fetch) | ✅ Complete | 18 |
| M11: Orca (Spec-driven generation) | ✅ Complete | 18 |
| Scaffold Roadmap (12 bundles, 163+ templates) | ✅ Complete | — |
| **Phase 3: Agency Specialist Integration** (108 specialists, 7 team packs) | ✅ Complete | — |
| **Runtime Adapters** (Codex, OpenCode, Claude, Cursor) | ✅ Complete | — |
| **Agent Manager Bridge** (origin CLI integration) | ✅ Complete | — |
| **Resource Lock & Upstream Sync** (SHA256, git sync, 4 CLI) | ✅ Complete | — |
| **JSON Schema Validation** (Draft-07) | ✅ Complete | — |
| **Quality Gates** (benchmarks, integration matrix) | ✅ Complete | — |
| **Documentation** (3 guides) | ✅ Complete | — |
| **TOTAL** | ✅ **618 tests passing** | **618** |

---

**Made with ❤️ for the developer community** 🌍
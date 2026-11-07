# Changelog

## [2.1.1] — Portable Workspace & Resolver Hotfix

### Fixed
- Capability-gated resources (e.g. `security-auditor`) were selected
  unconditionally for project types that did not select the matching
  capability (portfolio received an authentication security agent with no
  authentication capability). Resources now carry an explicit `when`
  activation condition (`always` / `capabilities_any` / `capabilities_all`
  / `stack_bundles` / `project_types`) and `selection_reason` describes what
  actually triggered selection.
- Phantom Agency resources in Portable projects: every locked active resource
  is now materialized under `.ai-workspace/` (agents from agency metadata
  when no bundled file exists), enforcing LOCKED ACTIVE RESOURCE →
  MATERIALIZED PORTABLE RESOURCE.
- Legacy GEMINI/V2 instruction conflicts: `copy_selective()` no longer
  generates root `GEMINI.md` and `generate_gemini_md()` no longer runs as
  the generic V2 generation step. Only the Antigravity runtime adapter may
  emit `.agent/GEMINI.md`. New Portable/Codex/OpenCode/Claude/Cursor
  projects do not contain root `GEMINI.md`.
- Stale runtime menu paths: runtime descriptions are loaded from the
  adapter catalog (`catalog/runtime-capabilities.yaml`) instead of
  hardcoded stale paths.
- Capability metadata inconsistency: all generated documentation derives
  from the same resolved canonical spec; no parallel legacy tech-stack
  object overrides canonical capability state.

### Improved
- Portable, runtime-neutral AI workspace (`.ai-workspace/` with
  `agents/`, `skills/`, `workflows/`, `rules/`, `shared/`) as the canonical
  portable resource layer, alongside machine-authoritative
  `.ai-coding-starter/`.
- Specialty-aware Agency agent scoring (execution-pack role, capability,
  project-type, stack/technology, specialty/tag, division relevance; id is
  the final tie-break) with explainable score breakdown.
- Complexity-aware team sizing (minimal/static 4-6, balanced 5-8, complex
  6-10; hard ceiling 10) derived from the stack bundle profile.
- Terminal UI colors and readability: centralized `core/cli_ui.py` with
  semantic ANSI styling, TTY/NO_COLOR/--no-color/Windows graceful fallback.
- Generated stack scaffolding: `react-static` now produces a functional
  React + TypeScript + Vite + TailwindCSS app (package.json, tsconfig.json,
  vite.config.ts, src/, public/, .gitignore, README.md).
- Runtime switching: `python new_project.py --switch-runtime <id> --project <.>`
  preserves canonical state and the portable workspace; only runtime-owned
  derived files change.

### Changed
- `VERSION` bumped to 2.1.1.
- Portfolio base resources now focus on project planning, frontend, design,
  accessibility, SEO, performance and deployment; `security-auditor`,
  `api-documenter` and `api-standards` are not auto-selected unless
  capabilities/stack require them.
- Runtime selection defaults to Portable.

### Removed
- Legacy V1 root-level `agents/`, `skills/`, `.shared/`, `workflows/`,
  `core/`, `rules/` generation from new V2 projects (replaced by the
  portable `.ai-workspace/`).

## [2.1.0] — Agency Agents Integration

### Added
- Full pinned Agency Agents catalog integration (msitarzewski/agency-agents)
- 268 agents across 18 specialist divisions
- Canonical catalog at `catalog/agency-agents.yaml` produced by maintainer-side importer `scripts/sync_agency_agents.py`
- Pinned upstream commit `b859c515d813efcfc4755d3471dd9e7686c7706d` (MIT license)
- Full provenance per agent: upstream repo, commit SHA, license, import date, SHA-256 content hash
- Resource registry (`core/resource_registry.py`) for bundled + agency-agents canonical resources
- Deterministic bounded specialist resolver (`core/resource_resolver.py`) with hard ceiling of 10 agents
- Execution packs (`catalog/execution-packs.yaml`, `core/execution_pack_registry.py`):
  - Agency-derived: startup-mvp, enterprise-feature, marketing-campaign, incident-response
  - AI-Coding-starter native: feature-development, bug-fix, refactor, code-review, security-audit, performance-investigation, ai-rag-development
- Runtime-native Agency agent rendering for Codex, OpenCode, Antigravity, Claude Code, Cursor (`core/generic-renderer.py` `render_agents()`)
- GitHub Actions CI (Ubuntu + Windows, Python 3.11)

### Fixed
- Transactional project generation: build into staging directory, atomically finalize; rollback staging on failure
- Zero-side-effect cancellation: parent directory not created before explicit user confirmation
- CWD-independent runtime adapter discovery
- Honest runtime install status: PARTIAL_SUCCESS instead of unconditional success
- Resource-root consistency: resolver and copier use same effective authority
- Cross-platform path tests CI-safe (resolved path comparison, PureWindowsPath semantics)

### Changed
- `catalog/upstream-sources.yaml`: Agency Agents reclassified from `architectural-inspiration` to `imported-catalog`
- `THIRD_PARTY_NOTICES.md`: Agency Agents imported-catalog entry with 268 agent records
- README: V2.1.0 runtime-native documentation

### Removed
- None

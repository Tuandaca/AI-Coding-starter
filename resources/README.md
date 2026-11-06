# Bundled Resources

This directory contains the self-contained resource set bundled with
AI-Coding-starter V2 for offline project generation.

## Provenance

All files under `resources/` were newly created for AI-Coding-starter V2
Milestone M2 (Self-contained Resource Migration). They are NOT copied from
any external template, upstream repository, or third-party source.

## Resource Categories

| Category | Purpose |
|---|---|
| `agents/` | Agent definitions (frontend-specialist, project-planner, orchestrator, etc.) |
| `skills/` | Skill definitions (modern-web-architect, seo-expert-kit, api-documenter, etc.) |
| `shared/` | Shared modules and design system assets |
| `workflows/` | Workflow definitions (create, enhance, preview, deploy, etc.) |
| `scripts/` | Utility scripts (auto_preview.py, checklist.py, verify_all.py) |
| `core/` | Core configuration files |
| `rules/` | Lint and formatting rules |

## Migration Notes

Migrated from the legacy external master-template dependency:

- The legacy V1 generator required an external template clone at
  `D:\VibeCoding-Template\.agent` (or similar machine-specific path).
- M2 eliminates this dependency by bundling the minimal resource set
  required for generator operation directly in the starter repository.
- `MASTER_TEMPLATE_PATH` in `config.json` is now optional; when set to a
  valid external path, it serves as a fallback only if bundled resources
  are unavailable.
- All resource discovery uses `Path(__file__).parent / "resources"`,
  which is repository-relative and works on Windows and POSIX.

## License

All bundled resources are original content created for AI-Coding-starter
and are covered by the repository's MIT License (see LICENSE).

## M7 Traceability

Full provenance tracking (`catalog/upstream-sources.yaml`,
`resources.lock` resolution, `THIRD_PARTY_NOTICES.md` workflow) is
deferred to Milestone M7.

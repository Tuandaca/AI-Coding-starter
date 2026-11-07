# Third-Party Notices

This file provides human-readable license and provenance notices for
AI-Coding-starter V2. It complements the machine-readable provenance catalog at
`catalog/upstream-sources.yaml`. It does not duplicate the entire catalog.

## Bundled resources (locally authored)

All files under `resources/` were newly created for AI-Coding-starter V2
Milestone M2. They are NOT copied from any external template, upstream
repository, or third-party source. They are covered by the repository's MIT
License (see `LICENSE`).

Snapshot: `8b61d297dc07772a000b85fc93138c8aefd21c45` (M2).
Reviewed: 2026-11-06.

## Audited upstream sources

The following upstream projects were reviewed for provenance tracking. None
are imported into generated projects by M7 unless noted.

| Source | Repository | Commit SHA | License | Classification | Imported resources |
|---|---|---|---|---|---|
| AI-Coding-starter Bundled Resources | (local) | 8b61d297dc07772a000b85fc93138c8aefd21c45 | MIT | bundled-local | 60 resource files (58 unique IDs) |
| Agency Agents | https://github.com/msitarzewski/agency-agents | b859c515d813efcfc4755d3471dd9e7686c7706d | MIT | imported-catalog | 268 agent records (catalog/agency-agents.yaml) |
| Agent-Reach | https://github.com/Panniantong/Agent-Reach | 47898829204ad27521d8a1719e3aeca3b8a3e0ca | MIT | optional-external-integration | none |
| Orca | https://github.com/orca-cli/orca | 5beeefcb57555962bb93facc54b5f82484731802 | MIT | optional-external-integration | none |
| Codebase Memory MCP | https://github.com/DeusData/codebase-memory-mcp | 612eee2518ef84cc573e491fdee5fa5c90264cb5 | MIT | optional-external-integration | none |
| OpenMontage | https://github.com/calesthio/OpenMontage | d21f5d4eaa08422b09c7091757a05affcbabb35b | AGPL-3.0 | architectural-inspiration | none |

## Agency Agents imported catalog

Agency Agents (MIT) is imported as the canonical specialist knowledge base at
`catalog/agency-agents.yaml`, produced by the maintainer-side importer
`scripts/sync_agency_agents.py` from upstream commit
`b859c515d813efcfc4755d3471dd9e7686c7706d`. The catalog contains all
268 agents across 18 divisions. Each record carries full provenance (upstream
repository, commit SHA, license, import date, and per-agent SHA-256 content
hash). Agency Agents is a **knowledge base only** — it is not a runtime
dependency, and end-user project generation activates only a small bounded
team of agents selected by the deterministic resolver (never the full catalog).

## OpenMontage license firewall

OpenMontage is licensed AGPL-3.0 and is classified as
architectural-inspiration only. NO OpenMontage source code is copied into this
MIT-licensed project. No OpenMontage resources are imported into generated
projects. Declarative pipeline manifest, scored provider selection, and approval
gate concepts are adopted as architecture only; no source is copied.

## Notes

- `catalog/upstream-sources.yaml` is the authoritative machine-readable
  provenance catalog. This file is a human-readable convenience view.
- Upstream verification/update is a maintainer-only operation
  (`docs/upstream-update-workflow.md`). End-user project generation requires
  no network access.

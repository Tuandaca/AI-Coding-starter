# Changelog

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

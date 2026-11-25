# FINAL_STABILIZATION_PLAN.md

STATUS: AWAITING USER APPROVAL

IMPLEMENTATION AUTHORIZED: NO

No source-code, test, workflow, configuration, documentation, version, tag, or release modification is authorized yet.

## 1. Baseline
- Branch master, HEAD 07cb28865ee75ffbd831b43b8c82deaa7dc1a5bc
- Remote master HEAD identical; working tree clean
- Tags: v2.2.0 (a303f2c, immutable), v2.1.1, v2.1.0, v2.0.1
- VERSION=2.2.0, pyproject.toml=2.1.1 (drift)
- SCAFFOLD_SUPPORT canonical in core/stack_scaffold.py (11 FULL incl. tauri)
- full-scaffold-validation.yml omits tauri-react-sqlite
- Target release v2.2.1
- Implementation branch: fix/v2.2.1-final-stabilization

## 2. Target architecture
- Canonical scaffold support: SCAFFOLD_SUPPORT in core/stack_scaffold.py
- Canonical validation: derive per-bundle validator from a single registry keyed by SCAFFOLD_SUPPORT; no FULL_BUNDLES list
- Version authority: VERSION file; pyproject/README/PROJECT_STATUS derived/synced
- CI reuse: reusable workflow for core validation called for Ubuntu+Windows
- Release gate: exact tag commit passes Ubuntu+Windows+all FULL scaffolds+security+consistency

## 3. Root-cause map
- RC-SCF-GENERIC: generic npm build assumes build script -> stack-aware validators
- RC-SCF-IMPORTS: FastAPI/AI-RAG relative import depth -> audit all emitted imports
- RC-CI-RELEASE: Ubuntu-only release + tag ref risk -> reusable workflow + explicit ref
- RC-VERSION: drift -> single authority
- RC-DOC: stale -> consistency tests
- RC-SEC-PATH: component checks -> resolved containment

## 4. Execution phases
Phase 0 freeze/baseline; Phase 1 scaffold build defects (react-static, fastapi, ai-rag); Phase 2 canonical validation arch (npm policy, expo, tauri, support registry); Phase 3 security (path containment, subprocess); Phase 4 CI architecture; Phase 5 release gate; Phase 6 version/docs; Phase 7 remote validation; Phase 8 release decision.

## 5. Detailed tasks

### Task SCF-REGISTRY-01
Severity: P1 | Phase 2
Problem: Duplicated/hard-coded scaffold validation lists risk drift from SCAFFOLD_SUPPORT.
Evidence: full-scaffold-validation.yml matrix lists 10 bundles; SCAFFOLD_SUPPORT lists 11 incl. tauri.
Root cause: No single canonical mapping from support level to validator.
Affected files: core/stack_scaffold.py, scripts/ci_validate_scaffolds.py, .github/workflows/*.yml
Exact planned modification: Add a canonical BUNDLE_VALIDATORS registry in core/stack_scaffold.py mapping each FULL bundle to its validation command set; generate CI matrices from it; remove any independent FULL_BUNDLES lists.
Do NOT change: support levels semantics; metadata-only bundles.
Tests: unit test that every FULL bundle has a validator entry and every validator entry is FULL.
Local verification: python -m unittest tests/test_stack_bundles_catalog.py
Remote CI: consistency check passes.
Acceptance: no duplicated FULL lists; matrices derived from canonical data.
Dependencies: none (SCF-TAURI-01 depends on this, not vice versa)
Risk: low. Rollback: revert registry addition.

### Task SCF-REACT-01
Severity: P0 | Phase 1
Problem: react-static build fails TS6310 "Referenced project tsconfig.node.json may not disable emit."
Evidence: remote CI TS6310.
Root cause: tsconfig.node.json has noEmit true while composite/project references require emit for referenced projects; Vite expects project references with composite and emit.
Affected files: generated react-static tsconfig.json, tsconfig.node.json, vite.config.ts, package.json (in core/stack_scaffold.py templates)
Exact planned modification: Set tsconfig.node.json composite true and remove noEmit (or set noEmit false) so referenced project emits; ensure tsconfig.json references tsconfig.node.json; align Vite build with project references; document why.
Do NOT change: unrelated compiler strictness.
Tests: generated react-static npm install + npm run build smoke.
Local verification: generate + cd + npm install + npm run build.
Remote CI: fast-scaffolds react-static job PASS.
Acceptance: build PASS on remote Ubuntu.
Dependencies: none.
Risk: medium. Rollback: revert template change.

### Task SCF-FAPI-01
Severity: P0 | Phase 1
Problem: FastAPI relative import depth wrong causing ModuleNotFoundError src.api.database.
Evidence: remote CI traceback.
Root cause: imports under src/api/routes and src/api use incorrect relative depth.
Affected files: core/stack_scaffold.py FASTAPI templates (src/main.py, src/api/deps.py, src/api/routes/*, src/models/*, src/schemas/*, src/services/*, migrations/*)
Exact planned modification: Inspect the actual generated package hierarchy first; then audit every import in all listed modules and correct relative depths according to the real package structure (do not assume a fixed depth or reuse examples blindly); do not change package hierarchy.
Do NOT change: package layout.
Tests: generated FastAPI compileall + from src.main import app + route module smoke imports.
Local verification: python -m compileall . ; python -c "from src.main import app"; python -c "import src.api.routes.users"
Remote CI: fastapi-postgres job PASS.
Acceptance: all imports resolve.
Dependencies: none.
Risk: medium. Rollback: revert template.

### Task SCF-RAG-01
Severity: P0 | Phase 1
Problem: AI-RAG likely same import defect.
Evidence: suspicious imports from ..database in routes and .config in models.
Root cause: same relative-depth mistake.
Affected files: core/stack_scaffold.py AI_RAG templates (src/api/routes/documents.py, src/api/routes/chat.py, src/models/document.py, src/services/*)
Exact planned modification: Independent full audit; inspect actual generated package hierarchy first; correct all relative imports under src/api, src/models, src/services, src/main according to real package structure; do not assume FastAPI corrections apply.
Do NOT change: package layout.
Tests: compileall + from src.main import app + documents/chat smoke imports.
Local verification: as above.
Remote CI: full-scaffold ai-rag-python PASS.
Acceptance: imports resolve.
Dependencies: none.
Risk: medium. Rollback: revert.

### Task SCF-NPM-01
Severity: P1 | Phase 2
Problem: Inconsistent npm install strategy (ci uses npm ci || npm install; release uses npm ci; generated projects lack lockfile).
Evidence: workflows + generated package.json.
Root cause: no single policy.
Affected files: .github/workflows/ci.yml, full-scaffold-validation.yml, release-validation.yml, scripts/ci_validate_scaffolds.py, core/stack_scaffold.py
Exact planned modification: Decide npm install policy. Since generated scaffolds do not generate package-lock.json, use `npm install` consistently across all gates; document tradeoff (npm ci requires committed lockfile). Alternatively generate lockfile during scaffold and use npm ci. Prefer npm install for coherence and simplicity; explain.
Do NOT change: package dependencies.
Tests: consistency check verifies same install command across workflows.
Local verification: grep workflows for install commands.
Remote CI: all Node scaffold jobs PASS.
Acceptance: single policy documented and enforced.
Dependencies: SCF-REGISTRY-01
Risk: low. Rollback: revert.

### Task SCF-EXPO-01
Severity: P1 | Phase 2
Problem: Generic CI runs npm run build on Expo which has no build script.
Evidence: expo package.json scripts.
Root cause: generic build assumption.
Affected files: .github/workflows/*.yml, scripts/ci_validate_scaffolds.py, core/stack_scaffold.py
Exact planned modification: Stack-aware validation: Expo uses npm install + npm run typecheck + Expo config validation (npx expo config / expo-doctor where appropriate). No npm run build.
Do NOT change: Expo scripts.
Tests: Expo job runs typecheck.
Local verification: generate + npm install + npm run typecheck.
Remote CI: Expo job PASS.
Acceptance: no false build failure.
Dependencies: SCF-REGISTRY-01, SCF-NPM-01
Risk: low. Rollback: revert.

### Task SCF-TAURI-01
Severity: P1 | Phase 2
Problem: tauri-react-sqlite marked FULL but omitted from release validation.
Evidence: SCAFFOLD_SUPPORT + full-scaffold-validation.yml matrix.
Root cause: inconsistent support contract.
Affected files: core/stack_scaffold.py, full-scaffold-validation.yml, README, PROJECT_STATUS
Exact planned modification: Choose PARTIAL unless CI can provide Rust/Cargo/Tauri native deps and cargo check passes. If FULL, add toolchain setup and cargo check to validation. If PARTIAL, change SCAFFOLD_SUPPORT to "partial" and update docs. Recommend PARTIAL initially with documented reason; FULL only after toolchain gate proven.
Do NOT change: scaffold generation.
Tests: support classification consistency test.
Local verification: n/a for Rust unless installed.
Remote CI: if FULL, tauri job PASS.
Acceptance: exactly one honest state.
Dependencies: SCF-REGISTRY-01
Risk: medium. Rollback: revert level.

### Task SEC-PATH-01
Severity: P1 | Phase 3
Problem: Path containment uses component checks only; may allow absolute/UNC/drive paths.
Evidence: current implementation parts check.
Root cause: no resolved-root verification.
Affected files: core path handling (search for parts == ".."), tests/test_runtime_path_escape.py
Exact planned modification: Implement resolved target containment: resolve destination root and target; ensure target is within root using Path.resolve() and relative_to(); handle Windows/POSIX. Add tests for ../evil.txt, ../../evil.txt, nested/../../../evil.txt, /tmp/evil.txt, C:\evil.txt, C:/evil.txt, \\server\share\evil.txt, valid/nested/file.txt.
Do NOT change: valid file operations.
Tests: all listed cases.
Local verification: python -m unittest tests/test_runtime_path_escape.py
Remote CI: security job PASS.
Acceptance: all traversal attempts blocked; valid paths allowed.
Dependencies: none.
Risk: medium (Windows semantics). Rollback: revert.

### Task SEC-SUBPROCESS-01
Severity: P2 | Phase 3
Problem: get_cmd_output uses shlex.split; potential parsing/quote issues.
Evidence: call sites git config, node -v, python --version, etc.
Root cause: string-based API.
Affected files: utility defining get_cmd_output and all callers.
Exact planned modification: Change signature to get_cmd_output(args: Sequence[str]); update all callers to pass explicit arrays; remove shlex; use subprocess with list args; no shell.
Do NOT change: command behavior.
Tests: existing setup/security tests.
Local verification: python -m compileall; unittest.
Remote CI: PASS.
Acceptance: no shell=True; all callers updated.
Dependencies: none.
Risk: low. Rollback: revert.

### Task CI-REUSE-01
Severity: P1 | Phase 4
Problem: Duplicated CI logic; no Windows core gate in release.
Evidence: ci.yml, release-validation.yml.
Root cause: separate workflows.
Affected files: .github/workflows/ci.yml, release-validation.yml, new reusable workflow
Exact planned modification: Create reusable core-validation workflow (workflow_call) running Ubuntu+Windows core tests; ci.yml calls it; release calls it. Avoid duplication.
Do NOT change: test commands.
Tests: workflow syntax.
Local verification: act or manual review.
Remote CI: both OS PASS.
Acceptance: core validation shared.
Dependencies: none.
Risk: medium. Rollback: revert workflows.

### Task REL-TAG-01
Severity: P0 | Phase 5
Problem: Release may validate different commit than tag; Ubuntu-only.
Evidence: release.yml/release-validation.yml.
Root cause: ref semantics and single-OS gate.
Affected files: .github/workflows/release.yml, release-validation.yml
Exact planned modification: Ensure checkout uses ref: ${{ github.ref }} (exact tag) in all jobs including publish; require reusable core validation (Ubuntu+Windows) + all FULL scaffolds + security + consistency before publish; no publish on failure.
Do NOT change: publish mechanism.
Tests: workflow review.
Local verification: inspect.
Remote CI: tag push dry run (not performed now).
Acceptance: validated commit == released tag commit.
Dependencies: CI-REUSE-01, SCF-REGISTRY-01
Risk: high. Rollback: revert workflows.

### Task VER-01
Severity: P1 | Phase 6
Problem: Version drift across authorities.
Evidence: VERSION 2.2.0 vs pyproject 2.1.1; generated strings v2.1.1.
Root cause: multiple uncoordinated version sources.
Affected files: VERSION, pyproject.toml, README.md, PROJECT_STATUS.md, CHANGELOG.md, core/stack_scaffold.py generated strings, release metadata
Exact planned modification: Make VERSION canonical; bump once directly to 2.2.1 at the end of stabilization (no intermediate 2.2.0 sync); update all user-visible strings; add consistency check.
Do NOT change: v2.2.0 tag.
Tests: test_version_identity.py.
Local verification: grep version strings.
Remote CI: consistency PASS.
Acceptance: all authorities agree.
Dependencies: late (after functional fixes).
Risk: low. Rollback: revert.

### Task DOC-01
Severity: P2 | Phase 6
Problem: README/PROJECT_STATUS stale counts and contradictory support claims.
Evidence: README 618 tests vs 624; 10 types vs 16; 12 bundles vs 11; etc.
Root cause: duplicated facts drift.
Affected files: README.md, PROJECT_STATUS.md, tests/test_*consistency*, scripts/ci_consistency_check.py
Exact planned modification: Add automated consistency checks comparing README/PROJECT_STATUS to canonical catalogs (project types, bundles, support levels, runtime list, test count, version). Update docs to match. Define what belongs in each doc.
Do NOT change: canonical catalogs.
Tests: new consistency tests.
Local verification: python scripts/ci_consistency_check.py
Remote CI: PASS.
Acceptance: no stale counts.
Dependencies: VER-01
Risk: low. Rollback: revert docs.

### Task REL-META-01
Severity: P3 | Phase 6
Problem: Existing v2.2.0 release body may be stale.
Evidence: prior review.
Root cause: historical metadata.
Affected files: GitHub release v2.2.0 (remote only)
Exact planned modification: Inspect release body; decide leave as historical record (recommended) vs limited metadata corrections; never move tag.
Do NOT change: tag.
Tests: n/a.
Local verification: gh release view v2.2.0
Remote CI: n/a.
Acceptance: documented decision.
Dependencies: none.
Risk: low. Rollback: n/a.

### Task BRANCH-PROTECT-01
Severity: P2 | Phase 7 (manual admin)
Problem: master not protected.
Evidence: protected: false.
Root cause: settings.
Affected files: GitHub repo settings (manual)
Exact planned modification: Enable branch protection requiring relevant status checks; prevent merge on failure; optionally restrict direct pushes.
Do NOT change: code.
Tests: n/a.
Local verification: gh api repos/.../branches/master/protection
Remote CI: n/a.
Acceptance: protected true.
Dependencies: remote CI green.
Risk: low. Rollback: disable protection.

## 6. Test strategy
- Generated scaffold import smoke tests for FastAPI and AI-RAG.
- react-static npm run build in CI.
- Security containment tests (listed cases).
- Consistency tests for README counts vs catalogs.
- Support registry tests.

## 7. Remote CI strategy
- Create fix/v2.2.1-final-stabilization
- Implement tasks
- Local full validation
- Push branch
- Observe GitHub Actions
- Fix legitimate issues
- Repeat until green
- Merge to master
- Master CI green
- Only then request tag/release approval

## 8. Version/release strategy
- v2.2.0 immutable; v2.2.1 after green; bump late.

## 9. Branch protection/admin steps
- BRANCH-PROTECT-01 manual.

## 10. Implementation tracking
- [ ] SCF-REGISTRY-01
- [ ] SCF-REACT-01
- [ ] SCF-FAPI-01
- [ ] SCF-RAG-01
- [ ] SCF-NPM-01
- [ ] SCF-EXPO-01
- [ ] SCF-TAURI-01
- [ ] SEC-PATH-01
- [ ] SEC-SUBPROCESS-01
- [ ] CI-REUSE-01
- [ ] REL-TAG-01
- [ ] VER-01
- [ ] DOC-01
- [ ] REL-META-01
- [ ] BRANCH-PROTECT-01

## 11. Handoff context
- Current master SHA: 07cb28865ee75ffbd831b43b8c82deaa7dc1a5bc
- Failed CI: remote red on scaffold jobs (react-static TS6310, fastapi imports)
- Architecture constraints: preserve .ai-coding-starter/, .ai-workspace/, deterministic resolver, resource applicability engine, agency specialist catalog, transactional generation, runtime-neutral canonical state, fail-open optional integrations
- Files to inspect first: core/stack_scaffold.py, scripts/ci_generate_scaffold.py, scripts/ci_validate_scaffolds.py, .github/workflows/*
- Commands: python -m unittest discover -s tests -t . ; python scripts/ci_consistency_check.py
- Expected release: v2.2.1
- Must not rewrite: v2.2.0 tag, production architecture

## 12. Approval gate
AWAITING USER APPROVAL. IMPLEMENTATION AUTHORIZED: NO.

## Final completion criteria
0 unresolved P0/P1 release blockers; Ubuntu+Windows core PASS; runtime isolation/switching PASS; every FULL scaffold PASS remotely; security+consistency PASS; docs/version synchronized; master remote CI GREEN.

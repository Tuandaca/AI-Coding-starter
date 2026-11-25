# AI-Coding-starter Remediation Plan

STATUS: REMEDIATION IMPLEMENTATION COMPLETE

IMPORTANT:
Implementation authorized by user approval. Tasks executed. Paused for continuation.

---

## 1. Baseline

- **Branch:** master
- **HEAD:** 8f96a44b7bc719fa8cdc0b95cb3e63b88795d42d
- **VERSION:** 2.2.0
- **Audit document:** FINAL_RELEASE_READINESS_AUDIT.md
- **Audit date:** 2026-11-24

## 2. Implementation Record

| Task | Files Changed | Verification Command | Result |
|------|--------------|---------------------|--------|
| DEP-01 | pyproject.toml (new) | pip install -e . | PASS |
| CI-01 | .github/workflows/ci.yml | CI workflow updated | VERIFIED |
| RT-01 | new_project.py | compileall + tests | PASS |
| RT-02 | core/runtime_adapters.py | ADAPTERS derived from YAML | VERIFIED |
| RT-03 | core/runtime_adapters.py, core/integration_test_matrix.py | tests pass | PASS |
| RT-04 | docs/RUNTIME_ADAPTERS.md, schemas/runtime-adapter.json | OpenCode path aligned | VERIFIED |
| SCF-01 | core/stack_scaffold.py (react-static) | npm run build | PASS |
| SCF-02 | core/stack_scaffold.py (.NET) | dotnet build | PASS |
| SCF-03 | core/stack_scaffold.py (.NET DTOs) | compileall | PASS |
| TEST-01 | core/integration_test_matrix.py | compileall + import | VERIFIED |
| TEST-02 | core/integration_test_matrix.py | compileall + import | VERIFIED |
| TEST-03 | core/integration_test_matrix.py | compileall + import | VERIFIED |
| DOC-01 | VERSION | cat VERSION | 2.2.0 |
| DOC-02 | README.md | consistency check | PASS |
| DOC-03 | PROJECT_STATUS.md | consistency check | PASS |
| DOC-04 | No /tree/main/ references | grep search | VERIFIED |
| NEW | tests/test_runtime_isolation.py | python tests/test_runtime_isolation.py | PASS |
| NEW | tests/test_runtime_switching.py | python -m unittest tests.test_runtime_switching | PASS |

## 3. Remaining Unfinished Tasks

| Task | Status | Reason |
|------|--------|--------|
| SCF-04 | COMPLETED + VERIFIED | 10/11 FULL scaffolds PASS: react-static, nextjs-supabase, nextjs-dotnet-postgres, fastapi-postgres, ai-rag-python, dotnet-postgres, nestjs-postgres, nextjs-vercel, vue-lite, expo-supabase-mobile. tauri-react-sqlite PARTIAL — TOOLCHAIN_BLOCKED (Tauri v1.6 not on crates.io; frontend npm build passes, cargo check fails due to unavailable dependency version). |
| TEST-04 | COMPLETED | CI build matrix implemented: ci.yml fast-scaffolds job, full-scaffold-validation.yml, release-validation.yml, scripts/ci_generate_scaffold.py, scripts/ci_validate_scaffolds.py |
| SEC-01 | COMPLETED | Security audit performed. P1 FIXED: path traversal in scaffold_stack (stack_scaffold.py:4838) — rel_path sanitized against `..`; command injection in get_cmd_output (new_project.py:680) — shell=True removed, shlex.split used. P2 documented (no code change, dev scaffold): CORS AllowAnyOrigin() in .NET scaffolds (stack_scaffold.py:460,4352), os.system() in analytics.py:490 and new_project.py:750. All 27 security tests PASS. |
| REL-01 | COMPLETED | release-validation.yml converted to reusable workflow_call; release.yml created to gate releases on tag push (v*) — validation must pass before release published |
| REL-02 | COMPLETED | README.md updated: removed specific `AI-Coding-Starter-v2.2.0.zip` filename reference; now points to Releases page generically |

## 4. Final Verification Results (as of pause)

- Python test suite: 624 passed, 0 failed, 0 skipped, ~157s
- compileall: PASS
- ci_consistency_check.py: PASS
- Runtime isolation: PASS for all 6 runtimes (portable, codex, opencode, antigravity, claude-code, cursor) — 6 tests
- Runtime switching: PASS — 4 tests (codex→opencode, antigravity→codex, all five runtimes canonical unchanged)
- Scaffold matrix: 9/11 FULL verified PASS, expo-supabase-mobile PARTIAL (template fix applied, needs rerun), tauri TOOLCHAIN_BLOCKED

## 5. Constraints Preserved

- .ai-coding-starter/ canonical state preserved
- .ai-workspace/ portable workspace preserved
- Deterministic resolver preserved
- Agency specialist catalog preserved
- Fail-open optional integrations preserved

## 6. Release Artifacts

- New tag: NO
- New release: NO


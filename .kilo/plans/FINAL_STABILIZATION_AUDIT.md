# FINAL_STABILIZATION_AUDIT.md

## Repository baseline
- Branch: master
- Local HEAD: 07cb28865ee75ffbd831b43b8c82deaa7dc1a5bc
- Remote master HEAD: 07cb28865ee75ffbd831b43b8c82deaa7dc1a5bc
- Working tree: clean
- Latest tags: v2.2.0 (a303f2c...), v2.1.1, v2.1.0, v2.0.1
- VERSION=2.2.0, pyproject.toml=2.1.1 (drift confirmed)
- SCAFFOLD_SUPPORT canonical in core/stack_scaffold.py (11 FULL incl. tauri)
- full-scaffold-validation.yml omits tauri-react-sqlite (inconsistency confirmed)
- Generic CI build runs npm ci || npm install then npm run build (expo risk)
- expo-supabase-mobile has no build script (per prior review; verify)

## Root causes
1. Generic Node build assumes `npm run build` for all bundles.
2. FastAPI/AI-RAG relative import depth (audit needed).
3. Release gate Ubuntu-only; tag commit integrity unverified.
4. Version authority split (VERSION vs pyproject).
5. Docs/status stale counts.
6. Path containment component-only.

## Release-readiness: NOT ready. Target v2.2.1.

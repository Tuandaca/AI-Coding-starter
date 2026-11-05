# Characterization tests (M0)

This directory contains the M0 behavioral characterization suite for
AI-Coding-starter. Tests use **Python unittest + standard library only**
(`unittest`, `tempfile`, `unittest.mock`, `pathlib`, `re`, `json`,
`py_compile`-compatible). They are deterministic, offline, and write only
inside `tempfile.TemporaryDirectory()`.

No production file is modified, no external template is cloned, and no
setup/install/network action is executed.

## Files

| Test file | Coverage area |
|-----------|---------------|
| `test_config_loading.py` | 1. Config loading: valid/missing/malformed config, missing keys, fallback values, Windows paths |
| `test_project_types.py` | 2. Project types: PROJECT_TYPES structure, 7 types, agents/skills/workflows/scripts per type |
| `test_tech_presets.py` | 3. Tech presets: TECH_PRESETS, CUSTOM_STACK_OPTIONS, get_presets_for_types, select_custom_stack (input mocked) |
| `test_merge_tech_stacks.py` | 4. Multi-preset merge: captures current blind-merge output (intentionally not changed) |
| `test_merge_requirements.py` | 5. Requirement merging: single/multiple types, duplicates, ordering, empty input |
| `test_copy_selective.py` | 6. Selective copy: temp fixtures, selected files, nested dirs, missing source, destination structure |
| `test_generated_files.py` | 7. Generated files: GEMINI.md / CONTEXT.md targeted metadata assertions |
| `test_analytics.py` | 8. Analytics: checkbox parsing [x]/[X]/[ ]/[/], empty/missing/malformed/valid, load/save/track |
| `test_setup_scripts.py` | 9. Setup scripts: static text inspection only (URLs, paths, config generation, sed mutation, Windows/POSIX divergence) |

## Fixtures

`tests/fixtures/configs/` — config JSON fixtures (valid, missing keys, malformed, empty).

`tests/fixtures/fake_master/` — fake master template tree used by copy_selective tests.

## Running

```
python -m unittest discover -s tests -t .
```

or run a single file:

```
python tests\test_analytics.py
```

No `pytest`, `ruff`, or `mypy` is required. Production behavior is unchanged by this suite.

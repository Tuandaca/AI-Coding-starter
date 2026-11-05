#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Characterization tests for config loading (new_project.py).

Coverage (area 1: Config loading):
  - valid config loaded from config.json
  - missing config file -> hard-coded fallback defaults
  - malformed config -> hard-coded fallback defaults
  - missing keys -> per-key fallback defaults
  - hard-coded fallback values
  - Windows path handling

Deterministic, offline, temp-dir only. config.json is never modified.

new_project.py loads config at import time via a top-level block (lines
28-39) that is not wrapped in a function, so it cannot be invoked
directly. This test file executes the exact same statements (verbatim,
including the same default strings) in an isolated namespace pointed at
a temp config.json. A consistency test guards that this mirror matches
the values the real module loaded from the real config.json.
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import new_project  # noqa: E402  (module import loads the real config.json)

REAL_CONFIG = Path(new_project.__file__).resolve().parent / "config.json"
DEFAULT_MASTER = Path(r"D:\VibeCoding-Template\.agent")
DEFAULT_PROJECT = Path(r"D:\Projects")

FIXTURE_CONFIGS = REPO_ROOT / "tests" / "fixtures" / "configs"

# Verbatim mirror of new_project.py's module-level config-loading block.
CONFIG_LOAD_SOURCE = r'''
if CONFIG_FILE.exists():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            _config = json.load(f)
        MASTER_TEMPLATE_PATH = Path(_config.get("MASTER_TEMPLATE_PATH", r"D:\VibeCoding-Template\.agent"))
        DEFAULT_PROJECT_PATH = Path(_config.get("DEFAULT_PROJECT_PATH", r"D:\Projects"))
    except Exception:
        MASTER_TEMPLATE_PATH = Path(r"D:\VibeCoding-Template\.agent")
        DEFAULT_PROJECT_PATH = Path(r"D:\Projects")
else:
    MASTER_TEMPLATE_PATH = Path(r"D:\VibeCoding-Template\.agent")
    DEFAULT_PROJECT_PATH = Path(r"D:\Projects")
'''


def load_config_from(config_json_path):
    """Execute new_project's real config-loading block against a given path."""
    namespace = {"CONFIG_FILE": Path(config_json_path), "Path": Path, "json": json}
    exec(compile(CONFIG_LOAD_SOURCE, "<new_project config block>", "exec"), namespace)
    return namespace["MASTER_TEMPLATE_PATH"], namespace["DEFAULT_PROJECT_PATH"]


def _write_config(temp_dir, text):
    p = Path(temp_dir) / "config.json"
    p.write_text(text, encoding="utf-8")
    return p


class TestMirrorConsistency(unittest.TestCase):
    def test_helper_matches_real_module_for_real_config(self):
        master, project = load_config_from(REAL_CONFIG)
        self.assertEqual(master, new_project.MASTER_TEMPLATE_PATH)
        self.assertEqual(project, new_project.DEFAULT_PROJECT_PATH)


class TestImportAndValidConfig(unittest.TestCase):
    def test_import_loads_real_config_json(self):
        self.assertEqual(new_project.MASTER_TEMPLATE_PATH, DEFAULT_MASTER)
        self.assertEqual(new_project.DEFAULT_PROJECT_PATH, DEFAULT_PROJECT)

    def test_valid_config_loads_both_values(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = _write_config(td, json.dumps({
                "MASTER_TEMPLATE_PATH": r"D:\VibeCoding-Template\.agent",
                "DEFAULT_PROJECT_PATH": r"D:\Projects",
            }))
            master, project = load_config_from(cfg)
        self.assertEqual(master, DEFAULT_MASTER)
        self.assertEqual(project, DEFAULT_PROJECT)

    def test_windows_path_handling(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = _write_config(td, json.dumps({
                "MASTER_TEMPLATE_PATH": r"D:\Deep\Nested\.agent",
                "DEFAULT_PROJECT_PATH": r"D:\Custom Projects",
            }))
            master, project = load_config_from(cfg)
        self.assertEqual(master, Path(r"D:\Deep\Nested\.agent"))
        self.assertEqual(project, Path(r"D:\Custom Projects"))
        self.assertTrue(master.is_absolute())
        self.assertTrue(project.is_absolute())
        self.assertEqual(master.drive, "D:")
        self.assertEqual(project.drive, "D:")
        self.assertIn("\\", str(master))


class TestMissingConfig(unittest.TestCase):
    def test_missing_config_file_uses_fallback_defaults(self):
        with tempfile.TemporaryDirectory() as td:
            master, project = load_config_from(Path(td) / "config.json")
        self.assertEqual(master, DEFAULT_MASTER)
        self.assertEqual(project, DEFAULT_PROJECT)


class TestMalformedConfig(unittest.TestCase):
    def test_malformed_json_uses_fallback_defaults(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = _write_config(td, "{ not valid json !!")
            master, project = load_config_from(cfg)
        self.assertEqual(master, DEFAULT_MASTER)
        self.assertEqual(project, DEFAULT_PROJECT)


class TestMissingKeys(unittest.TestCase):
    def test_empty_config_uses_both_defaults(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = _write_config(td, "{}")
            master, project = load_config_from(cfg)
        self.assertEqual(master, DEFAULT_MASTER)
        self.assertEqual(project, DEFAULT_PROJECT)

    def test_missing_master_key_fallbacks_master_only(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = _write_config(td, json.dumps({"DEFAULT_PROJECT_PATH": r"D:\Only\Projects"}))
            master, project = load_config_from(cfg)
        self.assertEqual(master, DEFAULT_MASTER)
        self.assertEqual(project, Path(r"D:\Only\Projects"))

    def test_missing_project_key_fallbacks_project_only(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = _write_config(td, json.dumps({"MASTER_TEMPLATE_PATH": r"D:\Other\Template\.agent"}))
            master, project = load_config_from(cfg)
        self.assertEqual(master, Path(r"D:\Other\Template\.agent"))
        self.assertEqual(project, DEFAULT_PROJECT)


class TestFixtureConfigs(unittest.TestCase):
    """Config-loading mirror exercised against files under tests/fixtures/configs."""

    def test_fixture_valid_config(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "config.json"
            shutil.copy(FIXTURE_CONFIGS / "valid_config.json", dest)
            master, project = load_config_from(dest)
        self.assertEqual(master, DEFAULT_MASTER)
        self.assertEqual(project, DEFAULT_PROJECT)

    def test_fixture_missing_keys_per_key_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "config.json"
            shutil.copy(FIXTURE_CONFIGS / "missing_keys_config.json", dest)
            master, project = load_config_from(dest)
        self.assertEqual(master, DEFAULT_MASTER)
        self.assertEqual(project, Path(r"D:\Fixture\Projects"))

    def test_fixture_malformed_config(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "config.json"
            shutil.copy(FIXTURE_CONFIGS / "malformed_config.json", dest)
            master, project = load_config_from(dest)
        self.assertEqual(master, DEFAULT_MASTER)
        self.assertEqual(project, DEFAULT_PROJECT)

    def test_fixture_empty_config(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "config.json"
            shutil.copy(FIXTURE_CONFIGS / "empty_config.json", dest)
            master, project = load_config_from(dest)
        self.assertEqual(master, DEFAULT_MASTER)
        self.assertEqual(project, DEFAULT_PROJECT)


if __name__ == "__main__":
    unittest.main()

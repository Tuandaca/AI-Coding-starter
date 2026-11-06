#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Characterization tests for setup.bat / setup.sh (area 9: Setup scripts).

These tests ONLY inspect the setup script text. They NEVER execute the
scripts, never clone repositories, never mutate files, and never touch
the network.

M2 CHANGE LOG (INTENTIONAL CHANGES):
- test_setup_bat_clones_antigravity_ide: setup.bat no longer clones external template.
- test_setup_sh_clones_google_antigravity: setup.sh no longer clones external template.
- test_clone_urls_are_different: Neither script clones external templates.
- test_setup_bat_default_paths_on_windows_drive: No more D:\ hard-coded paths.
- test_setup_sh_default_paths_under_home: No more template path under HOME.
- test_setup_sh_does_not_write_config_json: setup.sh now writes config.json.
- test_setup_sh_copies_new_project_py_to_projects: No longer copies new_project.py.
- test_setup_sh_mutates_new_project_py_with_sed: setup.sh no longer uses sed.
- New: test_setup_bat_no_external_clone, test_setup_sh_no_external_clone.
- New: test_setup_bat_validates_bundled_resources, test_setup_sh_validates_bundled_resources.
- New: test_setup_scripts_config_equivalence, test_setup_scripts_no_sed_mutation.
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SETUP_BAT = REPO_ROOT / "setup.bat"
SETUP_SH = REPO_ROOT / "setup.sh"


class TestSetupScriptsStatic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bat = SETUP_BAT.read_text(encoding="utf-8")
        cls.sh = SETUP_SH.read_text(encoding="utf-8")

    def test_files_exist_and_non_empty(self):
        self.assertTrue(SETUP_BAT.exists())
        self.assertTrue(SETUP_SH.exists())
        self.assertGreater(len(self.bat), 0)
        self.assertGreater(len(self.sh), 0)

    # --- M2: No external clone by default ---
    def test_setup_bat_no_external_clone(self):
        """INTENTIONAL CHANGE — M2: setup.bat does not clone external template."""
        self.assertNotIn("git clone", self.bat)
        self.assertNotIn("antigravity-ide.git", self.bat)
        self.assertNotIn("google-antigravity.git", self.bat)

    def test_setup_sh_no_external_clone(self):
        """INTENTIONAL CHANGE — M2: setup.sh does not clone external template."""
        self.assertNotIn("git clone", self.sh)
        self.assertNotIn("antigravity-ide.git", self.sh)
        self.assertNotIn("google-antigravity.git", self.sh)

    def test_clone_urls_are_different(self):
        """INTENTIONAL CHANGE — M2: Neither script clones, so URLs are moot."""
        self.assertNotIn("https://github.com/Dokhacgiakhoa/antigravity-ide.git", self.bat)
        self.assertNotIn("https://github.com/Dokhacgiakhoa/google-antigravity.git", self.sh)

    # --- M2: No machine-specific hard-coded paths ---
    def test_setup_bat_no_drive_letter_paths(self):
        """INTENTIONAL CHANGE — M2: No D:\ hard-coded paths in setup.bat."""
        self.assertNotIn('DEFAULT_BASE=D:', self.bat)
        self.assertNotIn('D:\\VibeCoding-Template', self.bat)
        self.assertNotIn('D:\\Projects', self.bat)

    def test_setup_sh_no_home_template_path(self):
        """INTENTIONAL CHANGE — M2: No template path under HOME in setup.sh."""
        self.assertNotIn('$HOME/VibeCoding-Template', self.sh)
        self.assertNotIn('TEMPLATE_PATH=', self.sh)

    # --- M2: Config generation ---
    def test_setup_bat_writes_config_json(self):
        """setup.bat writes config.json with portable fields."""
        self.assertIn('echo {>', self.bat)
        self.assertIn("MASTER_TEMPLATE_PATH", self.bat)
        self.assertIn("DEFAULT_PROJECT_PATH", self.bat)
        self.assertIn("bundled_resources_enabled", self.bat)

    def test_setup_sh_writes_config_json(self):
        """INTENTIONAL CHANGE — M2: setup.sh now writes config.json (parity with setup.bat)."""
        self.assertIn("config.json", self.sh)
        self.assertIn("MASTER_TEMPLATE_PATH", self.sh)
        self.assertIn("DEFAULT_PROJECT_PATH", self.sh)
        self.assertIn("bundled_resources_enabled", self.sh)

    # --- M2: No source mutation ---
    def test_setup_sh_no_sed_mutation(self):
        """INTENTIONAL CHANGE — M2: setup.sh does not mutate new_project.py."""
        self.assertNotIn("sed", self.sh)

    def test_setup_bat_does_not_use_sed(self):
        self.assertNotIn("sed", self.bat)

    def test_setup_bat_creates_newpj_shortcut(self):
        self.assertIn('echo @echo off', self.bat)
        self.assertIn("python new_project.py", self.bat)

    def test_setup_sh_creates_newpj_shortcut(self):
        self.assertIn("NewPJ.bat", self.sh)
        self.assertIn("python new_project.py", self.sh)

    # --- M2: Bundled resources validation ---
    def test_setup_bat_validates_bundled_resources(self):
        self.assertIn("resources", self.bat)
        self.assertIn("agents", self.bat)

    def test_setup_sh_validates_bundled_resources(self):
        self.assertIn("resources", self.sh)
        self.assertIn("agents", self.sh)

    # --- Platform markers (retained) ---
    def test_platform_markers(self):
        self.assertIn("@echo off", self.bat)
        self.assertIn("set /p", self.bat)        # interactive prompts on Windows
        self.assertIn("#!/bin/bash", self.sh)
        self.assertIn("command -v python3", self.sh)
        self.assertIn("mkdir -p", self.sh)

    def test_setup_bat_interactive_setup_sh_non_interactive(self):
        self.assertIn("set /p", self.bat)
        self.assertNotIn("set /p", self.sh)

    # --- M2: Setup parity ---
    def test_setup_scripts_config_equivalence(self):
        """INTENTIONAL CHANGE — M2: Both scripts write equivalent config.json fields."""
        self.assertIn("bundled_resources_enabled", self.bat)
        self.assertIn("bundled_resources_enabled", self.sh)
        self.assertIn("external_template_optional", self.bat)
        self.assertIn("external_template_optional", self.sh)


if __name__ == "__main__":
    unittest.main()

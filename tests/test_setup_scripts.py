#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Characterization tests for setup.bat / setup.sh (area 9: Setup scripts).

These tests ONLY inspect the setup script text. They NEVER execute the
scripts, never clone repositories, never mutate files, and never touch
the network. They capture the current, observable divergence between the
Windows and POSIX setup paths for regression purposes.
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

    # --- Repo URLs (divergent between the two scripts) ---
    def test_setup_bat_clones_antigravity_ide(self):
        self.assertIn("https://github.com/Dokhacgiakhoa/antigravity-ide.git", self.bat)
        self.assertIn("git clone", self.bat)

    def test_setup_sh_clones_google_antigravity(self):
        self.assertIn("https://github.com/Dokhacgiakhoa/google-antigravity.git", self.sh)
        self.assertIn("git clone", self.sh)

    def test_clone_urls_are_different(self):
        self.assertNotIn("google-antigravity.git", self.bat)
        self.assertNotIn("antigravity-ide.git", self.sh)

    # --- Default paths ---
    def test_setup_bat_default_paths_on_windows_drive(self):
        self.assertIn('set "DEFAULT_BASE=D:"', self.bat)
        self.assertIn("%USER_BASE%\\VibeCoding-Template", self.bat)
        self.assertIn("%USER_BASE%\\Projects", self.bat)

    def test_setup_sh_default_paths_under_home(self):
        self.assertIn('TEMPLATE_PATH="$HOME/VibeCoding-Template"', self.sh)
        self.assertIn('PROJECTS_PATH="$HOME/Projects"', self.sh)

    # --- Config generation vs source mutation ---
    def test_setup_bat_writes_config_json(self):
        self.assertIn('echo {> "%~dp0config.json"', self.bat)
        self.assertIn("MASTER_TEMPLATE_PATH", self.bat)
        self.assertIn("DEFAULT_PROJECT_PATH", self.bat)
        self.assertIn("JSON_TEMPLATE_DIR", self.bat)
        self.assertIn("JSON_PROJECTS_DIR", self.bat)

    def test_setup_bat_creates_newpj_shortcut(self):
        self.assertIn('echo @echo off > "%~dp0NewPJ.bat"', self.bat)
        self.assertIn("python new_project.py", self.bat)

    def test_setup_sh_does_not_write_config_json(self):
        self.assertNotIn("config.json", self.sh)

    def test_setup_sh_copies_new_project_py_to_projects(self):
        self.assertIn('cp "$SCRIPT_DIR/new_project.py" "$PROJECTS_PATH/"', self.sh)

    def test_setup_sh_mutates_new_project_py_with_sed(self):
        self.assertIn("sed -i.bak", self.sh)
        self.assertIn("new_project.py", self.sh)
        self.assertIn("VibeCoding-Template", self.sh)

    def test_setup_bat_does_not_use_sed(self):
        self.assertNotIn("sed", self.bat)

    # --- Platform differences ---
    def test_platform_markers(self):
        self.assertIn("@echo off", self.bat)
        self.assertIn("set /p", self.bat)        # interactive prompts on Windows
        self.assertIn('mkdir "%TEMPLATE_DIR%"', self.bat)
        self.assertIn("#!/bin/bash", self.sh)
        self.assertIn("command -v python3", self.sh)
        self.assertIn("command -v git", self.sh)
        self.assertIn("mkdir -p", self.sh)

    def test_setup_bat_interactive_setup_sh_non_interactive(self):
        self.assertIn("set /p", self.bat)
        self.assertNotIn("set /p", self.sh)


if __name__ == "__main__":
    unittest.main()

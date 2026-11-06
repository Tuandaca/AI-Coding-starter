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

M12 CHANGE LOG (INTENTIONAL CHANGES):
- test_setup_bat_writes_config_json: setup.bat now delegates config generation
  to scripts/setup_portable.py (proper JSON escaping via json.dump).
- test_setup_sh_writes_config_json: setup.sh now delegates config generation
  to scripts/setup_portable.py (proper JSON escaping via json.dump).
- test_setup_sh_creates_newpj_shortcut: setup.sh now creates NewPJ.sh (POSIX),
  not NewPJ.bat (Windows).
- test_setup_bat_interactive_setup_sh_non_interactive: setup.bat no longer uses
  set /p (Python helper handles prompting); setup.sh never used set /p.
- test_setup_scripts_config_equivalence: Both scripts delegate to the Python
  helper, which writes bundled_resources_enabled via json.dump.
- test_platform_markers: setup.bat no longer uses set /p; setup.sh checks
  python3 first then python.
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

    # --- M12: Config generation via shared Python helper ---
    def test_setup_bat_writes_config_json(self):
        """setup.bat delegates config generation to setup_portable.py."""
        self.assertIn("scripts\\setup_portable.py", self.bat)

    def test_setup_sh_writes_config_json(self):
        """INTENTIONAL CHANGE — M12: setup.sh delegates config generation
        to setup_portable.py (parity with setup.bat)."""
        self.assertIn("scripts/setup_portable.py", self.sh)

    def test_setup_bat_config_written_by_python_helper(self):
        """setup.bat uses Python json.dump for proper escaping (no raw echo)."""
        self.assertNotIn('echo {>', self.bat)
        self.assertNotIn('echo   "MASTER_TEMPLATE_PATH"', self.bat)
        self.assertNotIn('echo   "DEFAULT_PROJECT_PATH"', self.bat)
        self.assertNotIn('echo   "bundled_resources_enabled"', self.bat)
        self.assertNotIn('echo   "external_template_optional"', self.bat)

    def test_setup_sh_config_written_by_python_helper(self):
        """setup.sh uses Python json.dump, not heredoc interpolation."""
        self.assertNotIn('cat > "$SCRIPT_DIR/config.json" << EOF', self.sh)
        self.assertNotIn('"MASTER_TEMPLATE_PATH": null', self.sh)
        self.assertNotIn('"DEFAULT_PROJECT_PATH": "$PROJECTS_PATH"', self.sh)

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
        """setup.sh creates NewPJ.sh (POSIX), not NewPJ.bat (Windows)."""
        self.assertIn("NewPJ.sh", self.sh)
        self.assertIn("python3 new_project.py", self.sh)

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
        # setup.bat no longer uses set /p (Python helper prompts)
        self.assertNotIn("set /p", self.bat)
        self.assertIn("#!/bin/bash", self.sh)
        self.assertIn("command -v python3", self.sh)
        # setup.sh delegates directory creation to Python helper
        self.assertNotIn("mkdir -p", self.sh)

    def test_setup_bat_interactive_setup_sh_non_interactive(self):
        """setup.bat delegates prompting to Python helper (no set /p);
        setup.sh never used set /p."""
        self.assertNotIn("set /p", self.bat)
        self.assertNotIn("set /p", self.sh)

    # --- M2: Setup parity ---
    def test_setup_scripts_config_equivalence(self):
        """INTENTIONAL CHANGE — M12: Both scripts delegate to the Python
        helper which writes config.json with bundled_resources_enabled etc."""
        self.assertIn("scripts\\setup_portable.py", self.bat)
        self.assertIn("scripts/setup_portable.py", self.sh)


if __name__ == "__main__":
    unittest.main()

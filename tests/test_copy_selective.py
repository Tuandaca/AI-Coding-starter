#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Characterization tests for copy_selective (area 6: Selective copy).

Coverage:
  - selected files copied into temp destination; missing optional source
    files are skipped without error
  - nested directories copied (skills/, shared/)
  - destination directory structure created (agents, skills, .shared,
    workflows, scripts, core, rules)
  - GEMINI.md and CONTEXT.md generated
  - total_bytes equals sum of copied file sizes
  - empty requirements: zero bytes, generated files still written
  - missing source tree: no crash, zero bytes

All source content comes from tests/fixtures/fake_master; all output goes
into tempfile.TemporaryDirectory(). No production files are touched.
"""
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import new_project  # noqa: E402

FIXTURES = REPO_ROOT / "tests" / "fixtures"
FAKE_MASTER = FIXTURES / "fake_master"

BASE_MERGED = {
    "agents": ["frontend-specialist.md", "absent-agent.md"],
    "skills": ["modern-web-architect"],
    "shared": ["design-system"],
    "workflows": ["create.md", "absent-workflow.md"],
    "scripts": ["checklist.py", "absent-script.py"],
    "focus": ["Test focus area"],
}

COPIED_FILES = [
    FAKE_MASTER / "agents" / "frontend-specialist.md",
    FAKE_MASTER / "skills" / "modern-web-architect" / "skill.md",
    # INTENTIONAL CHANGE — M2: bundled resources use "shared/" not ".shared/"
    FAKE_MASTER / "shared" / "design-system" / "tokens.md",
    FAKE_MASTER / "workflows" / "create.md",
    FAKE_MASTER / "scripts" / "checklist.py",
    # core/ and rules/ are copied unconditionally, so included in expected total
    FAKE_MASTER / "core" / "config.yaml",
    FAKE_MASTER / "rules" / "lint.md",
]


class TestCopySelective(unittest.TestCase):
    def expected_bytes(self):
        return sum(f.stat().st_size for f in COPIED_FILES)

    def expected_core_rules_bytes(self):
        """Bytes from core/ and rules/ which are always copied if present."""
        core_rules = [
            FAKE_MASTER / "core" / "config.yaml",
            FAKE_MASTER / "rules" / "lint.md",
        ]
        return sum(f.stat().st_size for f in core_rules)

    def _run_copy_selective(self, *args, **kwargs):
        """Run copy_selective with stdout redirected to suppress emoji printing."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            return new_project.copy_selective(*args, **kwargs)

    def test_selected_files_copied_missing_optional_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "dest"
            total = self._run_copy_selective(
                FAKE_MASTER, dest, dict(BASE_MERGED), "test-proj",
                ["personal-web"],
            )
            # Selected files copied verbatim.
            self.assertTrue((dest / "agents" / "frontend-specialist.md").exists())
            # Optional missing sources skipped, no exception.
            self.assertFalse((dest / "agents" / "absent-agent.md").exists())
            self.assertFalse((dest / "workflows" / "absent-workflow.md").exists())
            self.assertFalse((dest / "scripts" / "absent-script.py").exists())
            # Nested directories copied.
            self.assertTrue((dest / "skills" / "modern-web-architect" / "skill.md").exists())
            self.assertTrue((dest / ".shared" / "design-system" / "tokens.md").exists())
            # Workflows / scripts.
            self.assertTrue((dest / "workflows" / "create.md").exists())
            self.assertTrue((dest / "scripts" / "checklist.py").exists())
            # core / rules copied wholesale (unconditionally if source exists).
            self.assertTrue((dest / "core" / "config.yaml").exists())
            self.assertTrue((dest / "rules" / "lint.md").exists())
            # Generated files.
            self.assertTrue((dest / "GEMINI.md").exists())
            self.assertTrue((dest / "CONTEXT.md").exists())
            # Only selected agent files were copied (ghost.md stays out).
            agent_names = sorted(p.name for p in (dest / "agents").iterdir())
            self.assertEqual(agent_names, ["frontend-specialist.md"])
            # Byte total matches the copied files (including core + rules).
            self.assertEqual(total, self.expected_bytes())
            self.assertGreater(total, 0)

    def test_copied_content_is_verbatim(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "dest"
            self._run_copy_selective(
                FAKE_MASTER, dest, dict(BASE_MERGED), "test-proj",
                ["personal-web"],
            )
            src = FAKE_MASTER / "agents" / "frontend-specialist.md"
            self.assertEqual(
                (dest / "agents" / "frontend-specialist.md").read_text(encoding="utf-8"),
                src.read_text(encoding="utf-8"),
            )

    def test_destination_structure_created(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "dest"
            self._run_copy_selective(
                FAKE_MASTER, dest, dict(BASE_MERGED), "test-proj",
                ["personal-web"],
            )
            for sub in ("agents", "skills", ".shared", "workflows", "scripts",
                        "core", "rules"):
                self.assertTrue((dest / sub).is_dir(), f"missing {sub}")

    def test_empty_requirements_core_rules_copied_generated_files(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "dest"
            empty = {"agents": [], "skills": [], "shared": [],
                     "workflows": [], "scripts": [], "focus": []}
            total = self._run_copy_selective(
                FAKE_MASTER, dest, empty, "empty-proj", [])
            # core/ and rules/ are copied unconditionally if they exist.
            self.assertEqual(total, self.expected_core_rules_bytes())
            self.assertTrue((dest / "GEMINI.md").exists())
            self.assertTrue((dest / "CONTEXT.md").exists())
            # core/ and rules/ directories created.
            self.assertTrue((dest / "core").is_dir())
            self.assertTrue((dest / "rules").is_dir())
            # .shared directory created unconditionally before the loop (mkdir exist_ok=True).
            self.assertTrue((dest / ".shared").is_dir())

    def test_missing_source_tree_no_crash(self):
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "does-not-exist"
            dest = Path(td) / "dest"
            total = self._run_copy_selective(
                missing, dest, dict(BASE_MERGED), "proj", ["personal-web"],
            )
            self.assertEqual(total, 0)
            self.assertTrue(dest.exists())


if __name__ == "__main__":
    unittest.main()

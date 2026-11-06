#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M4 minimal-file-count tests.

Coverage:
  - .ai-coding-starter/ contains no more than 4 files (prefer exactly 3)
  - exactly project.yaml, state.yaml, resources.lock under canonical state dir
  - derived Markdown lives at project root, NOT inside .ai-coding-starter/

Deterministic, offline, writes only inside tempfile.TemporaryDirectory().
"""
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.portable_renderer import render_all
from core.spec import build_project_spec, write_project_spec
from core.state import build_initial_state, build_resources_lock, write_resources_lock, write_state


class TestMinimalFileCount(unittest.TestCase):
    def test_canonical_state_dir_has_three_files(self):
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td)
            spec = build_project_spec(
                "File Count App", project_type_id="saas",
                capabilities=["authentication"], stack_bundle_id="nextjs-supabase",
            )
            state = build_initial_state(str(spec.id))
            lock = build_resources_lock("nextjs-supabase")
            write_project_spec(project_root, spec)
            write_state(project_root, state)
            write_resources_lock(project_root, lock)
            render_all(project_root, spec, state)

            ai_dir = project_root / ".ai-coding-starter"
            self.assertTrue(ai_dir.is_dir())
            files = [p for p in ai_dir.iterdir() if p.is_file()]
            file_names = sorted(p.name for p in files)
            # No more than 4 files; exactly 3 preferred.
            self.assertLessEqual(len(files), 4)
            self.assertEqual(
                file_names, ["project.yaml", "resources.lock", "state.yaml"]
            )

    def test_derived_markdown_lives_at_project_root(self):
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td)
            spec = build_project_spec("Root Markdown App", project_type_id="portfolio")
            state = build_initial_state(str(spec.id))
            written = render_all(project_root, spec, state)
            self.assertTrue((project_root / "AGENTS.md").exists())
            self.assertTrue((project_root / "CONTEXT.md").exists())
            self.assertTrue((project_root / "DECISIONS.md").exists())
            self.assertTrue((project_root / "HANDOFF.md").exists())
            # Derived markdown is NOT inside .ai-coding-starter/ (keeps it <= 4 files).
            ai_dir = project_root / ".ai-coding-starter"
            self.assertFalse((ai_dir / "AGENTS.md").exists())
            self.assertFalse((ai_dir / "CONTEXT.md").exists())
            self.assertFalse((ai_dir / "DECISIONS.md").exists())
            self.assertFalse((ai_dir / "HANDOFF.md").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)

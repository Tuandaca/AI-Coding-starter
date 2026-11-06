#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M4 authority tests.

Coverage:
  - project.yaml is the sole machine-authoritative project config
  - Markdown (AGENTS.md/CONTEXT.md/HANDOFF.md) is derived, not authority
  - conflicting Markdown cannot override canonical project.yaml
  - state loading never parses Markdown as fallback authority

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
from core.spec import build_project_spec, read_project_spec, write_project_spec
from core.state import build_initial_state, read_state, write_state


class TestPortableAuthority(unittest.TestCase):
    def test_canonical_spec_wins_over_conflicting_markdown(self):
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td)
            spec = build_project_spec(
                "Authority App", project_type_id="saas",
                capabilities=["authentication"], stack_bundle_id="nextjs-supabase",
            )
            state = build_initial_state(str(spec.id))
            write_project_spec(project_root, spec)
            write_state(project_root, state)
            render_all(project_root, spec, state)

            # Derived Markdown now reflects canonical state.
            context = (project_root / "CONTEXT.md").read_text(encoding="utf-8")
            self.assertIn("saas", context)
            self.assertIn("nextjs-supabase", context)

            # Now corrupt the Markdown to claim a different type/bundle.
            (project_root / "CONTEXT.md").write_text(
                "Project Type: e-commerce\nStack Bundle: nextjs-dotnet-postgres\n",
                encoding="utf-8",
            )
            (project_root / "AGENTS.md").write_text(
                "# AGENTS.md\nProject Type: e-commerce\n", encoding="utf-8",
            )

            # Reloading canonical state must still return project.yaml values.
            reloaded_spec = read_project_spec(
                project_root / ".ai-coding-starter" / "project.yaml"
            )
            self.assertEqual(str(reloaded_spec.project_type), "saas")
            self.assertEqual(str(reloaded_spec.stack_bundle), "nextjs-supabase")
            self.assertEqual(
                [str(c) for c in reloaded_spec.capabilities], ["authentication"]
            )

            # State reload also ignores Markdown.
            reloaded_state = read_state(
                project_root / ".ai-coding-starter" / "state.yaml"
            )
            self.assertEqual(reloaded_state.phase, "planning")

    def test_markdown_never_parsed_as_fallback_authority(self):
        """The state loader reads only .ai-coding-starter/*.yaml, never Markdown."""
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td)
            # Only Markdown present, no canonical state.
            (project_root / "CONTEXT.md").write_text(
                "Project Type: markdown-only\n", encoding="utf-8",
            )
            # Reading state from a directory without canonical files must not
            # silently fall back to Markdown; it must raise clearly.
            with self.assertRaises((FileNotFoundError, ValueError, OSError)):
                read_state(project_root / ".ai-coding-starter" / "state.yaml")
            with self.assertRaises((FileNotFoundError, ValueError, OSError)):
                read_project_spec(project_root / ".ai-coding-starter" / "project.yaml")


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M4 portable renderer tests.

Coverage:
  - derived Markdown matches canonical state (one-way: canonical -> Markdown)
  - AGENTS.md/CONTEXT.md/DECISIONS.md/HANDOFF.md reflect project/stack/state
  - no runtime-specific instructions (Codex/OpenCode/Antigravity/Claude/Cursor)
  - regenerating Markdown after canonical change reflects new state

Deterministic, offline, writes only inside tempfile.TemporaryDirectory().
"""
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.portable_renderer import (
    render_agents_md,
    render_context_md,
    render_decisions_md,
    render_handoff_md,
    render_all,
)
from core.spec import build_project_spec
from core.state import build_initial_state


class TestPortableRenderer(unittest.TestCase):
    def setUp(self):
        self.spec = build_project_spec(
            "Renderer App", project_type_id="saas",
            capabilities=["authentication", "payments"],
            stack_bundle_id="nextjs-dotnet-postgres",
        )
        self.state = build_initial_state(
            str(self.spec.id), phase="planning", focus="Set up scaffolding",
            canonical_branch=None,
        )

    def test_agents_md_matches_canonical_state(self):
        content = render_agents_md(self.spec)
        self.assertIn("# AGENTS.md", content)
        self.assertIn("Renderer App", content)
        self.assertIn("saas", content)
        self.assertIn("authentication", content)
        self.assertIn("payments", content)
        self.assertIn("nextjs-dotnet-postgres", content)
        self.assertIn(".ai-coding-starter/project.yaml", content)
        # No runtime-specific instructions.
        for runtime in ["codex", "opencode", "antigravity", "claude", "cursor", "gemini"]:
            self.assertNotIn(runtime, content.lower())

    def test_context_md_matches_canonical_state(self):
        content = render_context_md(self.spec, self.state)
        self.assertIn("# 📋 PROJECT CONTEXT", content)
        self.assertIn("Renderer App", content)
        self.assertIn("saas", content)
        self.assertIn("nextjs-dotnet-postgres", content)
        self.assertIn("- **Phase**: planning", content)
        self.assertIn("not initialized / unavailable", content)
        self.assertIn("Set up scaffolding", content)

    def test_decisions_md_append_only_minimal(self):
        content = render_decisions_md()
        self.assertIn("# Architecture Decisions", content)
        self.assertIn("No decisions recorded yet.", content)

    def test_handoff_md_honest_about_no_git(self):
        content = render_handoff_md(self.spec, self.state)
        self.assertIn("# Handoff", content)
        self.assertIn("Renderer App", content)
        self.assertIn("not initialized / unavailable", content)
        self.assertIn("0 worktree(s)", content)

    def test_regenerating_markdown_reflects_canonical_change(self):
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td)
            render_all(project_root, self.spec, self.state)
            context_before = (project_root / "CONTEXT.md").read_text(encoding="utf-8")
            self.assertIn("- **Phase**: planning", context_before)

            # Change canonical state.
            changed_spec = build_project_spec(
                "Renderer App", project_type_id="e-commerce",
                capabilities=["authentication", "payments", "subscriptions"],
                stack_bundle_id="nextjs-supabase",
            )
            changed_state = build_initial_state(
                str(changed_spec.id), phase="architecture", focus="Design data model",
                canonical_branch=None,
            )
            render_all(project_root, changed_spec, changed_state)
            context_after = (project_root / "CONTEXT.md").read_text(encoding="utf-8")
            self.assertIn("- **Phase**: architecture", context_after)
            self.assertIn("Design data model", context_after)
            self.assertIn("subscriptions", context_after)
            self.assertNotIn("- **Phase**: planning", context_after)


if __name__ == "__main__":
    unittest.main(verbosity=2)

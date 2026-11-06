#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M5: Runtime instruction discoverability tests (declarative/static).

Covers requirement 19 (TEST PLAN — DISCOVERABILITY):
  - Codex: root AGENTS.md used/shared; adapter does not own/delete it
  - OpenCode: root AGENTS.md used/shared (or generated config references it)
  - Claude: instruction location matches current documented discovery
  - Cursor: shared AGENTS.md matches documented discovery
  - Antigravity: .agent/GEMINI.md owned and justified

These are declarative/static tests against adapter metadata plus renderer
behavior. No external runtime applications are launched.

Standard library only. No network.
"""
import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

generic_renderer = importlib.import_module("core.generic-renderer")  # noqa: E402
GenericRenderer = generic_renderer.GenericRenderer

from core.spec import build_project_spec, write_project_spec  # noqa: E402
from core.state import (  # noqa: E402
    build_initial_state,
    build_resources_lock,
    write_resources_lock,
    write_state,
)

ADAPTERS_DIR = REPO_ROOT / "runtime-adapters"
RUNTIME_IDS = ["codex", "opencode", "antigravity", "claude-code", "cursor"]


def load_adapter(runtime_id):
    with open(ADAPTERS_DIR / f"{runtime_id}.yaml", "r", encoding="utf-8") as handle:
        return json.load(handle)


def make_canonical_project(root, project_name="Discover Project"):
    root = Path(root)
    spec = build_project_spec(
        project_name, project_type_id="saas",
        capabilities=["authentication"], stack_bundle_id="nextjs-supabase",
    )
    write_project_spec(root, spec)
    write_state(root, build_initial_state(str(spec.id), phase="planning"))
    write_resources_lock(
        root, build_resources_lock("nextjs-supabase", requested_bundle_id="nextjs-supabase")
    )
    (root / "AGENTS.md").write_text("# Discover Project\n\nM4 instructions.\n", encoding="utf-8")
    return root


class TestAdapterDiscoverabilityMetadata(unittest.TestCase):
    def test_every_adapter_declares_instruction_source(self):
        for runtime_id in RUNTIME_IDS:
            with self.subTest(runtime=runtime_id):
                adapter = load_adapter(runtime_id)
                source = adapter.get("instruction_source")
                self.assertIsInstance(source, dict, f"{runtime_id}: missing instruction_source")
                self.assertIn("path", source, f"{runtime_id}: instruction_source missing path")
                self.assertIn("ownership", source, f"{runtime_id}: instruction_source missing ownership")
                self.assertIn(source["ownership"], ("shared", "owned"))

    def test_codex_uses_shared_root_agents_md(self):
        adapter = load_adapter("codex")
        source = adapter["instruction_source"]
        self.assertEqual(source["path"], "AGENTS.md")
        self.assertEqual(source["ownership"], "shared")
        # render.outputs must be empty (no owned file).
        self.assertEqual(adapter["render"]["outputs"], [])

    def test_opencode_uses_shared_root_agents_md(self):
        adapter = load_adapter("opencode")
        source = adapter["instruction_source"]
        self.assertEqual(source["path"], "AGENTS.md")
        self.assertEqual(source["ownership"], "shared")
        self.assertEqual(adapter["render"]["outputs"], [])

    def test_claude_code_uses_shared_root_agents_md(self):
        adapter = load_adapter("claude-code")
        source = adapter["instruction_source"]
        self.assertEqual(source["path"], "AGENTS.md")
        self.assertEqual(source["ownership"], "shared")
        self.assertEqual(adapter["render"]["outputs"], [])

    def test_cursor_uses_shared_root_agents_md(self):
        adapter = load_adapter("cursor")
        source = adapter["instruction_source"]
        self.assertEqual(source["path"], "AGENTS.md")
        self.assertEqual(source["ownership"], "shared")
        self.assertEqual(adapter["render"]["outputs"], [])

    def test_antigravity_owns_agent_gemini_md(self):
        adapter = load_adapter("antigravity")
        source = adapter["instruction_source"]
        self.assertEqual(source["path"], ".agent/GEMINI.md")
        self.assertEqual(source["ownership"], "owned")
        self.assertEqual(len(adapter["render"]["outputs"]), 1)
        self.assertEqual(adapter["render"]["outputs"][0]["path"], ".agent/GEMINI.md")
        self.assertTrue(adapter["render"]["outputs"][0].get("mark_owned"))


class TestSharedFileUninstall(unittest.TestCase):
    """Critical: uninstalling a shared-consumer adapter must not delete
    the M4 root AGENTS.md, even though that runtime consumes it."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="m5-sharedfile-"))
        self.root = make_canonical_project(self.temp_dir)
        self.renderer = GenericRenderer(self.root, adapters_dir=str(ADAPTERS_DIR))
        self.agents_md = self.root / "AGENTS.md"
        self.before = self.agents_md.read_text(encoding="utf-8")

    def test_install_then_uninstall_codex_preserves_agents_md(self):
        install_result = self.renderer.install("codex")
        self.assertTrue(install_result.ok, msg=install_result.errors)
        self.assertTrue(self.agents_md.exists())
        self.assertEqual(self.agents_md.read_text(encoding="utf-8"), self.before)

        uninstall_result = self.renderer.uninstall("codex")
        self.assertTrue(uninstall_result.ok, msg=uninstall_result.errors)
        self.assertTrue(self.agents_md.exists())
        self.assertEqual(self.agents_md.read_text(encoding="utf-8"), self.before)

    def test_install_then_uninstall_opencode_preserves_agents_md(self):
        self.renderer.install("opencode")
        self.assertTrue(self.agents_md.exists())
        self.assertEqual(self.agents_md.read_text(encoding="utf-8"), self.before)
        self.renderer.uninstall("opencode")
        self.assertTrue(self.agents_md.exists())
        self.assertEqual(self.agents_md.read_text(encoding="utf-8"), self.before)

    def test_install_then_uninstall_antigravity_preserves_agents_md(self):
        self.renderer.install("antigravity")
        self.assertTrue(self.agents_md.exists())
        self.assertEqual(self.agents_md.read_text(encoding="utf-8"), self.before)
        self.renderer.uninstall("antigravity")
        self.assertTrue(self.agents_md.exists())
        self.assertEqual(self.agents_md.read_text(encoding="utf-8"), self.before)
        # Antigravity's owned file removed, shared AGENTS.md remains.
        self.assertFalse((self.root / ".agent/GEMINI.md").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)

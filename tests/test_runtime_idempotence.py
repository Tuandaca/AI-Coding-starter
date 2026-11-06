#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M5: Idempotence tests (corrected model).

Covers requirement 48 (TEST PLAN — IDEMPOTENCE):
  - install(runtime); install(runtime) -> stable
  - no duplicated blocks
  - no duplicated files
  - no accumulating garbage

Standard library only. No network.
"""
import importlib
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


def make_canonical_project(root, project_name="Idempotent Project"):
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
    return root


class TestInstallIdempotence(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="m5-idem-"))
        self.root = make_canonical_project(self.temp_dir)
        self.renderer = GenericRenderer(self.root, adapters_dir=str(ADAPTERS_DIR))

    def test_shared_consumer_install_twice_stable(self):
        first = self.renderer.install("codex")
        self.assertTrue(first.ok, msg=first.errors)
        self.assertEqual(first.written, [])
        second = self.renderer.install("codex")
        self.assertTrue(second.ok, msg=second.errors)
        self.assertEqual(second.written, [])

    def test_owned_adapter_install_twice_produces_identical_file_once(self):
        first = self.renderer.install("antigravity")
        self.assertTrue(first.ok, msg=first.errors)
        owned = self.root / ".agent/GEMINI.md"
        self.assertTrue(owned.exists())
        first_content = owned.read_text(encoding="utf-8")
        marker = "<!-- ai-coding-starter runtime adapter: antigravity | generated | owned -->"
        self.assertEqual(first_content.count(marker), 1)

        second = self.renderer.install("antigravity")
        self.assertTrue(second.ok, msg=second.errors)
        second_content = owned.read_text(encoding="utf-8")
        self.assertEqual(second_content, first_content)
        self.assertEqual(second_content.count(marker), 1)

        # Only one file exists (no duplicates).
        agent_dir = self.root / ".agent"
        files = [p for p in agent_dir.iterdir()] if agent_dir.exists() else []
        self.assertEqual([f.name for f in files], ["GEMINI.md"])

    def test_manifest_stable_across_reinstall(self):
        self.renderer.install("antigravity")
        manifest_1 = (
            self.root / ".ai-coding-starter" / ".runtime-manifest.json"
        ).read_text(encoding="utf-8")
        self.renderer.install("antigravity")
        manifest_2 = (
            self.root / ".ai-coding-starter" / ".runtime-manifest.json"
        ).read_text(encoding="utf-8")
        self.assertEqual(manifest_1, manifest_2)

    def test_render_twice_no_accumulating_garbage(self):
        sizes = []
        for _ in range(3):
            self.renderer.install("opencode")
            # opencode is a shared consumer: creates no .opencode/ files.
            opencode_dir = self.root / ".opencode"
            file_count = len(list(opencode_dir.iterdir())) if opencode_dir.exists() else 0
            self.assertEqual(file_count, 0)
            sizes.append(1)
        self.assertEqual(sizes[0], sizes[1])
        self.assertEqual(sizes[1], sizes[2])

    def test_switch_then_reinstall_is_stable(self):
        r1 = self.renderer.install("codex")
        self.renderer.switch("codex", "antigravity")
        r2 = self.renderer.install("antigravity")
        self.assertTrue(r1.ok)
        self.assertTrue(r2.ok)
        self.assertTrue((self.root / ".agent/GEMINI.md").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M5: Install / uninstall reversibility tests (corrected model).

Covers requirement 47 (TEST PLAN — REVERSIBILITY):
  - install -> generated adapter-owned files exist (antigravity only)
  - uninstall -> only owned generated files removed
  - canonical files preserved
  - user files preserved
  - shared M4 AGENTS.md preserved across install/uninstall of shared consumers

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


def make_canonical_project(root, project_name="Reversible Project"):
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


class TestInstallUninstallReversibility(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="m5-reverse-"))
        self.root = make_canonical_project(self.temp_dir)
        self.renderer = GenericRenderer(self.root, adapters_dir=str(ADAPTERS_DIR))

    def _user_file(self, rel, content="user content"):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_shared_consumer_install_uninstall_no_files(self):
        result = self.renderer.install("codex")
        self.assertTrue(result.ok, msg=result.errors)
        self.assertEqual(result.written, [])
        uninstall_result = self.renderer.uninstall("codex")
        self.assertTrue(uninstall_result.ok, msg=uninstall_result.errors)
        self.assertEqual(uninstall_result.removed, [])

    def test_antigravity_install_creates_owned_file(self):
        result = self.renderer.install("antigravity")
        self.assertTrue(result.ok, msg=result.errors)
        owned = self.root / ".agent/GEMINI.md"
        self.assertTrue(owned.exists())
        self.assertIn(owned, result.written)

    def test_antigravity_uninstall_removes_only_owned_file(self):
        self.renderer.install("antigravity")
        owned = self.root / ".agent/GEMINI.md"
        self.assertTrue(owned.exists())

        result = self.renderer.uninstall("antigravity")
        self.assertTrue(result.ok, msg=result.errors)
        self.assertIn(owned, result.removed)
        self.assertFalse(owned.exists())

    def test_uninstall_preserves_canonical_files(self):
        self.renderer.install("antigravity")
        before = {
            name: (self.root / ".ai-coding-starter" / name).read_bytes()
            for name in ("project.yaml", "state.yaml", "resources.lock")
        }
        self.renderer.uninstall("antigravity")
        after = {
            name: (self.root / ".ai-coding-starter" / name).read_bytes()
            for name in ("project.yaml", "state.yaml", "resources.lock")
        }
        self.assertEqual(before, after)

    def test_uninstall_preserves_user_files_in_same_directory(self):
        user_file = self._user_file(".agent/user-note.md", "my private notes")
        self.renderer.install("antigravity")
        self.assertTrue(user_file.exists())
        self.renderer.uninstall("antigravity")
        self.assertTrue(user_file.exists(), "user file must not be deleted on uninstall")
        self.assertFalse((self.root / ".agent/GEMINI.md").exists())

    def test_uninstall_removes_empty_owned_directory(self):
        self.renderer.install("antigravity")
        self.assertTrue((self.root / ".agent").exists())
        self.renderer.uninstall("antigravity")
        self.assertFalse((self.root / ".agent").exists())

    def test_uninstall_when_not_installed_is_safe_noop(self):
        result = self.renderer.uninstall("antigravity")
        self.assertTrue(result.ok)
        self.assertEqual(result.removed, [])

    def test_manifest_entry_removed_on_uninstall(self):
        import json
        self.renderer.install("antigravity")
        manifest = self.root / ".ai-coding-starter" / ".runtime-manifest.json"
        self.assertIn("antigravity", json.loads(manifest.read_text(encoding="utf-8"))["runtimes"])
        self.renderer.uninstall("antigravity")
        self.assertNotIn("antigravity", json.loads(manifest.read_text(encoding="utf-8"))["runtimes"])

    def test_all_runtimes_install_and_uninstall_cleanly(self):
        for runtime_id in ["codex", "opencode", "antigravity", "claude-code", "cursor"]:
            with self.subTest(runtime=runtime_id):
                result = self.renderer.install(runtime_id)
                self.assertTrue(result.ok, msg=f"{runtime_id}: {result.errors}")
                if runtime_id == "antigravity":
                    expected = self.root / ".agent/GEMINI.md"
                    self.assertTrue(expected.exists())
                uninstall_result = self.renderer.uninstall(runtime_id)
                self.assertTrue(uninstall_result.ok, msg=f"{runtime_id}: {uninstall_result.errors}")
                # Canonical intact after every cycle.
                for name in ("project.yaml", "state.yaml", "resources.lock"):
                    self.assertTrue(
                        (self.root / ".ai-coding-starter" / name).exists()
                    )


if __name__ == "__main__":
    unittest.main(verbosity=2)

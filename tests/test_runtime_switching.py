#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M5: Runtime switching tests (corrected shared-ownership model).

Covers requirement 46 (TEST PLAN — SWITCHING):
  - create M4 canonical temp project; snapshot canonical files + shared AGENTS.md
  - install runtime A; snapshot canonical files
  - switch/uninstall runtime A; install runtime B; snapshot canonical files
  - Required: canonical snapshots identical; M4 AGENTS.md preserved

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
CANONICAL_NAMES = ("project.yaml", "state.yaml", "resources.lock")
SHARED_CONSUMERS = ["codex", "opencode", "claude-code", "cursor"]
ALL_RUNTIME_IDS = SHARED_CONSUMERS + ["antigravity"]


def make_canonical_project(root, project_name="Switch Project"):
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
    # M4 derives a shared root AGENTS.md.
    (root / "AGENTS.md").write_text("# Switch Project\n\nM4 instructions.\n", encoding="utf-8")
    return root


def canonical_snapshot(root):
    state_dir = Path(root) / ".ai-coding-starter"
    snapshot = {}
    for name in CANONICAL_NAMES:
        path = state_dir / name
        snapshot[name] = path.read_bytes() if path.exists() else None
    # Include the shared M4 AGENTS.md (must be preserved across switches).
    agents = root / "AGENTS.md"
    snapshot["AGENTS.md"] = agents.read_bytes() if agents.exists() else None
    return snapshot


class TestRuntimeSwitching(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="m5-switch-"))
        self.root = make_canonical_project(self.temp_dir)
        self.renderer = GenericRenderer(self.root, adapters_dir=str(ADAPTERS_DIR))
        self.baseline = canonical_snapshot(self.root)

    def test_install_shared_consumer_leaves_everything_unchanged(self):
        self.renderer.install("codex")
        self.assertEqual(canonical_snapshot(self.root), self.baseline)
        # No owned runtime output created.
        self.assertFalse((self.root / ".agent/GEMINI.md").exists())

    def test_switch_codex_to_opencode_keeps_canonical_identical(self):
        self.renderer.install("codex")
        result = self.renderer.switch("codex", "opencode")
        self.assertTrue(result.ok, msg=result.errors)
        self.assertTrue(result.canonical_unchanged)
        # No owned output files for shared consumers.
        self.assertFalse((self.root / ".agent/GEMINI.md").exists())
        # Canonical + shared AGENTS.md byte-identical across the switch.
        self.assertEqual(canonical_snapshot(self.root), self.baseline)

    def test_switch_to_antigravity_creates_owned_then_removes(self):
        self.renderer.install("antigravity")
        self.assertTrue((self.root / ".agent/GEMINI.md").exists())
        self.assertEqual(canonical_snapshot(self.root), self.baseline)

        result = self.renderer.switch("antigravity", "codex")
        self.assertTrue(result.ok, msg=result.errors)
        self.assertTrue(result.canonical_unchanged)
        # Antigravity-owned file removed on switch away.
        self.assertFalse((self.root / ".agent/GEMINI.md").exists())
        # Shared AGENTS.md preserved.
        self.assertEqual(
            (self.root / "AGENTS.md").read_bytes(), self.baseline["AGENTS.md"]
        )
        self.assertEqual(canonical_snapshot(self.root), self.baseline)

    def test_switch_all_five_runtimes_canonical_unchanged(self):
        previous = None
        for runtime_id in ALL_RUNTIME_IDS:
            if previous is not None:
                self.renderer.switch(previous, runtime_id)
            else:
                self.renderer.install(runtime_id)
            previous = runtime_id
            self.assertEqual(canonical_snapshot(self.root), self.baseline)
        self.assertIsNotNone(previous)


if __name__ == "__main__":
    unittest.main(verbosity=2)

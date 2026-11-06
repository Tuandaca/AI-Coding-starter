#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M5: Fail-open tests.

Covers requirement 51 (TEST PLAN — FAIL OPEN):
  - unknown runtime
  - missing adapter
  - malformed adapter
  - runtime absent
  - canonical project remains readable/valid
  - no canonical files modified

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

from core.spec import read_project_spec, build_project_spec, write_project_spec  # noqa: E402
from core.state import (  # noqa: E402
    read_state, build_initial_state, build_resources_lock,
    write_resources_lock, write_state,
)

ADAPTERS_DIR = REPO_ROOT / "runtime-adapters"


def make_canonical_project(root, project_name="FailOpen Project"):
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


def canonical_bytes(root):
    state_dir = Path(root) / ".ai-coding-starter"
    return {
        name: (state_dir / name).read_bytes()
        for name in ("project.yaml", "state.yaml", "resources.lock")
    }


class TestFailOpen(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="m5-failopen-"))
        self.root = make_canonical_project(self.temp_dir)
        self.renderer = GenericRenderer(self.root, adapters_dir=str(ADAPTERS_DIR))
        self.baseline = canonical_bytes(self.root)

    def test_unknown_runtime_returns_error_and_keeps_canonical(self):
        result = self.renderer.install("not-a-real-runtime")
        self.assertFalse(result.ok)
        self.assertTrue(result.errors)
        self.assertEqual(canonical_bytes(self.root), self.baseline)

    def test_missing_adapter_returns_error_and_keeps_canonical(self):
        renderer = GenericRenderer(self.root, adapters_dir=self.temp_dir / "no-adapters")
        result = renderer.install("codex")
        self.assertFalse(result.ok)
        self.assertEqual(canonical_bytes(self.root), self.baseline)

    def test_malformed_adapter_returns_error_and_keeps_canonical(self):
        adapter_dir = self.temp_dir / "bad-adapters"
        adapter_dir.mkdir()
        (adapter_dir / "malformed.yaml").write_text("{ not valid json", encoding="utf-8")
        renderer = GenericRenderer(self.root, adapters_dir=str(adapter_dir))
        result = renderer.install("malformed")
        self.assertFalse(result.ok)
        self.assertEqual(canonical_bytes(self.root), self.baseline)

    def test_runtime_absent_detection_fail_open(self):
        result = self.renderer.detect("codex")
        self.assertFalse(result.detected)
        self.assertEqual(canonical_bytes(self.root), self.baseline)

    def test_render_without_canonical_state_fail_open(self):
        # project root with no .ai-coding-starter at all.
        empty_root = self.temp_dir / "empty"
        empty_root.mkdir()
        renderer = GenericRenderer(empty_root, adapters_dir=str(ADAPTERS_DIR))
        result = renderer.install("codex")
        self.assertFalse(result.ok)
        self.assertTrue(result.errors)
        # No runtime output file created (install may create the dir, but not the output).
        self.assertFalse((empty_root / ".codex/AGENTS.md").exists())

    def test_canonical_state_still_readable_after_failures(self):
        self.renderer.install("not-a-real-runtime")
        self.renderer.install("codex")  # valid, writes runtime file only
        spec = read_project_spec(self.root / ".ai-coding-starter" / "project.yaml")
        self.assertEqual(spec.name, "FailOpen Project")
        state = read_state(self.root / ".ai-coding-starter" / "state.yaml")
        self.assertEqual(state.phase, "planning")


if __name__ == "__main__":
    unittest.main(verbosity=2)

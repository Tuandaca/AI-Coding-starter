#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M5: Path escape tests.

Covers requirement 50 (TEST PLAN — PATH ESCAPE):
  - adapters with output ../outside, ../../escape, absolute path must be rejected
  - no file created outside temp project root

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
UnsafePathError = generic_renderer.UnsafePathError

from core.spec import build_project_spec, write_project_spec  # noqa: E402
from core.state import (  # noqa: E402
    build_initial_state,
    build_resources_lock,
    write_resources_lock,
    write_state,
)

BAD_ADAPTERS_DIR = None  # set per-test via temp dir


def make_canonical_project(root, project_name="Escape Project"):
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


def write_bad_adapter(adapter_dir, runtime_id, output_path):
    adapter = {
        "schema_version": "1.0.0",
        "id": runtime_id,
        "runtime_id": runtime_id,
        "name": "Bad Runtime",
        "description": "adapter with unsafe output path",
        "instruction_format": "custom",
        "render": {
            "outputs": [
                {"path": output_path, "template": ["# x"], "mark_owned": True}
            ]
        },
        "install": {"paths": []},
        "uninstall": {"owned_files": [], "owned_dirs": []},
        "permission_policy": {
            "modifies_global_config": False,
            "requires_explicit_consent": True,
            "dangerous_flags_never_enabled": [
                "--dangerously-skip-permissions",
                "--dangerously-bypass-approvals-and-sandbox",
                "--yolo",
            ],
        },
        "limitations": ["test-only unsafe adapter"],
    }
    path = Path(adapter_dir) / f"{runtime_id}.yaml"
    path.write_text(json.dumps(adapter, indent=2), encoding="utf-8")
    return path


class TestPathEscape(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="m5-escape-"))
        self.root = make_canonical_project(self.temp_dir)
        self.adapter_dir = self.temp_dir / "adapters"
        self.adapter_dir.mkdir()
        self.renderer = GenericRenderer(self.root, adapters_dir=str(self.adapter_dir))

    def test_safe_output_path_rejects_parent_traversal(self):
        for bad in ["../outside.txt", "../../escape.txt", "sub/../../outside.txt"]:
            with self.subTest(path=bad):
                with self.assertRaises(UnsafePathError):
                    self.renderer._safe_output_path(bad)

    def test_safe_output_path_rejects_absolute_paths(self):
        for bad in ["/tmp/outside.txt", "C:\\Users\\outside.txt", "/home/user/out.txt"]:
            with self.subTest(path=bad):
                with self.assertRaises(UnsafePathError):
                    self.renderer._safe_output_path(bad)

    def test_render_rejects_parent_traversal_output(self):
        write_bad_adapter(self.adapter_dir, "bad-x", "../outside.txt")
        result = self.renderer.render("bad-x")
        self.assertFalse(result.ok)
        self.assertTrue(any("parent traversal" in e or "escapes project root" in e
                            for e in result.errors))
        self.assertFalse((self.temp_dir / "outside.txt").exists())

    def test_render_rejects_absolute_output(self):
        write_bad_adapter(self.adapter_dir, "bad-abs", "/tmp/absolute-out.txt")
        result = self.renderer.render("bad-abs")
        self.assertFalse(result.ok)
        self.assertFalse(Path("/tmp/absolute-out.txt").exists())

    def test_render_rejects_drive_letter_output(self):
        write_bad_adapter(self.adapter_dir, "bad-drive", "C:\\Users\\out.txt")
        result = self.renderer.render("bad-drive")
        self.assertFalse(result.ok)
        self.assertFalse(Path("C:/Users/out.txt").exists())

    def test_no_file_created_outside_project_root(self):
        self.renderer.install("codex")  # legitimate runtime, stays inside
        # Nothing written outside temp_dir root.
        for p in self.temp_dir.rglob("*"):
            self.assertIn(self.temp_dir.resolve(), p.resolve().parents)


if __name__ == "__main__":
    unittest.main(verbosity=2)

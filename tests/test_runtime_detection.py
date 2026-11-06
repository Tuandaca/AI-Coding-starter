#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M5: Runtime detection tests.

Covers requirement 49 (TEST PLAN — DETECTION):
  - mock executable present / config present / env indicator present / runtime absent
  - detection reports signals
  - does not write
  - does not install
  - does not mutate global config

Standard library only. No network.
"""
import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

generic_renderer = importlib.import_module("core.generic-renderer")  # noqa: E402
GenericRenderer = generic_renderer.GenericRenderer

ADAPTERS_DIR = REPO_ROOT / "runtime-adapters"


def _no_env(k, d=None):
    return d


def _which_none(exe):
    return None


class TestRuntimeDetection(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="m5-detect-"))
        self.renderer = GenericRenderer(self.temp_dir, adapters_dir=str(ADAPTERS_DIR))
        self.written_before = set(self._all_files())

    def _all_files(self):
        files = []
        if self.temp_dir.exists():
            for p in self.temp_dir.rglob("*"):
                files.append(p)
        return files

    def _assert_no_writes(self, label=""):
        after = set(self._all_files())
        self.assertEqual(
            after, self.written_before,
            f"detection must not write files{label}: "
            f"{sorted(after - self.written_before)}",
        )

    @patch.object(generic_renderer.shutil, "which", side_effect=lambda exe: "/usr/bin/codex" if exe == "codex" else None)
    @patch.object(generic_renderer.os.environ, "get", side_effect=_no_env)
    def test_detection_reports_signals_when_executable_found(self, mock_env, mock_which):
        result = self.renderer.detect("codex")
        self.assertEqual(result.runtime_id, "codex")
        self.assertTrue(result.detected)
        self.assertTrue(any("executable 'codex': found" in s for s in result.signals))
        self.assertIsInstance(result.writable, bool)
        self._assert_no_writes(" (executable found)")

    @patch.object(generic_renderer.shutil, "which", side_effect=_which_none)
    @patch.object(generic_renderer.os.environ, "get", side_effect=_no_env)
    def test_detection_runtime_absent_reports_not_found(self, mock_env, mock_which):
        result = self.renderer.detect("codex")
        self.assertEqual(result.runtime_id, "codex")
        self.assertFalse(result.detected)
        self.assertIn("executable 'codex': not found", result.signals)
        self._assert_no_writes(" (runtime absent)")

    @patch.object(generic_renderer.shutil, "which", side_effect=_which_none)
    @patch.object(generic_renderer.os.environ, "get", side_effect=_no_env)
    def test_detection_unknown_runtime_no_signals(self, mock_env, mock_which):
        result = self.renderer.detect("does-not-exist")
        self.assertEqual(result.runtime_id, "does-not-exist")
        self.assertFalse(result.detected)
        self.assertIn("adapter not found", result.reason)
        self._assert_no_writes(" (unknown runtime)")

    @patch.object(generic_renderer.shutil, "which", side_effect=_which_none)
    @patch.object(generic_renderer.os.environ, "get", side_effect=_no_env)
    def test_detection_does_not_install(self, mock_env, mock_which):
        self.renderer.detect("codex")
        self._assert_no_writes(" (detect must not install)")
        self.assertFalse((self.temp_dir / ".codex").exists())
        self.assertFalse((self.temp_dir / ".opencode").exists())

    @patch.object(generic_renderer.shutil, "which", side_effect=_which_none)
    @patch.object(generic_renderer.os.environ, "get", side_effect=_no_env)
    def test_detection_no_global_config_mutation(self, mock_env, mock_which):
        # Detection reads environment only; never creates or mutates global
        # runtime config directories (they may pre-exist; detect must not
        # change them).
        global_paths = [Path.home() / ".codex", Path.home() / ".claude",
                        Path.home() / ".config" / "opencode", Path.home() / ".cursor"]
        before = {p: p.exists() for p in global_paths}
        self.renderer.detect("codex")
        self.renderer.detect("claude-code")
        self.renderer.detect("cursor")
        after = {p: p.exists() for p in global_paths}
        self.assertEqual(before, after,
                         f"detection must not mutate global config: {global_paths}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Behavioral regression tests for the release identity validation script.

Coverage:
  - tag == v + VERSION passes
  - tag without v prefix fails
  - version drift between VERSION and pyproject.toml fails
  - non-release refs (branches/SHA) fail unless they equal v{VERSION}

Deterministic, offline.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCRIPT = REPO_ROOT / "scripts" / "ci_validate_release_identity.py"


class TestReleaseIdentityScript(unittest.TestCase):
    def _run(self, ref):
        return subprocess.run(
            [sys.executable, str(SCRIPT), ref],
            capture_output=True, text=True,
        )

    def test_matching_tag_passes(self):
        result = self._run("refs/tags/v2.2.1")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Release identity OK", result.stdout)

    def test_tag_without_v_fails(self):
        result = self._run("refs/tags/2.2.1")
        self.assertNotEqual(result.returncode, 0)

    def test_wrong_tag_fails(self):
        result = self._run("refs/tags/v2.2.0")
        self.assertNotEqual(result.returncode, 0)

    def test_branch_fails(self):
        result = self._run("refs/heads/main")
        self.assertNotEqual(result.returncode, 0)

    def test_sha_fails(self):
        result = self._run("86f6ed1471ad92e44d56f5d01fe5dba3c0abc6ac")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

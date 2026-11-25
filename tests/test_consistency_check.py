#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression tests for scripts/ci_consistency_check.py drift detection.

These tests mirror the consistency conditions enforced by
ci_consistency_check.py using independent derivation, and verify the check
script itself fails when repository state drifts.

Deterministic, offline.
"""
import subprocess
import sys
import tomllib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

CHECK_SCRIPT = REPO_ROOT / "scripts" / "ci_consistency_check.py"
VERSION_PATH = REPO_ROOT / "VERSION"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
README_PATH = REPO_ROOT / "README.md"
PROJECT_STATUS_PATH = REPO_ROOT / "PROJECT_STATUS.md"
CATALOG_DIR = REPO_ROOT / "catalog"


def read_version() -> str:
    return VERSION_PATH.read_text(encoding="utf-8").strip()


class TestConsistencyChecks(unittest.TestCase):
    def test_version_matches_pyproject(self):
        version = read_version()
        pyproject = tomllib.loads(
            PYPROJECT_PATH.read_text(encoding="utf-8")
        )
        pyproject_version = str(pyproject.get("project", {}).get("version", ""))
        self.assertEqual(pyproject_version, version)

    def test_readme_reports_current_version(self):
        version = read_version()
        readme = README_PATH.read_text(encoding="utf-8")
        self.assertIn(f"V{version}", readme)

    def test_project_status_reports_current_version(self):
        version = read_version()
        status = PROJECT_STATUS_PATH.read_text(encoding="utf-8")
        self.assertIn(f"V{version}", status)

    def test_catalog_project_types_derivable(self):
        import json
        data = json.loads((CATALOG_DIR / "project-types.yaml").read_text(encoding="utf-8"))
        count = len(data.get("project_types", []))
        self.assertGreater(count, 0)

    def test_catalog_stack_bundles_derivable(self):
        import json
        data = json.loads((CATALOG_DIR / "stack-bundles.yaml").read_text(encoding="utf-8"))
        count = len(data.get("stack_bundles", []))
        self.assertGreater(count, 0)

    def test_scaffold_support_tracks_catalog(self):
        import json
        from core.stack_scaffold import SCAFFOLD_SUPPORT, BUNDLE_TEMPLATES  # noqa: WPS433
        sb_data = json.loads((CATALOG_DIR / "stack-bundles.yaml").read_text(encoding="utf-8"))
        catalog_ids = {str(b.get("id")) for b in sb_data.get("stack_bundles", []) if isinstance(b, dict)}
        for bid in set(SCAFFOLD_SUPPORT) | set(BUNDLE_TEMPLATES):
            self.assertIn(bid, catalog_ids, f"scaffold bundle {bid!r} not in catalog")

    def test_no_stale_version_markers(self):
        text = (REPO_ROOT / "core" / "stack_scaffold.py").read_text(encoding="utf-8")
        for marker in ("v2.1.1", "2.1.1", "V2.1.1"):
            self.assertNotIn(marker, text, f"stale version marker {marker!r} present")

    def test_consistency_script_exits_zero(self):
        result = subprocess.run([sys.executable, str(CHECK_SCRIPT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_consistency_script_detects_version_drift(self):
        """Temporarily break VERSION/pyproject sync; script must fail; restore after."""
        original_pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")
        try:
            text = original_pyproject
            import re as _re
            drifted = _re.sub(r'^version\s*=\s*"[^"]+"', 'version = "9.9.9"', text, flags=_re.MULTILINE)
            self.assertNotEqual(drifted, original_pyproject)
            PYPROJECT_PATH.write_text(drifted, encoding="utf-8")
            result = subprocess.run([sys.executable, str(CHECK_SCRIPT)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0, "script should fail on version drift")
            self.assertIn("pyproject.toml version", result.stdout + result.stderr)
        finally:
            PYPROJECT_PATH.write_text(original_pyproject, encoding="utf-8")

    def test_consistency_script_detects_readme_drift(self):
        original_readme = README_PATH.read_text(encoding="utf-8")
        try:
            version = read_version()
            drifted = original_readme.replace(f"V{version}", f"V{version[:-1]}9")
            self.assertNotEqual(drifted, original_readme)
            README_PATH.write_text(drifted, encoding="utf-8")
            result = subprocess.run([sys.executable, str(CHECK_SCRIPT)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0, "script should fail on README drift")
        finally:
            README_PATH.write_text(original_readme, encoding="utf-8")


if __name__ == "__main__":
    unittest.main(verbosity=2)

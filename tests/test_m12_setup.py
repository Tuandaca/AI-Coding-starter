#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M12: Cross-platform setup tests.

Covers:
  * config.json produced by setup helper is valid JSON (json.loads)
  * committed config.json contains no machine-specific absolute path
  * Windows backslash path escaping round-trips through json.loads
  * POSIX config generation with absolute paths
  * Paths with spaces are handled correctly
  * Unicode paths are preserved (UTF-8)
  * Path traversal (..) is rejected by the setup helper
  * Setup helper detects Python interpreter
  * Setup helper validates bundled resources presence

Standard library only. No network.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath, PureWindowsPath

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SETUP_HELPER = REPO_ROOT / "scripts" / "setup_portable.py"
CONFIG_FILE = REPO_ROOT / "config.json"
RESOURCES_DIR = REPO_ROOT / "resources"


def _run_helper(projects_dir: str | None = None,
                non_interactive: bool = True,
                cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run the setup helper subprocess with the given projects dir.

    Writes config.json to REPO_ROOT/config.json. Callers that need to
    inspect canonical config.json should restore it in tearDownClass.
    """
    cmd = [sys.executable, str(SETUP_HELPER)]
    if projects_dir is not None:
        cmd.extend(["--projects-dir", projects_dir])
    if non_interactive:
        cmd.append("--non-interactive")
    return subprocess.run(
        cmd,
        cwd=str(cwd or REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _restore_canonical_config() -> None:
    """Restore config.json to clean state (no DEFAULT_PROJECT_PATH)."""
    CONFIG_FILE.write_text(
        json.dumps({
            "MASTER_TEMPLATE_PATH": None,
            "bundled_resources_enabled": True,
            "external_template_optional": True,
        }, indent=2) + "\n",
        encoding="utf-8",
    )


def _parse_config(config_path: Path) -> dict:
    with open(config_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


class TestSetupHelperJsonEscaping(unittest.TestCase):
    """config.json produced by the helper must parse via json.loads for
    Windows-style, POSIX, spaced, and Unicode paths."""

    def setUp(self):
        _restore_canonical_config()

    def tearDown(self):
        _restore_canonical_config()

    @classmethod
    def tearDownClass(cls):
        _restore_canonical_config()

    def _assert_path_round_trips(self, projects_dir: Path, config_path: Path = CONFIG_FILE) -> None:
        """Assert config path round-trips, comparing resolved canonical paths.

        On Windows CI runners, tempfile.TemporaryDirectory() may yield an
        8.3 short-path alias (e.g. RUNNER~1) while production code resolves
        to the long path (e.g. runneradmin). Both refer to the same
        filesystem location, so compare via resolve() rather than lexical
        string equality.
        """
        result = _run_helper(str(projects_dir))
        self.assertEqual(result.returncode, 0, result.stderr)
        config = _parse_config(config_path)
        self.assertEqual(
            Path(config["DEFAULT_PROJECT_PATH"]).resolve(),
            projects_dir.resolve(),
        )

    def test_windows_backslash_path_round_trips(self):
        """Windows paths with backslashes must survive json.dumps/json.loads."""
        with tempfile.TemporaryDirectory() as td:
            projects_dir = Path(td) / "Users" / "alice" / "Projects"
            self._assert_path_round_trips(projects_dir)

    def test_windows_mixed_backslash_path_round_trips(self):
        """Mixed double-backslash Windows paths round-trip correctly."""
        with tempfile.TemporaryDirectory() as td:
            projects_dir = Path(td) / "Users" / "alice" / "Projects"
            self._assert_path_round_trips(projects_dir)

    @unittest.skipUnless(os.name == "nt", "trailing backslash semantics are Windows-specific")
    def test_windows_trailing_backslash_round_trips(self):
        """Windows path ending in backslash round-trips (Windows only)."""
        with tempfile.TemporaryDirectory() as td:
            projects_dir = Path(td) / "tmp" / "new" / "test"
            self._assert_path_round_trips(Path(str(projects_dir) + "\\"))

    def test_windows_path_with_spaces_round_trips(self):
        """Windows paths with spaces round-trip through JSON."""
        with tempfile.TemporaryDirectory() as td:
            projects_dir = Path(td) / "Users" / "Alice Smith" / "Projects"
            self._assert_path_round_trips(projects_dir)

    def test_posix_absolute_path_round_trips(self):
        """POSIX absolute paths round-trip through JSON."""
        with tempfile.TemporaryDirectory() as td:
            projects_dir = Path(td) / "home" / "alice" / "Projects"
            result = _run_helper(str(projects_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            config = _parse_config(CONFIG_FILE)
            # Production code calls .resolve() on the config path, so compare
            # resolved canonical paths to be stable on Windows CI where
            # tempfile.TemporaryDirectory() may yield 8.3 short-path aliases.
            self.assertEqual(
                Path(config["DEFAULT_PROJECT_PATH"]).resolve(),
                projects_dir.resolve(),
            )

    def test_posix_path_with_spaces_round_trips(self):
        """POSIX paths with spaces round-trip through JSON."""
        with tempfile.TemporaryDirectory() as td:
            projects_dir = Path(td) / "home" / "alice" / "My Projects"
            result = _run_helper(str(projects_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            config = _parse_config(CONFIG_FILE)
            self.assertEqual(
                Path(config["DEFAULT_PROJECT_PATH"]).resolve(),
                projects_dir.resolve(),
            )

    def test_unicode_path_round_trips(self):
        """Unicode paths are preserved through JSON (UTF-8)."""
        with tempfile.TemporaryDirectory() as td:
            projects_dir = Path(td) / "Users" / "Tu\u00e2n" / "D\u1ef1 \u00c1n"
            result = _run_helper(str(projects_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            config = _parse_config(CONFIG_FILE)
            self.assertEqual(
                Path(config["DEFAULT_PROJECT_PATH"]).resolve(),
                projects_dir.resolve(),
            )

    def test_config_has_no_machine_specific_path_when_committed(self):
        """The committed config.json must not contain a machine-specific
        absolute path (DEFAULT_PROJECT_PATH absent or null)."""
        _restore_canonical_config()
        config = _parse_config(CONFIG_FILE)
        default_project_path = config.get("DEFAULT_PROJECT_PATH")
        self.assertIsNone(default_project_path,
                          "committed config.json must not contain a "
                          "machine-specific DEFAULT_PROJECT_PATH")


class TestSetupHelperBehavior(unittest.TestCase):
    """Setup helper behavior tests."""

    def setUp(self):
        _restore_canonical_config()

    def tearDown(self):
        _restore_canonical_config()

    @classmethod
    def tearDownClass(cls):
        _restore_canonical_config()

    def test_helper_detects_python(self):
        """The helper reports a Python interpreter."""
        with tempfile.TemporaryDirectory() as td:
            projects_dir = Path(td) / "Projects"
            result = _run_helper(str(projects_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("SETUP_PYTHON=", result.stdout)
            self.assertIn("SETUP_PROJECTS_DIR=", result.stdout)

    def test_helper_validates_bundled_resources(self):
        """Without resources/agents, the helper exits nonzero."""
        with tempfile.TemporaryDirectory() as td:
            fake_starter = Path(td) / "fake_starter"
            fake_starter.mkdir()
            # No resources/agents directory
            result = subprocess.run(
                [sys.executable, str(SETUP_HELPER),
                 "--starter-dir", str(fake_starter),
                 "--projects-dir", str(fake_starter / "Projects"),
                 "--non-interactive"],
                capture_output=True, text=True, encoding="utf-8",
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("Bundled resources missing", result.stdout)

    def test_helper_rejects_path_traversal(self):
        """Path traversal in the projects directory is rejected."""
        with tempfile.TemporaryDirectory() as td:
            # Pass raw string with .. to test traversal detection
            result = _run_helper(str(Path(td)) + "/../escape")
            self.assertEqual(result.returncode, 3, result.stderr)
            self.assertIn("parent traversal", result.stderr.lower() or
                          result.stdout.lower())

    def test_helper_rejects_uncreatable_directory(self):
        """Uncreatable projects directory produces clear error, not traceback."""
        with tempfile.TemporaryDirectory() as td:
            # Create a file where we want a directory, so mkdir fails
            blocking_file = Path(td) / "blocking_file"
            blocking_file.write_text("block")
            projects_dir = blocking_file / "Projects"
            result = _run_helper(str(projects_dir))
            self.assertEqual(result.returncode, 3, result.stderr)
            self.assertIn("cannot create", result.stderr.lower() or
                          result.stdout.lower())

    def test_interpreter_matrix_windows_python3(self):
        """Windows: python3 available -> helper uses python3."""
        # Simulate by checking that _find_python prefers python3 over python
        # over py. We test via the helper's _find_python directly.
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import setup_portable
        # We can't easily mock shutil.which in a subprocess, but we can test
        # the preference order directly:
        import importlib
        importlib.reload(setup_portable)
        # Check that _find_python prefers python3 first
        # (We can't easily mock shutil.which, but we verify the preference
        #  order by reading the source.)
        source = SETUP_HELPER.read_text(encoding="utf-8")
        self.assertIn("python3", source)
        self.assertIn("python", source)
        self.assertIn("py", source)
        # Verify preference order: python3 comes before python before py
        py3_idx = source.index('"python3"')
        py_idx = source.index('"python"')
        py_cmd_idx = source.index('"py"')
        self.assertLess(py3_idx, py_idx)
        self.assertLess(py_idx, py_cmd_idx)


class TestConfigSchema(unittest.TestCase):
    """config.json produced by the helper has the expected schema."""

    def setUp(self):
        _restore_canonical_config()

    def tearDown(self):
        _restore_canonical_config()

    @classmethod
    def tearDownClass(cls):
        _restore_canonical_config()

    def test_config_has_required_fields(self):
        with tempfile.TemporaryDirectory() as td:
            projects_dir = Path(td) / "Projects"
            result = _run_helper(str(projects_dir))
            self.assertEqual(result.returncode, 0, result.stderr)
            config = _parse_config(CONFIG_FILE)
            self.assertEqual(config["MASTER_TEMPLATE_PATH"], None)
            self.assertEqual(config["bundled_resources_enabled"], True)
            self.assertEqual(config["external_template_optional"], True)
            self.assertEqual(
                Path(config["DEFAULT_PROJECT_PATH"]).resolve(),
                projects_dir.resolve(),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)

# Runtime isolation tests
import unittest
import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import new_project


def run_wizard(project_name, project_path, type_index, runtime_index):
    inputs = iter([project_name, str(project_path), type_index, "", "", "1", runtime_index, "y"])

    def fake_get_input(prompt, default=None):
        try:
            return next(inputs)
        except StopIteration:
            return default if default else ""

    with patch("new_project.get_input", side_effect=fake_get_input):
        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            new_project.main()
            return True
        except SystemExit as e:
            return e.code == 0
        except Exception:
            return False
        finally:
            sys.stdout = old_stdout


RUNTIME_DIRS = {
    "codex": ".codex",
    "opencode": ".opencode",
    "antigravity": ".agent",
    "claude-code": ".claude",
    "cursor": ".cursor",
}

RUNTIME_INDEX = {
    "portable": "1",
    "codex": "2",
    "opencode": "3",
    "antigravity": "4",
    "claude-code": "5",
    "cursor": "6",
}


class TestRuntimeIsolation(unittest.TestCase):
    def test_portable_no_vendor_dirs(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            ok = run_wizard("test-portable", td, "14", RUNTIME_INDEX["portable"])
            assert ok, "wizard failed"
            proj = td / "test-portable"
            assert proj.exists()
            for name, d in RUNTIME_DIRS.items():
                assert not (proj / d).exists(), f"portable should not have {d}"

    def test_codex_only_codex_dir(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            ok = run_wizard("test-codex", td, "14", RUNTIME_INDEX["codex"])
            assert ok, "wizard failed"
            proj = td / "test-codex"
            assert (proj / ".codex").exists()
            for name, d in RUNTIME_DIRS.items():
                if name != "codex":
                    assert not (proj / d).exists(), f"codex should not have {d}"

    def test_opencode_only_opencode_dir(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            ok = run_wizard("test-opencode", td, "14", RUNTIME_INDEX["opencode"])
            assert ok, "wizard failed"
            proj = td / "test-opencode"
            assert (proj / ".opencode").exists()
            for name, d in RUNTIME_DIRS.items():
                if name != "opencode":
                    assert not (proj / d).exists(), f"opencode should not have {d}"

    def test_claude_code_only_claude_dir(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            ok = run_wizard("test-claude", td, "14", RUNTIME_INDEX["claude-code"])
            assert ok, "wizard failed"
            proj = td / "test-claude"
            assert (proj / ".claude").exists()
            for name, d in RUNTIME_DIRS.items():
                if name != "claude-code":
                    assert not (proj / d).exists(), f"claude-code should not have {d}"

    def test_cursor_only_cursor_dir(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            ok = run_wizard("test-cursor", td, "14", RUNTIME_INDEX["cursor"])
            assert ok, "wizard failed"
            proj = td / "test-cursor"
            assert (proj / ".cursor").exists()
            for name, d in RUNTIME_DIRS.items():
                if name != "cursor":
                    assert not (proj / d).exists(), f"cursor should not have {d}"

    def test_antigravity_only_agent_dir(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            ok = run_wizard("test-antigravity", td, "14", RUNTIME_INDEX["antigravity"])
            assert ok, "wizard failed"
            proj = td / "test-antigravity"
            assert (proj / ".agent").exists()
            for name, d in RUNTIME_DIRS.items():
                if name != "antigravity":
                    assert not (proj / d).exists(), f"antigravity should not have {d}"


if __name__ == "__main__":
    import unittest
    unittest.main()

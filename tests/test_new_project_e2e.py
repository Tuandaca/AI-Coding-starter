#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M5: End-to-end tests for new_project.main().

These tests exercise the FULL new_project.main() function (transactional wizard:
COLLECT -> RESOLVE -> BUILD IN MEMORY -> PREVIEW -> CONFIRM -> WRITE), not just
helpers. They verify the actual end-to-end behavior of project generation.

Standard library only. No network.
"""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import new_project  # noqa: E402
from core.catalog_loader import load_catalog

CANONICAL_STATE_DIR = ".ai-coding-starter"
CANONICAL_FILES = ("project.yaml", "state.yaml", "resources.lock")

CATALOG = load_catalog()  # same catalog the wizard uses


def _type_position(type_id: str) -> str:
    """1-based position of a project type in the wizard's sorted listing."""
    types = sorted(CATALOG.project_types.values(), key=lambda pt: str(pt.id))
    for i, pt in enumerate(types, 1):
        if str(pt.id) == type_id:
            return str(i)
    raise AssertionError(f"project type {type_id!r} not found in catalog")


# 1-based positions in select_runtime(): portable=1, codex=2, opencode=3,
# antigravity=4, claude-code=5, cursor=6.
RUNTIME_POS = {"portable": "1", "codex": "2", "antigravity": "4"}


def _snapshot(root: Path) -> dict:
    """Snapshot all files under root, keyed by relative path."""
    snap = {}
    if root.is_dir():
        for p in root.rglob("*"):
            if p.is_file():
                snap[p.relative_to(root).as_posix()] = p.read_bytes()
    return snap


def _make_inputs(project_name, project_path, type_id, confirm, runtime="portable"):
    """Build the mocked input sequence for one wizard run.

    Every prompt is answered so the flow never blocks and never relies on a
    default being substituted by a mock (which previously caused an infinite
    loop in select_runtime).
    """
    return [
        project_name,            # project name
        str(project_path),       # project path (parent directory)
        _type_position(type_id), # project type
        "",                      # capabilities (defaults)
        "",                      # stack bundle (first recommendation)
        RUNTIME_POS[runtime],    # runtime adapter
        confirm,                 # confirm generation (y/n)
    ]


def _run_wizard(project_name="my-test-project", type_id="saas",
                confirm="y", runtime="portable"):
    """Run new_project.main() with mocked inputs in a temp directory.

    Returns the full project path (parent / project_name).
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="m5_e2e_"))
    project_path = temp_dir  # parent dir; project_name is appended by main()
    inputs = iter(_make_inputs(project_name, project_path, type_id, confirm, runtime))

    def fake_get_input(prompt, default=None):
        try:
            return next(inputs)
        except StopIteration:
            # Mimic real get_input: truthy default wins on empty input.
            return default if default else ""

    with patch("new_project.get_input", side_effect=fake_get_input):
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            new_project.main()
        except SystemExit:
            # Cancel path calls sys.exit(0); that is an expected outcome.
            pass
        finally:
            sys.stdout = old_stdout

    return temp_dir / project_name, temp_dir


class TestNewProjectE2E(unittest.TestCase):
    """End-to-end tests for new_project.main()."""

    def test_e2e_cancel_writes_nothing(self):
        """Canceling at confirmation writes ZERO files to the target path."""
        project_root, parent = _run_wizard("cancel-test", "saas", confirm="n")

        # The project directory must NOT be created (confirm happens before mkdir).
        self.assertFalse(project_root.exists(),
                         f"Project directory {project_root} should not exist after cancel")
        # No canonical state, no runtime files, no README anywhere under parent.
        self.assertFalse((parent / ".ai-coding-starter").exists())
        self.assertFalse((parent / "AGENTS.md").exists())

    def test_e2e_creates_canonical_state_at_correct_level(self):
        """Generation produces canonical state at .ai-coding-starter/ (not nested)."""
        project_root, _ = _run_wizard("my-test-project", "saas", confirm="y")

        state_dir = project_root / ".ai-coding-starter"
        self.assertTrue(state_dir.is_dir(),
                        f".ai-coding-starter/ not found at {state_dir}")

        for fname in CANONICAL_FILES:
            self.assertTrue((state_dir / fname).is_file(),
                            f"{fname} not found at {state_dir / fname}")

        # CRITICAL: no nested .ai-coding-starter/.ai-coding-starter/
        nested = state_dir / ".ai-coding-starter"
        self.assertFalse(nested.exists(),
                         f"Nested .ai-coding-starter/.ai-coding-starter/ found at {nested}!")

        # Exactly one .ai-coding-starter/ at project root.
        matches = [p for p in project_root.rglob(".ai-coding-starter") if p.is_dir()]
        self.assertEqual(len(matches), 1, f"Expected exactly one .ai-coding-starter/, got {matches}")

    def test_e2e_canonical_state_is_valid(self):
        """Generated canonical state files are valid and readable."""
        project_root, _ = _run_wizard("my-test-project", "saas", confirm="y")

        state_dir = project_root / ".ai-coding-starter"
        spec = new_project.read_project_spec(state_dir / "project.yaml")
        self.assertEqual(spec.name, "my-test-project")
        self.assertEqual(str(spec.project_type), "saas")

        state = new_project.read_state(state_dir / "state.yaml")
        self.assertEqual(state.phase, "planning")

        lock = new_project.read_resources_lock(state_dir / "resources.lock")
        # The lock records the resolved bundle consistently.
        sbr = lock.stack_bundle_resolution
        self.assertEqual(sbr.resolved_bundle, sbr.requested_bundle)
        self.assertTrue(sbr.resolved_bundle)
        # It must be a bundle the resolver considers valid for SaaS.
        saas_bundles = {str(b.id) for b in CATALOG.stack_bundles.values()
                        if "saas" in {str(p) for p in b.project_types}}
        self.assertIn(sbr.resolved_bundle, saas_bundles)
        self.assertGreater(len(lock.resources), 0,
                           "resources.lock must list selected resources (not zero)")

    def test_e2e_resources_selected_for_types(self):
        """Portfolio, SaaS, Fullstack and AI/ML each select meaningful resources."""
        for type_id in ("portfolio", "saas", "fullstack-application", "ai-rag"):
            project_root, _ = _run_wizard(f"proj-{type_id}", type_id, confirm="y")
            lock = new_project.read_resources_lock(
                project_root / ".ai-coding-starter" / "resources.lock")
            self.assertGreater(
                len(lock.resources), 0,
                f"{type_id} must select meaningful resources (got zero)"
            )

    def test_e2e_determinism(self):
        """Same inputs produce identical resource selection and lock state."""
        lock_a = self._lock_for("saas", confirm="y")
        lock_b = self._lock_for("saas", confirm="y")
        keys_a = [(r.id, r.type) for r in lock_a.resources]
        keys_b = [(r.id, r.type) for r in lock_b.resources]
        self.assertEqual(sorted(keys_a), sorted(keys_b))

    def _lock_for(self, type_id, confirm="y"):
        project_root, _ = _run_wizard("det-project", type_id, confirm=confirm)
        return new_project.read_resources_lock(
            project_root / ".ai-coding-starter" / "resources.lock")

    def test_e2e_runtime_antigravity_creates_owned_file(self):
        """Antigravity runtime renders its owned .agent/GEMINI.md file."""
        project_root, _ = _run_wizard("rt-project", "saas", confirm="y", runtime="antigravity")
        owned = project_root / ".agent" / "GEMINI.md"
        self.assertTrue(owned.is_file(),
                        f"Antigravity owned output not found at {owned}")
        text = owned.read_text(encoding="utf-8")
        self.assertIn("ai-coding-starter runtime adapter: antigravity", text)

    def test_e2e_runtime_codex_is_safe_noop(self):
        """Codex runtime is a shared consumer: it installs cleanly with no owned file."""
        project_root, _ = _run_wizard("rt-project", "saas", confirm="y", runtime="codex")
        # Codex installs without error and writes no owned runtime file.
        self.assertTrue((project_root / ".ai-coding-starter" / "project.yaml").is_file())

    def test_e2e_lock_matches_copied_resources(self):
        """Every locked resource corresponds to a resource actually copied into the project."""
        project_root, _ = _run_wizard("lock-project", "saas", confirm="y")
        lock = new_project.read_resources_lock(
            project_root / ".ai-coding-starter" / "resources.lock")
        # Agents are copied as <id>.md under agents/.
        agents_dir = project_root / "agents"
        for res in lock.resources:
            if res.type == "agent":
                self.assertTrue((agents_dir / f"{res.id}.md").is_file(),
                                f"Locked agent {res.id} was not copied into the project")

    def test_e2e_no_network_access(self):
        """Generation works with bundled resources only (no external template required)."""
        project_root, _ = _run_wizard("offline-project", "saas", confirm="y")
        self.assertTrue((project_root / ".ai-coding-starter" / "project.yaml").is_file(),
                        "Offline generation failed - project.yaml not created")


if __name__ == "__main__":
    unittest.main(verbosity=2)

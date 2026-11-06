#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M4 end-to-end portable state integration test.

Coverage:
  - select project type -> capabilities -> resolver -> one M3 bundle
  - generate a temporary project with M4 canonical state
  - valid .ai-coding-starter/project.yaml, state.yaml, resources.lock
  - derived Markdown (AGENTS.md/CONTEXT.md/DECISIONS.md/HANDOFF.md)
  - canonical state reflects the M3 selection (IDs, not display names)
  - .ai-coding-starter/ contains no more than 4 files

Uses input injection (no real terminal), tempfile only, no network,
no external templates, no real user directories.
"""
import io
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import new_project  # noqa: E402
from core.catalog_loader import load_catalog
from core.portable_renderer import render_all
from core.spec import (
    CANONICAL_STATE_DIR,
    PROJECT_YAML,
    build_project_spec,
    read_project_spec,
    write_project_spec,
)
from core.state import (
    STATE_YAML,
    RESOURCES_LOCK,
    build_initial_state,
    build_resources_lock,
    read_state,
    read_resources_lock,
    write_resources_lock,
    write_state,
)

CATALOG_DIR = REPO_ROOT / "catalog"


class TestPortableIntegration(unittest.TestCase):
    def setUp(self):
        # The wizard prints Vietnamese text and emoji; captured stdout must use
        # an explicit UTF-8 stream (Windows console defaults to cp1252).
        self._original_stdout = sys.stdout
        sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8", errors="replace")

        self.catalog = load_catalog(CATALOG_DIR)
        # Sorted project types; saas is 16th (1-based).
        self.inputs = iter(["16", "", ""])
        self.get_input_calls = []

        def fake_get_input(prompt, default=None):
            self.get_input_calls.append((prompt, default))
            try:
                return next(self.inputs)
            except StopIteration:
                return ""

        self.get_input_patcher = patch.object(new_project, "get_input", side_effect=fake_get_input)
        self.get_input_patcher.start()

    def tearDown(self):
        self.get_input_patcher.stop()
        sys.stdout = self._original_stdout

    def test_end_to_end_m3_selection_to_m4_state(self):
        # STEP 1: project type
        project_type_id = new_project.select_project_type(self.catalog)
        self.assertEqual(project_type_id, "saas")

        # STEP 2: capabilities (defaults)
        cap_ids = new_project.select_capabilities(self.catalog, project_type_id)
        self.assertIn("authentication", cap_ids)
        self.assertIn("payments", cap_ids)

        # STEP 3: resolver -> one bundle
        resolution = new_project.resolve_stacks(self.catalog, project_type_id, cap_ids)
        self.assertTrue(resolution.ok, resolution.rejection_reason)
        bundle_id = new_project.select_bundle(resolution, self.catalog)
        self.assertIsNotNone(bundle_id)

        # STEP 4 (M4): generate canonical state into a temp project dir.
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td)
            spec = build_project_spec(
                "Integration App",
                project_type_id=project_type_id,
                capabilities=cap_ids,
                stack_bundle_id=bundle_id,
            )
            write_project_spec(project_root, spec)
            state = build_initial_state(str(spec.id), phase="planning", focus="")
            write_state(project_root, state)
            lock = build_resources_lock(bundle_id, requested_bundle_id=bundle_id)
            write_resources_lock(project_root, lock)
            render_all(project_root, spec, state)

            # Canonical state files exist.
            self.assertTrue((project_root / CANONICAL_STATE_DIR / PROJECT_YAML).exists())
            self.assertTrue((project_root / CANONICAL_STATE_DIR / STATE_YAML).exists())
            self.assertTrue((project_root / CANONICAL_STATE_DIR / RESOURCES_LOCK).exists())

            # .ai-coding-starter/ has exactly 3 files (<= 4).
            ai_files = [p for p in (project_root / CANONICAL_STATE_DIR).iterdir() if p.is_file()]
            self.assertLessEqual(len(ai_files), 4)

            # Derived markdown at project root.
            self.assertTrue((project_root / "AGENTS.md").exists())
            self.assertTrue((project_root / "CONTEXT.md").exists())
            self.assertTrue((project_root / "DECISIONS.md").exists())
            self.assertTrue((project_root / "HANDOFF.md").exists())

            # Canonical state reflects M3 selection (IDs, not display names).
            reloaded = read_project_spec(project_root / CANONICAL_STATE_DIR / PROJECT_YAML)
            self.assertEqual(str(reloaded.project_type), "saas")
            self.assertEqual(str(reloaded.stack_bundle), bundle_id)
            self.assertEqual([str(c) for c in reloaded.capabilities], sorted(cap_ids))

            reloaded_state = read_state(project_root / CANONICAL_STATE_DIR / STATE_YAML)
            self.assertEqual(reloaded_state.phase, "planning")
            self.assertEqual(reloaded_state.completed_tasks, [])

            reloaded_lock = read_resources_lock(
                project_root / CANONICAL_STATE_DIR / RESOURCES_LOCK
            )
            self.assertEqual(reloaded_lock.stack_bundle_resolution.resolved_bundle, bundle_id)
            self.assertEqual(reloaded_lock.resources, [])

            # Round-trips are equivalent.
            self.assertEqual(read_project_spec(project_root / CANONICAL_STATE_DIR / PROJECT_YAML), spec)
            self.assertEqual(read_state(project_root / CANONICAL_STATE_DIR / STATE_YAML), state)


if __name__ == "__main__":
    unittest.main(verbosity=2)

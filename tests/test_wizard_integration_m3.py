#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M3 wizard-level integration test.

Coverage:
  - select project type -> select capabilities -> resolve bundles -> select ONE bundle
  - generator continues with one coherent stack bundle
  - normal M3 selection flow does NOT call blind merge_tech_stacks()

Uses input injection (no real terminal), no network, no external resources.
"""
import inspect
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

CATALOG_DIR = REPO_ROOT / "catalog"

# Inputs: [project type index, capabilities (blank=defaults), bundle (blank=first)].
# The project type index is computed from the loaded catalog to stay robust
# when catalog entries are added or reordered.


class TestWizardIntegrationM3(unittest.TestCase):
    def setUp(self):
        # The wizard prints Vietnamese text and emoji. On Windows, redirected
        # stdout defaults to a legacy code page (cp1252) that cannot encode
        # them, so capture output through an explicit UTF-8 stream.
        self._original_stdout = sys.stdout
        sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8",
                                      errors="replace")

        self.catalog = load_catalog(CATALOG_DIR)
        saas_index = sorted(self.catalog.project_types).index("saas") + 1
        self.inputs = iter([str(saas_index), "", ""])
        self.get_input_calls = []

        def fake_get_input(prompt, default=None):
            self.get_input_calls.append((prompt, default))
            try:
                return next(self.inputs)
            except StopIteration:
                return ""

        self.get_input_patcher = patch.object(new_project, "get_input", side_effect=fake_get_input)
        self.get_input_patcher.start()

        # Track blind-merge calls: the M3 normal flow must never invoke it.
        self.merge_calls = []

        def fake_merge_tech_stacks(*args, **kwargs):
            self.merge_calls.append((args, kwargs))
            raise AssertionError(
                "merge_tech_stacks() must NOT be called by the M3 normal flow"
            )

        self.merge_patcher = patch.object(new_project, "merge_tech_stacks",
                                          side_effect=fake_merge_tech_stacks)
        self.merge_patcher.start()

    def tearDown(self):
        self.merge_patcher.stop()
        self.get_input_patcher.stop()
        sys.stdout = self._original_stdout

    def test_full_selection_flow_returns_one_coherent_bundle(self):
        # STEP 1: Project type
        project_type_id = new_project.select_project_type(self.catalog)
        self.assertEqual(project_type_id, "saas")

        # STEP 2: Capabilities (progressive disclosure: defaults preselected)
        cap_ids = new_project.select_capabilities(self.catalog, project_type_id)
        self.assertEqual(
            cap_ids,
            ["authentication", "authorization", "email", "payments", "subscriptions"],
        )

        # STEP 3: Resolver returns ranked, compatible bundles
        resolution = new_project.resolve_stacks(self.catalog, project_type_id, cap_ids)
        self.assertTrue(resolution.ok, resolution.rejection_reason)
        self.assertGreater(resolution.bundle_count, 0)

        # STEP 4: Select ONE bundle
        bundle_id = new_project.select_bundle(resolution, self.catalog)
        self.assertIsNotNone(bundle_id)
        bundle = self.catalog.stack_bundles[bundle_id]

        # Generator continues with one coherent stack bundle
        tech_stack = new_project.bundle_to_tech_stack(bundle, "SaaS Platform")
        self.assertEqual(tech_stack["bundle_id"], bundle.id)
        self.assertTrue(tech_stack["bundle_name"])
        self.assertEqual(tech_stack["project_type"], "SaaS Platform")
        # One primary frontend / backend / database per bundle (coherence)
        self.assertEqual(tech_stack["frontend"], "Next.js")
        self.assertEqual(tech_stack["backend"], "ASP.NET Core")
        self.assertEqual(tech_stack["database"], "PostgreSQL")

        # Blind multi-preset merge is NOT used in the normal M3 flow
        self.assertEqual(self.merge_calls, [],
                         "merge_tech_stacks must not be called in normal flow")

    def test_capability_input_adds_and_removes_defaults(self):
        # SaaS defaults are kept; index 6 adds file-upload.
        self.inputs = iter(["6"])
        cap_ids = new_project.select_capabilities(self.catalog, "saas")
        self.assertIn("file-upload", cap_ids)
        self.assertIn("authentication", cap_ids)
        self.assertIn("payments", cap_ids)

        # "-2" removes the second item in the displayed relevant list
        # (authentication) while keeping the other defaults.
        self.inputs = iter(["-2"])
        cap_ids = new_project.select_capabilities(self.catalog, "saas")
        self.assertNotIn("authentication", cap_ids)
        self.assertIn("authorization", cap_ids)
        self.assertIn("payments", cap_ids)

    def test_normal_main_flow_uses_catalog_and_resolver(self):
        """The normal path must not use legacy preset selection/merging."""
        source = inspect.getsource(new_project.main)
        self.assertIn("load_starter_catalog()", source)
        self.assertIn("select_project_type(catalog)", source)
        self.assertIn("select_capabilities(catalog, project_type_id)", source)
        self.assertIn("resolve_stacks(catalog, project_type_id, selected_cap_ids)",
                      source)
        self.assertNotIn("select_multiple(", source)
        self.assertNotIn("select_tech_stack(", source)
        self.assertNotIn("merge_tech_stacks(", source)

    def test_resolver_returns_coherent_not_merged_bundles(self):
        resolution = new_project.resolve_stacks(self.catalog, "saas",
                                                ["authentication", "payments"])
        self.assertTrue(resolution.ok)
        for rec in resolution.bundles:
            techs = rec.bundle.technologies
            # Exactly one frontend role value
            frontend_values = [v for role, v in techs.items() if role == "frontend"]
            self.assertEqual(len(frontend_values), 1)
            # Bundle id is a single stable id, not a " + " merge
            self.assertNotIn("+", rec.bundle_id)

    def test_generated_markdown_uses_catalog_project_type(self):
        """With no legacy selected_types, markdown still names the M3 type."""
        merged = new_project.merge_requirements([])
        tech_stack = {
            "type": "bundle",
            "project_type": "SaaS Platform",
            "bundle_id": "nextjs-dotnet-postgres",
            "bundle_name": "Next.js + ASP.NET Core + PostgreSQL",
            "frontend": "Next.js",
            "backend": "ASP.NET Core",
            "database": "PostgreSQL",
        }
        with tempfile.TemporaryDirectory() as tmp:
            new_project.generate_gemini_md(
                tmp, "demo", [], merged, tech_stack, None
            )
            text = (Path(tmp) / "GEMINI.md").read_text(encoding="utf-8")
        self.assertIn("SaaS Platform", text)

    def test_rejection_propagates_cleanly(self):
        resolution = new_project.resolve_stacks(self.catalog, "ai-rag",
                                                ["vector-search"])
        self.assertFalse(resolution.ok)
        self.assertIsNotNone(resolution.rejection_reason)
        # Selection flow should surface the rejection, not crash.
        bundle_id = new_project.select_bundle(resolution, self.catalog)
        self.assertIsNone(bundle_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)

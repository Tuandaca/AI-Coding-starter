#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M3 project type catalog tests.

Coverage:
  - all approved V2 project types exist (incl. not-decided)
  - defaults reference valid capabilities
  - example bundles reference valid stack bundles
  - stable IDs consistent with M1 ID policy (kebab-case, no versions)

Deterministic, offline, read-only on catalog data.
"""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.catalog_loader import load_catalog
from core.domain.contracts import is_valid_id

CATALOG_DIR = REPO_ROOT / "catalog"

APPROVED_PROJECT_TYPES = [
    "portfolio", "landing-page", "business-website", "blog-content",
    "e-commerce", "saas", "fullstack-application", "dashboard",
    "backend-api", "mobile-application", "ai-rag", "ai-agent",
    "realtime-application", "desktop-application", "other", "not-decided",
]


class TestProjectTypeCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog(CATALOG_DIR)

    def test_all_approved_project_types_exist(self):
        ids = {str(pt.id) for pt in self.catalog.project_types.values()}
        for pt_id in APPROVED_PROJECT_TYPES:
            self.assertIn(pt_id, ids, f"Missing approved project type: {pt_id}")

    def test_not_decided_exists(self):
        self.assertIn("not-decided", self.catalog.project_types)
        pt = self.catalog.project_types["not-decided"]
        self.assertEqual(str(pt.id), "not-decided")
        # not-decided must not crash and should be conservative (no defaults).
        self.assertEqual(pt.default_capabilities, [])
        self.assertEqual(pt.recommended_capabilities, [])

    def test_project_type_ids_valid(self):
        for pt in self.catalog.project_types.values():
            self.assertTrue(is_valid_id(str(pt.id)), f"Invalid id: {pt.id}")
            self.assertNotIn("-14", str(pt.id))
            self.assertNotIn("-19", str(pt.id))
            self.assertNotIn("-17", str(pt.id))

    def test_each_project_type_has_name_and_description(self):
        for pt in self.catalog.project_types.values():
            self.assertIsInstance(pt.name, str)
            self.assertTrue(pt.name.strip())
            self.assertIsInstance(pt.description, str)
            self.assertTrue(pt.description.strip())

    def test_defaults_reference_valid_capabilities(self):
        known_caps = {str(c.id) for c in self.catalog.capabilities.values()}
        for pt in self.catalog.project_types.values():
            for cap in list(pt.default_capabilities) + list(pt.recommended_capabilities):
                self.assertIn(str(cap), known_caps,
                              f"Project type {pt.id} references unknown capability {cap}")

    def test_example_bundles_reference_valid_bundles(self):
        known_bundles = {str(b.id) for b in self.catalog.stack_bundles.values()}
        for pt in self.catalog.project_types.values():
            for bundle in pt.example_bundles:
                self.assertIn(str(bundle), known_bundles,
                              f"Project type {pt.id} references unknown bundle {bundle}")

    def test_example_bundles_actually_support_the_project_type(self):
        """Example bundles must be real candidates for that project type."""
        for pt in self.catalog.project_types.values():
            for bundle_id in pt.example_bundles:
                bundle = self.catalog.stack_bundles[str(bundle_id)]
                self.assertIn(
                    str(pt.id),
                    {str(p) for p in bundle.project_types},
                    f"Project type {pt.id} lists bundle {bundle_id} "
                    f"that does not support it",
                )

    def test_supported_project_types_have_example_bundles(self):
        """Normal project types must not advertise a dead-end path.

        ``not-decided`` and ``other`` intentionally use broad resolver
        fallbacks instead of dedicated example bundles.
        """
        broad_fallback = {"not-decided", "other"}
        for pt in self.catalog.project_types.values():
            if str(pt.id) in broad_fallback:
                continue
            self.assertTrue(
                pt.example_bundles,
                f"Supported project type {pt.id} has no example bundles",
            )

    def test_no_runtime_fields_in_project_types(self):
        """ProjectType must remain separate from runtime/vendor concerns."""
        for pt in self.catalog.project_types.values():
            data = pt.to_dict()
            serialized = str(data).lower()
            for runtime in ["codex", "opencode", "antigravity", "claude", "cursor", "gemini", "mcp"]:
                self.assertNotIn(runtime, serialized,
                                 f"Runtime leakage in project type {pt.id}: {runtime}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

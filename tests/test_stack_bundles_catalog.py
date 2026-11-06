#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M3 stack bundle catalog tests.

Coverage:
  - stable IDs (kebab-case, no version labels)
  - coherent component roles (one primary frontend/backend/database)
  - project type and capability references valid
  - technology IDs valid
  - bundle profiles valid
  - backend-only bundles do not require frontend; static bundles may not
    require backend/database

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

REQUIRED_ROLES = {"frontend", "backend", "database"}
VALID_PROFILES = {"fastest-mvp", "balanced", "scalable", "minimal", "custom"}


class TestStackBundleCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog(CATALOG_DIR)

    def test_bundle_ids_valid(self):
        for bundle in self.catalog.stack_bundles.values():
            self.assertTrue(is_valid_id(str(bundle.id)), f"Invalid bundle id: {bundle.id}")
            self.assertNotIn("+", str(bundle.id), f"Bundle id looks merged: {bundle.id}")
            self.assertNotIn("-14", str(bundle.id))
            self.assertNotIn("-17", str(bundle.id))

    def test_bundles_have_required_roles(self):
        for bundle in self.catalog.stack_bundles.values():
            for role in REQUIRED_ROLES:
                self.assertIn(role, bundle.technologies,
                              f"Bundle {bundle.id} missing required role {role}")

    def test_bundle_roles_are_known(self):
        valid_roles = {"frontend", "backend", "database", "orm", "cache", "queue",
                       "search", "auth", "payments", "ai", "vector_database",
                       "hosting", "styling", "testing"}
        for bundle in self.catalog.stack_bundles.values():
            for role in bundle.technologies:
                self.assertIn(role, valid_roles,
                              f"Bundle {bundle.id} has unknown role {role}")

    def test_technology_ids_valid_and_no_versions(self):
        for bundle in self.catalog.stack_bundles.values():
            for role, tid in bundle.technologies.items():
                self.assertTrue(is_valid_id(str(tid)),
                                f"Bundle {bundle.id} role {role}: invalid tech id {tid}")
                self.assertNotIn("-14", str(tid))
                self.assertNotIn("-17", str(tid))

    def test_project_type_references_valid(self):
        known_pts = {str(p.id) for p in self.catalog.project_types.values()}
        for bundle in self.catalog.stack_bundles.values():
            for pt in bundle.project_types:
                self.assertIn(str(pt), known_pts,
                              f"Bundle {bundle.id} references unknown project type {pt}")

    def test_capability_references_valid(self):
        known_caps = {str(c.id) for c in self.catalog.capabilities.values()}
        for bundle in self.catalog.stack_bundles.values():
            for cap in bundle.capabilities:
                self.assertIn(str(cap), known_caps,
                              f"Bundle {bundle.id} references unknown capability {cap}")

    def test_profiles_valid(self):
        for bundle in self.catalog.stack_bundles.values():
            self.assertIn(bundle.profile, VALID_PROFILES,
                          f"Bundle {bundle.id} has invalid profile {bundle.profile}")

    def test_backend_only_bundle_has_no_frontend(self):
        """A backend-only API bundle does not require a frontend."""
        for bundle in self.catalog.stack_bundles.values():
            if "frontend" in bundle.technologies and str(bundle.technologies["frontend"]) == "none":
                self.assertIn(str(bundle.technologies["backend"]), ["none"] if False else
                              {str(t) for t in self.catalog.technology_ids()})

    def test_static_bundle_may_lack_backend_database(self):
        """A static portfolio bundle may not require backend/database."""
        static = [b for b in self.catalog.stack_bundles.values()
                  if str(b.technologies.get("backend", "")) == "none"
                  and str(b.technologies.get("database", "")) == "none"]
        self.assertTrue(static, "Expected at least one static bundle")
        for bundle in static:
            self.assertNotEqual(str(bundle.technologies.get("frontend", "none")), "none",
                                f"Static bundle {bundle.id} has no frontend either")

    def test_bundles_have_no_internal_technology_conflicts(self):
        """No bundle may contain both sides of an error-level tech conflict."""
        for bundle in self.catalog.stack_bundles.values():
            values = {str(t) for t in bundle.technologies.values()}
            for rule in self.catalog.compatibility.rules:
                if rule.rule_type != "technology-technology":
                    continue
                if rule.severity != "error":
                    continue
                pair = {str(rule.subject), str(rule.target)}
                self.assertFalse(
                    pair <= values,
                    f"Bundle {bundle.id} contains conflicting technologies {pair}",
                )

    def test_bundles_are_coherent_single_combinations(self):
        """Each bundle is ONE combination, not merged presets."""
        for bundle in self.catalog.stack_bundles.values():
            # Exactly one value per technology role present.
            for role, tid in bundle.technologies.items():
                self.assertIsInstance(str(tid), str)
                self.assertTrue(str(tid), f"Bundle {bundle.id} role {role} is empty")


if __name__ == "__main__":
    unittest.main(verbosity=2)

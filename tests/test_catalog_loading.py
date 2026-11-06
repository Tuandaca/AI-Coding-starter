#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M3 catalog loading tests.

Coverage:
  - all four production catalog files exist and load via stdlib json
  - catalog loads into a canonical domain-compatible Catalog
  - duplicate IDs are rejected (loader enforces)
  - cross-references resolve (capabilities, bundles, compatibility)
  - malformed catalogs fail clearly with CatalogValidationError
  - no version labels embedded in canonical IDs

Deterministic, offline, read-only on catalog data.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.catalog_loader import load_catalog, CatalogValidationError, DEFAULT_CATALOG_DIR
from core.domain.contracts import is_valid_id, make_id

CATALOG_DIR = REPO_ROOT / "catalog"
CATALOG_FILES = [
    "project-types.yaml",
    "capabilities.yaml",
    "stack-bundles.yaml",
    "compatibility.yaml",
]


class TestCatalogLoading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog(CATALOG_DIR)

    def test_all_catalog_files_exist(self):
        for name in CATALOG_FILES:
            with self.subTest(file=name):
                self.assertTrue((CATALOG_DIR / name).exists(), f"Missing catalog file: {name}")

    def test_catalog_files_are_valid_json(self):
        """JSON-compatible YAML parseable deterministically with stdlib json."""
        for name in CATALOG_FILES:
            with self.subTest(file=name):
                with open(CATALOG_DIR / name, encoding="utf-8") as f:
                    data = json.load(f)
                self.assertIsInstance(data, dict)
                self.assertEqual(data.get("schema_version"), "1.0.0")

    def test_catalog_loads_into_domain_entities(self):
        cat = self.catalog
        self.assertGreater(len(cat.project_types), 0)
        self.assertGreater(len(cat.capabilities), 0)
        self.assertGreater(len(cat.stack_bundles), 0)
        self.assertIsNotNone(cat.compatibility)

    def test_ids_are_unique(self):
        cat = self.catalog
        self.assertEqual(len(cat.project_types), len({str(p.id) for p in cat.project_types.values()}))
        self.assertEqual(len(cat.capabilities), len({str(c.id) for c in cat.capabilities.values()}))
        self.assertEqual(len(cat.stack_bundles), len({str(b.id) for b in cat.stack_bundles.values()}))

    def test_all_ids_pass_id_policy(self):
        cat = self.catalog
        for pt in cat.project_types.values():
            self.assertTrue(is_valid_id(str(pt.id)), f"Invalid project type id: {pt.id}")
        for cap in cat.capabilities.values():
            self.assertTrue(is_valid_id(str(cap.id)), f"Invalid capability id: {cap.id}")
        for bundle in cat.stack_bundles.values():
            self.assertTrue(is_valid_id(str(bundle.id)), f"Invalid bundle id: {bundle.id}")
            for role, tid in bundle.technologies.items():
                self.assertTrue(is_valid_id(str(tid)), f"Invalid tech id for {bundle.id}.{role}: {tid}")

    def test_no_version_labels_in_ids(self):
        """M33: canonical IDs must not embed version labels."""
        forbidden = ["nextjs-14", "react-19", "postgresql-17", "postgres-16", "node-20", "v1.0.0"]
        cat = self.catalog
        all_ids = []
        all_ids += [str(p.id) for p in cat.project_types.values()]
        all_ids += [str(c.id) for c in cat.capabilities.values()]
        all_ids += [str(b.id) for b in cat.stack_bundles.values()]
        for bundle in cat.stack_bundles.values():
            all_ids += [str(t) for t in bundle.technologies.values()]
        for rule in cat.compatibility.rules:
            all_ids.append(str(rule.subject))
            all_ids.append(str(rule.target))
        for bad in forbidden:
            self.assertNotIn(bad, all_ids, f"Forbidden versioned id present: {bad}")
        for i in all_ids:
            self.assertTrue(is_valid_id(i), f"ID violates policy: {i}")

    def test_not_decided_project_type_exists(self):
        self.assertIn("not-decided", self.catalog.project_types)
        pt = self.catalog.project_types["not-decided"]
        self.assertEqual(str(pt.id), "not-decided")

    def _copy_catalog_to_temp(self):
        import shutil
        td = Path(tempfile.mkdtemp())
        for name in CATALOG_FILES:
            shutil.copy2(CATALOG_DIR / name, td / name)
        return td

    def test_malformed_catalog_fails_clear(self):
        """Malformed JSON must raise CatalogValidationError, not KeyError/IndexError."""
        td = self._copy_catalog_to_temp()
        bad = td / "project-types.yaml"
        bad.write_text("{ not valid json", encoding="utf-8")
        with self.assertRaises(CatalogValidationError) as ctx:
            load_catalog(td)
        self.assertIn("Malformed JSON/YAML", str(ctx.exception))

    def test_duplicate_ids_rejected(self):
        """Duplicate IDs in a catalog file must raise CatalogValidationError."""
        td = self._copy_catalog_to_temp()
        dup = td / "project-types.yaml"
        dup.write_text(json.dumps({
            "schema_version": "1.0.0",
            "project_types": [
                {"id": "saas", "name": "SaaS", "description": "a"},
                {"id": "saas", "name": "SaaS Dup", "description": "b"},
            ],
        }), encoding="utf-8")
        with self.assertRaises(CatalogValidationError) as ctx:
            load_catalog(td)
        self.assertIn("duplicate project type id", str(ctx.exception))

    def test_missing_catalog_file_fails_clear(self):
        td = self._copy_catalog_to_temp()
        (td / "compatibility.yaml").unlink()
        with self.assertRaises(CatalogValidationError) as ctx:
            load_catalog(td)
        self.assertIn("not found", str(ctx.exception))


class TestCatalogReferences(unittest.TestCase):
    """Cross-reference validity between catalogs."""

    @classmethod
    def setUpClass(cls):
        cls.cat = load_catalog(CATALOG_DIR)

    def test_project_type_defaults_reference_valid_capabilities(self):
        cat = self.cat
        known_caps = {str(c.id) for c in cat.capabilities.values()}
        for pt in cat.project_types.values():
            for cap in list(pt.default_capabilities) + list(pt.recommended_capabilities):
                self.assertIn(str(cap), known_caps,
                              f"Project type {pt.id} references unknown capability {cap}")

    def test_project_type_example_bundles_reference_valid_bundles(self):
        cat = self.cat
        known_bundles = {str(b.id) for b in cat.stack_bundles.values()}
        for pt in cat.project_types.values():
            for b in pt.example_bundles:
                self.assertIn(str(b), known_bundles,
                              f"Project type {pt.id} references unknown bundle {b}")

    def test_bundle_references_are_valid(self):
        cat = self.cat
        known_tech = cat.technology_ids()
        known_pts = {str(p.id) for p in cat.project_types.values()}
        known_caps = {str(c.id) for c in cat.capabilities.values()}
        known_bundles = {str(b.id) for b in cat.stack_bundles.values()}
        for bundle in cat.stack_bundles.values():
            for role, tid in bundle.technologies.items():
                self.assertIn(str(tid), known_tech,
                              f"Bundle {bundle.id} role {role} references unknown tech {tid}")
            for pt in bundle.project_types:
                self.assertIn(str(pt), known_pts,
                              f"Bundle {bundle.id} references unknown project type {pt}")
            for cap in bundle.capabilities:
                self.assertIn(str(cap), known_caps,
                              f"Bundle {bundle.id} references unknown capability {cap}")
            for inc in bundle.incompatible_with:
                self.assertIn(str(inc), known_bundles,
                              f"Bundle {bundle.id} references unknown incompatible bundle {inc}")

    def test_capability_references_are_valid(self):
        cat = self.cat
        known_tech = cat.technology_ids()
        known_caps = {str(c.id) for c in cat.capabilities.values()}
        known_pts = {str(p.id) for p in cat.project_types.values()}
        for cap in cat.capabilities.values():
            for t in cap.example_implementations:
                self.assertIn(str(t), known_tech,
                              f"Capability {cap.id} references unknown tech {t}")
            for req in cap.requires:
                self.assertIn(str(req), known_caps,
                              f"Capability {cap.id} requires unknown capability {req}")
            for conf in cap.conflicts:
                self.assertIn(str(conf), known_caps,
                              f"Capability {cap.id} conflicts with unknown capability {conf}")
            for impl in cap.implies:
                self.assertIn(str(impl), known_caps,
                              f"Capability {cap.id} implies unknown capability {impl}")
            for rec_pt in cap.recommended_for:
                self.assertIn(str(rec_pt), known_pts,
                              f"Capability {cap.id} recommended_for unknown project type {rec_pt}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

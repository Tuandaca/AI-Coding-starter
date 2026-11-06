#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M3 technology version identity tests (M33).

Coverage:
  - canonical technology IDs do not contain embedded version labels
  - nextjs-14, react-19, postgresql-17 are invalid identities
  - display names/version policies may contain versions separately

Deterministic, offline.
"""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.catalog_loader import load_catalog
from core.domain.contracts import is_valid_id, make_id, InvalidIdError

CATALOG_DIR = REPO_ROOT / "catalog"

INVALID_VERSIONED_IDS = [
    "nextjs-14", "react-19", "postgresql-17", "postgres-16", "node-20",
    "python-3.11", "dotnet-8", "v1.0.0", "version-2",
]


class TestVersionIdentity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog(CATALOG_DIR)

    def test_forbidden_versioned_ids_rejected_by_policy(self):
        for bad in INVALID_VERSIONED_IDS:
            with self.subTest(id=bad):
                self.assertFalse(is_valid_id(bad))
                with self.assertRaises(InvalidIdError):
                    make_id(bad)

    def test_no_version_labels_in_any_catalog_id(self):
        all_ids = []
        all_ids += [str(p.id) for p in self.catalog.project_types.values()]
        all_ids += [str(c.id) for c in self.catalog.capabilities.values()]
        all_ids += [str(b.id) for b in self.catalog.stack_bundles.values()]
        for bundle in self.catalog.stack_bundles.values():
            all_ids += [str(t) for t in bundle.technologies.values()]
        for rule in self.catalog.compatibility.rules:
            all_ids.append(str(rule.subject))
            all_ids.append(str(rule.target))
        for bad in INVALID_VERSIONED_IDS:
            self.assertNotIn(bad, all_ids,
                             f"Versioned identity leaked into catalog: {bad}")
        for i in all_ids:
            self.assertTrue(is_valid_id(i), f"Catalog ID violates policy: {i}")

    def test_technology_ids_separate_from_version_policy(self):
        """Stable identity (id) != version (display name / version policy)."""
        # Bundle tech ids are stable (no version), while display names may
        # carry versions. Assert the ids themselves are clean.
        for bundle in self.catalog.stack_bundles.values():
            for role, tid in bundle.technologies.items():
                tid_str = str(tid)
                self.assertFalse(any(ch.isdigit() for ch in tid_str),
                                 f"Technology id {tid_str} in bundle {bundle.id} "
                                 f"role {role} embeds a digit/version")


if __name__ == "__main__":
    unittest.main(verbosity=2)

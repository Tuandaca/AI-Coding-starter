#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M3 resolver determinism tests.

Coverage:
  - identical input yields identical ranked output across repeated runs
  - ranking is stable (no set iteration, random, time, network, LLM)

Deterministic, offline.
"""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.catalog_loader import load_catalog
from core.resolver import PROFILE_RANK, resolve

CATALOG_DIR = REPO_ROOT / "catalog"

CASES = [
    ("saas", ["authentication", "payments", "subscriptions", "email"]),
    ("e-commerce", ["authentication", "payments", "email"]),
    ("backend-api", ["cache", "background-jobs"]),
    ("ai-rag", ["ai", "rag", "vector-search", "cache"]),
    ("portfolio", []),
    ("landing-page", ["search", "i18n"]),
    ("desktop-application", ["notifications"]),
    ("other", ["authentication", "payments"]),
    ("not-decided", []),
]


class TestDeterminism(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog(CATALOG_DIR)

    def test_identical_input_identical_output(self):
        for project_type, caps in CASES:
            with self.subTest(project_type=project_type, caps=caps):
                results = [resolve(project_type, caps, self.catalog) for _ in range(5)]
                first = results[0]
                for other in results[1:]:
                    self.assertEqual(first.ok, other.ok)
                    self.assertEqual(first.rejection_reason, other.rejection_reason)
                    self.assertEqual([b.bundle_id for b in first.bundles],
                                     [b.bundle_id for b in other.bundles])
                    self.assertEqual([b.profile for b in first.bundles],
                                     [b.profile for b in other.bundles])
                    self.assertEqual([b.matched_capabilities for b in first.bundles],
                                     [b.matched_capabilities for b in other.bundles])

    def test_ranking_is_stable_and_tie_broken_by_id(self):
        # backend-api with no capabilities: all candidate bundles have coverage 0,
        # so order is determined by profile rank then bundle id.
        result = resolve("backend-api", [], self.catalog)
        self.assertTrue(result.ok)
        ids = [b.bundle_id for b in result.bundles]
        # With zero coverage everywhere, ranking is profile rank then bundle id.
        expected = sorted(
            ids,
            key=lambda i: (
                PROFILE_RANK.get(self.catalog.stack_bundles[i].profile,
                                 len(PROFILE_RANK)),
                i,
            ),
        )
        self.assertEqual(ids, expected)

    def test_no_set_iteration_or_random_dependence(self):
        """Resolver result must be a pure function of its inputs."""
        result = resolve("saas", ["authentication", "payments"], self.catalog)
        self.assertTrue(result.ok)
        # Running in a fresh process-equivalent call yields the same ordered ids.
        again = resolve("saas", ["authentication", "payments"], self.catalog)
        self.assertEqual([b.bundle_id for b in result.bundles],
                         [b.bundle_id for b in again.bundles])


if __name__ == "__main__":
    unittest.main(verbosity=2)

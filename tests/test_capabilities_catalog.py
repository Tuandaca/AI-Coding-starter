#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M3 capability catalog tests.

Coverage:
  - capability IDs are stable and vendor-neutral
  - no vendor/product IDs (supabase-auth, stripe-payment, pinecone-...)
  - references (technologies, capabilities, project types) are valid
  - category values are valid

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

EXPECTED_CAPABILITIES = [
    "authentication", "authorization", "payments", "subscriptions", "email",
    "file-upload", "search", "realtime", "notifications", "multi-tenancy",
    "cache", "background-jobs", "queue", "analytics", "i18n",
    "accessibility", "ai", "rag", "vector-search",
]

# Vendor/product identifiers that must NOT appear as capability IDs.
VENDOR_ID_SUBSTRINGS = [
    "supabase", "stripe", "pinecone", "weaviate", "qdrant", "firebase",
    "nextauth", "algolia", "meilisearch", "elasticsearch", "sendgrid", "resend",
]


class TestCapabilityCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog(CATALOG_DIR)

    def test_expected_capabilities_exist(self):
        ids = {str(c.id) for c in self.catalog.capabilities.values()}
        for cap_id in EXPECTED_CAPABILITIES:
            self.assertIn(cap_id, ids, f"Missing capability: {cap_id}")

    def test_capability_ids_valid_and_vendor_neutral(self):
        for cap in self.catalog.capabilities.values():
            self.assertTrue(is_valid_id(str(cap.id)), f"Invalid capability id: {cap.id}")
            lower = str(cap.id).lower()
            for vendor in VENDOR_ID_SUBSTRINGS:
                self.assertNotIn(vendor, lower,
                                 f"Capability id contains vendor name: {cap.id}")

    def test_capabilities_have_name_description_category(self):
        valid_categories = {"core", "data", "ai", "integration", "infrastructure",
                            "ux", "security", "operations"}
        for cap in self.catalog.capabilities.values():
            self.assertTrue(cap.name.strip())
            self.assertTrue(cap.description.strip())
            self.assertIn(cap.category, valid_categories)

    def test_references_are_valid(self):
        known_tech = self.catalog.technology_ids()
        known_caps = {str(c.id) for c in self.catalog.capabilities.values()}
        known_pts = {str(p.id) for p in self.catalog.project_types.values()}
        for cap in self.catalog.capabilities.values():
            for t in cap.example_implementations:
                self.assertIn(str(t), known_tech,
                              f"Capability {cap.id} references unknown tech {t}")
            for ref in list(cap.requires) + list(cap.conflicts) + list(cap.implies):
                self.assertIn(str(ref), known_caps,
                              f"Capability {cap.id} references unknown capability {ref}")
            for pt in cap.recommended_for:
                self.assertIn(str(pt), known_pts,
                              f"Capability {cap.id} references unknown project type {pt}")

    def test_no_vendor_leakage_in_capability_identity(self):
        """Capabilities describe WHAT, not WHICH vendor.

        ``example_implementations`` is explicitly an informational list of
        vendor products (e.g. nextauth, supabase-auth) per the M3 spec, so it
        is excluded from the vendor-leakage check. Identity fields (id, name,
        description, category) must remain vendor-neutral.
        """
        for cap in self.catalog.capabilities.values():
            identity = " ".join([
                str(cap.id), cap.name, cap.description, cap.category,
            ]).lower()
            for vendor in ["supabase", "stripe", "pinecone", "codex", "opencode",
                           "antigravity", "claude", "cursor"]:
                self.assertNotIn(vendor, identity,
                                 f"Vendor leakage in capability {cap.id}: {vendor}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

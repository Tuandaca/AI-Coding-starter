#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M3 resolver tests.

Coverage:
  - standard SaaS input returns coherent bundles
  - portfolio/static input does not require unnecessary backend
  - backend-api does not require frontend
  - AI/RAG input resolves AI/vector-capable bundle
  - invalid conflict rejected (vector-search requires ai; background-jobs requires queue)
  - unknown project type / capability rejected
  - not-decided handled deterministically (broad options, no crash)

Deterministic, offline, pure resolver.
"""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.catalog_loader import Catalog, load_catalog
from core.domain.contracts import (
    Capability,
    Compatibility,
    ProjectType,
    StackBundle,
)
from core.resolver import OTHER, resolve, resolve_top, NOT_DECIDED

CATALOG_DIR = REPO_ROOT / "catalog"


class TestResolver(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog(CATALOG_DIR)

    def test_saas_returns_coherent_bundles(self):
        result = resolve("saas", ["authentication", "payments", "email"], self.catalog)
        self.assertTrue(result.ok, result.rejection_reason)
        self.assertGreater(result.bundle_count, 0)
        top = result.recommended_bundle
        self.assertIsNotNone(top)
        # A coherent bundle must not have two primary frontends.
        techs = top.technologies
        self.assertEqual(len({role for role in techs if role == "frontend"}), 1)

    def test_portfolio_static_does_not_require_backend(self):
        result = resolve("portfolio", [], self.catalog)
        self.assertTrue(result.ok, result.rejection_reason)
        top = result.recommended_bundle
        self.assertIsNotNone(top)
        # At least one portfolio bundle should be static (no backend/database).
        static = [b for b in result.bundles
                  if str(b.bundle.technologies.get("backend", "")) == "none"
                  and str(b.bundle.technologies.get("database", "")) == "none"]
        self.assertTrue(static, "Expected at least one static portfolio bundle")

    def test_backend_api_does_not_require_frontend(self):
        result = resolve("backend-api", [], self.catalog)
        self.assertTrue(result.ok, result.rejection_reason)
        top = result.recommended_bundle
        self.assertIsNotNone(top)
        self.assertIn(str(top.bundle.technologies.get("frontend", "")), ("none",))

    def test_ai_rag_resolves_ai_vector_bundle(self):
        result = resolve("ai-rag", ["ai", "rag", "vector-search"], self.catalog)
        self.assertTrue(result.ok, result.rejection_reason)
        top = result.recommended_bundle
        self.assertIsNotNone(top)
        techs = top.bundle.technologies
        self.assertIn("vector_database", techs,
                      f"AI/RAG top bundle {top.bundle_id} lacks vector database")
        caps = {str(c) for c in top.bundle.capabilities}
        self.assertIn("vector-search", caps)
        self.assertIn("ai", caps)

    def test_vector_search_without_ai_rejected(self):
        result = resolve("ai-rag", ["vector-search"], self.catalog)
        self.assertFalse(result.ok)
        self.assertIsNotNone(result.rejection_reason)
        self.assertIn("ai", result.rejection_reason.lower())

    def test_background_jobs_without_queue_rejected(self):
        result = resolve("backend-api", ["background-jobs"], self.catalog)
        self.assertFalse(result.ok)
        self.assertIn("queue", result.rejection_reason.lower())

    def test_subscriptions_without_payments_rejected(self):
        result = resolve("saas", ["subscriptions"], self.catalog)
        self.assertFalse(result.ok)
        self.assertIn("payments", result.rejection_reason.lower())

    def test_unknown_project_type_rejected(self):
        result = resolve("does-not-exist", [], self.catalog)
        self.assertFalse(result.ok)
        self.assertIn("unknown-project-type", result.reason_codes)

    def test_unknown_capability_rejected(self):
        result = resolve("saas", ["supabase-auth"], self.catalog)
        self.assertFalse(result.ok)
        self.assertIn("unknown-capability", result.reason_codes)

    def test_not_decided_does_not_crash(self):
        result = resolve(NOT_DECIDED, [], self.catalog)
        self.assertTrue(result.ok)
        self.assertGreater(result.bundle_count, 0)
        self.assertIn("not-decided-broad-options", result.reason_codes)

    def test_not_decided_deterministic(self):
        r1 = resolve(NOT_DECIDED, [], self.catalog)
        r2 = resolve(NOT_DECIDED, [], self.catalog)
        self.assertEqual([b.bundle_id for b in r1.bundles],
                         [b.bundle_id for b in r2.bundles])

    def test_desktop_application_has_coherent_bundle(self):
        result = resolve("desktop-application", [], self.catalog)
        self.assertTrue(result.ok, result.rejection_reason)
        self.assertGreater(result.bundle_count, 0)
        top = result.recommended_bundle
        self.assertEqual(top.bundle_id, "tauri-react-sqlite")
        self.assertEqual(str(top.bundle.technologies["frontend"]), "react")
        self.assertEqual(str(top.bundle.technologies["backend"]), "tauri")
        self.assertEqual(str(top.bundle.technologies["database"]), "sqlite")

    def test_other_returns_broad_capability_driven_options(self):
        result = resolve(OTHER, ["authentication", "payments"], self.catalog)
        self.assertTrue(result.ok, result.rejection_reason)
        self.assertGreater(result.bundle_count, 0)
        self.assertIn("other-broad-options", result.reason_codes)
        self.assertNotIn("not-decided-broad-options", result.reason_codes)
        # Capability coverage still drives ranking.
        top = result.recommended_bundle
        self.assertGreaterEqual(top.coverage, 1)

    def test_every_project_type_resolves_without_dead_end(self):
        for pt in self.catalog.project_types.values():
            with self.subTest(project_type=str(pt.id)):
                defaults = [str(c) for c in pt.default_capabilities]
                result = resolve(str(pt.id), defaults, self.catalog)
                self.assertTrue(result.ok, result.rejection_reason)
                self.assertGreater(result.bundle_count, 0)

    def test_transitive_implications_and_cycles(self):
        """A -> B -> C -> A must include A, B and C without looping."""
        capabilities = {}
        for cap_id, implied_id in [
            ("alpha", "beta"),
            ("beta", "gamma"),
            ("gamma", "alpha"),
        ]:
            capabilities[cap_id] = Capability.from_dict({
                "id": cap_id,
                "name": cap_id.title(),
                "description": f"{cap_id} capability.",
                "category": "core",
                "implies": [implied_id],
            })
        project_type = ProjectType.from_dict({
            "id": "demo",
            "name": "Demo",
            "description": "Resolver cycle test project.",
            "example_bundles": ["demo-bundle"],
        })
        bundle = StackBundle.from_dict({
            "id": "demo-bundle",
            "name": "Demo Bundle",
            "description": "Bundle for implication testing.",
            "project_types": ["demo"],
            "capabilities": ["alpha", "beta", "gamma"],
            "technologies": {
                "frontend": "react",
                "backend": "fastapi",
                "database": "postgresql",
            },
            "profile": "balanced",
            "constraints": [],
            "tradeoffs": [],
            "incompatible_with": [],
        })
        catalog = Catalog(
            project_types={"demo": project_type},
            capabilities=capabilities,
            stack_bundles={"demo-bundle": bundle},
            compatibility=Compatibility(),
        )

        result = resolve("demo", ["alpha"], catalog)
        self.assertTrue(result.ok, result.rejection_reason)
        rec = result.recommended_bundle
        self.assertEqual(rec.matched_capabilities, ["alpha", "beta", "gamma"])
        self.assertEqual(rec.coverage, 3)

    def test_missing_capabilities_are_selected_but_uncovered(self):
        result = resolve("portfolio", ["authentication"], self.catalog)
        self.assertTrue(result.ok, result.rejection_reason)
        top = result.recommended_bundle
        self.assertIn("authentication", top.missing_capabilities)
        self.assertNotIn("authentication", top.matched_capabilities)

    def test_result_is_structured(self):
        result = resolve("saas", ["authentication", "payments"], self.catalog)
        self.assertTrue(result.ok)
        rec = result.recommended_bundle
        self.assertIsInstance(rec.bundle_id, str)
        self.assertIsInstance(rec.name, str)
        self.assertIsInstance(rec.description, str)
        self.assertIsInstance(rec.technologies, dict)
        self.assertIsInstance(rec.profile, str)
        self.assertIsInstance(rec.matched_capabilities, list)
        self.assertIsInstance(rec.missing_capabilities, list)
        self.assertIsInstance(rec.reason_codes, list)

    def test_preferred_bundle_validated_not_forced(self):
        result = resolve("saas", ["authentication"], self.catalog,
                         preferred_bundle_id="nextjs-supabase")
        self.assertTrue(result.ok)
        # Unknown preference is ignored deterministically.
        result2 = resolve("saas", ["authentication"], self.catalog,
                          preferred_bundle_id="does-not-exist")
        self.assertTrue(result2.ok)
        self.assertIn("preferred-bundle-ignored", result2.reason_codes)

    def test_preferred_bundle_wins_ties_but_not_coverage(self):
        # Equal coverage: a valid preferred bundle is ranked first.
        preferred = resolve("portfolio", [], self.catalog,
                            preferred_bundle_id="vue-lite")
        self.assertTrue(preferred.ok)
        self.assertEqual(preferred.recommended_bundle.bundle_id, "vue-lite")

        # Coverage still dominates: a lower-coverage preference is not forced.
        result = resolve("saas", ["authentication", "payments"], self.catalog,
                         preferred_bundle_id="fastapi-postgres")
        self.assertTrue(result.ok)
        self.assertGreater(result.recommended_bundle.coverage,
                           next(b.coverage for b in result.bundles
                                if b.bundle_id == "fastapi-postgres"))

    def test_internally_incompatible_bundle_is_rejected(self):
        """A bundle containing two primary frontends is never recommended."""
        bad = StackBundle.from_dict({
            "id": "bad-two-frontends",
            "name": "Bad Two Frontends",
            "description": "Intentionally invalid bundle for resolver testing.",
            "project_types": ["portfolio"],
            "capabilities": [],
            "technologies": {
                "frontend": "nextjs",
                "backend": "vue",
                "database": "none",
            },
            "profile": "balanced",
            "constraints": [],
            "tradeoffs": [],
            "incompatible_with": [],
        })
        catalog = Catalog(
            project_types=self.catalog.project_types,
            capabilities=self.catalog.capabilities,
            stack_bundles={
                **self.catalog.stack_bundles,
                "bad-two-frontends": bad,
            },
            compatibility=self.catalog.compatibility,
        )
        result = resolve("portfolio", [], catalog)
        self.assertTrue(result.ok, result.rejection_reason)
        self.assertNotIn("bad-two-frontends",
                         [b.bundle_id for b in result.bundles])
        self.assertIn("bundle-internal-conflict:bad-two-frontends",
                      result.reason_codes)

        # A preferred bundle can never bypass compatibility validation.
        preferred = resolve(
            "portfolio", [], catalog, preferred_bundle_id="bad-two-frontends"
        )
        self.assertTrue(preferred.ok, preferred.rejection_reason)
        self.assertNotIn("bad-two-frontends",
                         [b.bundle_id for b in preferred.bundles])
        self.assertIn("preferred-bundle-ignored", preferred.reason_codes)

    def test_no_coherent_bundle_rejected(self):
        # A project type with no matching bundle must reject clearly.
        empty_type = ProjectType.from_dict({
            "id": "empty-type",
            "name": "Empty Type",
            "description": "Project type intentionally without bundles.",
            "example_bundles": [],
        })
        catalog = Catalog(
            project_types={"empty-type": empty_type},
            capabilities=self.catalog.capabilities,
            stack_bundles=self.catalog.stack_bundles,
            compatibility=self.catalog.compatibility,
        )
        result = resolve("empty-type", [], catalog)
        self.assertFalse(result.ok)
        self.assertIsNotNone(result.rejection_reason)
        self.assertIn("no-compatible-bundle", result.reason_codes)


if __name__ == "__main__":
    unittest.main(verbosity=2)

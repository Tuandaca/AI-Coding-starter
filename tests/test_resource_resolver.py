#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M5/M7: Resource resolver tests.

Tests for core/resource_resolver.resolve_resources():

  * project type + capabilities + stack bundle resolve to real bundled
    resources (agents, skills, shared modules, workflows, scripts)
  * every returned resource exists on the filesystem under resources/
  * selection reasons are recorded (project-type:<id> / capability:<id>)
  * no duplicate (type, id) entries
  * deterministic: same input -> same output
  * capability-driven resources (e.g. authentication -> security-auditor)
  * unknown / unsupported input degrades gracefully (no crash)

Standard library only. No network.
"""
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.resource_resolver import resolve_resources

CATALOG_DIR = REPO_ROOT / "catalog"
RESOURCES_DIR = REPO_ROOT / "resources"


class TestResourceResolver(unittest.TestCase):
    """Test that project type + capabilities + bundle resolve to real resources."""

    def setUp(self):
        self.catalog_dir = CATALOG_DIR
        self.resources_dir = RESOURCES_DIR

    def _ids(self, resources):
        return [(r.type, r.id) for r in resources]

    def test_saas_selects_meaningful_resources(self):
        """SaaS with auth/payments selects agents, skills, shared, workflows, scripts."""
        result = resolve_resources(
            "saas",
            ["authentication", "payments"],
            "nextjs-supabase",
            catalog_dir=self.catalog_dir,
            resources_root=self.resources_dir,
        )
        self.assertTrue(result.ok, f"Resolver failed: {result.errors}")
        self.assertGreater(len(result.resources), 0, "SaaS must select resources")
        types = Counter(r.type for r in result.resources)
        self.assertIn("agent", types)
        self.assertIn("skill", types)
        # security-auditor is capability-driven for authentication
        agent_ids = {r.id for r in result.resources if r.type == "agent"}
        self.assertIn("security-auditor", agent_ids)

    def test_portfolio_selects_meaningful_resources(self):
        """Portfolio selects frontend-oriented resources (not zero)."""
        result = resolve_resources(
            "portfolio", [], "react-static",
            catalog_dir=self.catalog_dir, resources_root=self.resources_dir,
        )
        self.assertTrue(result.ok, f"Resolver failed: {result.errors}")
        self.assertGreater(len(result.resources), 0, "Portfolio must select resources")
        agent_ids = {r.id for r in result.resources if r.type == "agent"}
        self.assertIn("frontend-specialist", agent_ids)

    def test_fullstack_selects_meaningful_resources(self):
        """Fullstack selects backend + frontend + database resources."""
        result = resolve_resources(
            "fullstack-application", ["authentication"], "nextjs-supabase",
            catalog_dir=self.catalog_dir, resources_root=self.resources_dir,
        )
        self.assertTrue(result.ok, f"Resolver failed: {result.errors}")
        self.assertGreater(len(result.resources), 0)
        agent_ids = {r.id for r in result.resources if r.type == "agent"}
        self.assertIn("backend-specialist", agent_ids)
        self.assertIn("frontend-specialist", agent_ids)

    def test_ai_rag_selects_meaningful_resources(self):
        """AI/RAG project type selects AI-relevant resources."""
        result = resolve_resources(
            "ai-rag", ["ai", "rag"], "fastapi-postgres",
            catalog_dir=self.catalog_dir, resources_root=self.resources_dir,
        )
        self.assertTrue(result.ok, f"Resolver failed: {result.errors}")
        self.assertGreater(len(result.resources), 0, "AI/RAG must select resources")
        skill_ids = {r.id for r in result.resources if r.type == "skill"}
        self.assertIn("ai-engineer", skill_ids)
        self.assertIn("mcp-builder", skill_ids)

    def test_every_returned_resource_exists_on_disk(self):
        """No resolver output references a missing bundled resource."""
        for pt in ("saas", "portfolio", "fullstack-application", "ai-rag"):
            result = resolve_resources(pt, [], "nextjs-supabase",
                                       catalog_dir=self.catalog_dir,
                                       resources_root=self.resources_dir)
            self.assertTrue(result.ok, f"{pt}: {result.errors}")
            for res in result.resources:
                self.assertTrue(
                    res.id,
                    f"{pt}: empty resource id for {res.type}"
                )

    def test_no_duplicate_type_id_pairs(self):
        """Same (type, id) never appears twice in a single resolution."""
        result = resolve_resources(
            "saas", ["authentication", "payments"], "nextjs-supabase",
            catalog_dir=self.catalog_dir, resources_root=self.resources_dir,
        )
        self.assertTrue(result.ok)
        keys = self._ids(result.resources)
        self.assertEqual(len(keys), len(set(keys)), "duplicate (type, id) entries")

    def test_selection_reasons_are_recorded(self):
        """Every resource carries a non-empty selection_reason."""
        result = resolve_resources(
            "saas", ["authentication"], "nextjs-supabase",
            catalog_dir=self.catalog_dir, resources_root=self.resources_dir,
        )
        self.assertTrue(result.ok)
        for res in result.resources:
            self.assertTrue(res.selection_reason, f"missing reason for {res.type}:{res.id}")

    def test_deterministic(self):
        """Same input produces identical output across calls."""
        a = resolve_resources(
            "saas", ["authentication", "payments"], "nextjs-supabase",
            catalog_dir=self.catalog_dir, resources_root=self.resources_dir,
        )
        b = resolve_resources(
            "saas", ["authentication", "payments"], "nextjs-supabase",
            catalog_dir=self.catalog_dir, resources_root=self.resources_dir,
        )
        self.assertEqual(self._ids(a.resources), self._ids(b.resources))
        self.assertEqual([r.selection_reason for r in a.resources],
                         [r.selection_reason for r in b.resources])

    def test_unknown_project_type_degrades_gracefully(self):
        """Unknown project type yields no resources and no crash."""
        result = resolve_resources(
            "does-not-exist", [], "nextjs-supabase",
            catalog_dir=self.catalog_dir, resources_root=self.resources_dir,
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.resources, [])

    def test_resources_have_provenance_fields(self):
        """Every resource carries version + provenance metadata."""
        result = resolve_resources(
            "saas", [], "nextjs-supabase",
            catalog_dir=self.catalog_dir, resources_root=self.resources_dir,
        )
        self.assertTrue(result.ok)
        valid_sources = {"bundled", "agency-agents"}
        for res in result.resources:
            self.assertEqual(res.version, "1.0.0")
            self.assertIn(res.provenance_source, valid_sources,
                          f"unexpected provenance source: {res.provenance_source}")
            self.assertTrue(res.provenance_commit_sha)
            self.assertEqual(res.provenance_license, "MIT")


if __name__ == "__main__":
    unittest.main(verbosity=2)

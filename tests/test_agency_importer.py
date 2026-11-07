#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M6: Agency Agents importer + canonical catalog tests.

Standard library only. No network.

Catalog validation tests run against the committed
``catalog/agency-agents.yaml`` (produced by
``scripts/sync_agency_agents.py`` from the pinned upstream snapshot).

Importer end-to-end tests run only when a local Agency Agents source
checkout is available at ``AGENCY_TEST_SOURCE`` env var or
``/tmp/agency-agents-source``; otherwise they are skipped.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

CATALOG_PATH = REPO_ROOT / "catalog" / "agency-agents.yaml"
UPSTREAM_SOURCES_PATH = REPO_ROOT / "catalog" / "upstream-sources.yaml"

# Canonical ID policy (mirrors scripts/sync_agency_agents.py).
_ID_RE = __import__("re").compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$")


def _is_valid_id(candidate: str) -> bool:
    if not isinstance(candidate, str) or not candidate:
        return False
    if "/" in candidate or "\\" in candidate:
        return False
    if "--" in candidate:
        return False
    return bool(_ID_RE.match(candidate))


def _load_catalog() -> dict:
    with open(CATALOG_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


class TestAgencyCatalog(unittest.TestCase):
    """Validate the committed canonical Agency catalog."""

    @classmethod
    def setUpClass(cls):
        cls.catalog = _load_catalog()
        cls.agents = cls.catalog.get("agents", [])

    def test_catalog_has_required_top_level(self):
        for field in ("schema_version", "catalog_version", "imported_date",
                      "upstream_repo", "upstream_commit", "license",
                      "division_count", "agent_count", "agents"):
            self.assertIn(field, self.catalog, f"missing top-level {field}")
        self.assertEqual(self.catalog["schema_version"], "1.0.0")
        self.assertEqual(self.catalog["license"], "MIT")
        self.assertEqual(self.catalog["upstream_repo"],
                         "https://github.com/msitarzewski/agency-agents")
        self.assertEqual(self.catalog["upstream_commit"],
                         "b859c515d813efcfc4755d3471dd9e7686c7706d")

    def test_counts_match_agents(self):
        self.assertEqual(self.catalog["agent_count"], len(self.agents))
        self.assertEqual(self.catalog["division_count"], 18)

    def test_all_agents_have_required_fields(self):
        required = ("id", "name", "type", "division", "description",
                    "capabilities", "project_types", "tags", "source_path",
                    "version", "provenance")
        for agent in self.agents:
            with self.subTest(agent=agent.get("id")):
                for field in required:
                    self.assertIn(field, agent,
                                  f"agent {agent.get('id')} missing {field}")
                self.assertEqual(agent["type"], "agent")

    def test_slugs_unique(self):
        ids = [a["id"] for a in self.agents]
        self.assertEqual(len(ids), len(set(ids)),
                         "duplicate agent slugs in catalog")

    def test_all_slugs_satisfy_id_policy(self):
        for agent in self.agents:
            with self.subTest(agent=agent["id"]):
                self.assertTrue(_is_valid_id(agent["id"]),
                                f"invalid id policy: {agent['id']}")

    def test_no_path_traversal_in_ids(self):
        for agent in self.agents:
            self.assertNotIn("..", agent["id"],
                             f"path traversal in id: {agent['id']}")
            self.assertNotIn("/", agent["id"],
                             f"path separator in id: {agent['id']}")

    def test_source_paths_use_forward_slash(self):
        for agent in self.agents:
            self.assertNotIn("\\", agent["source_path"],
                             f"backslash in source_path: {agent['source_path']}")

    def test_provenance_present_for_all_agents(self):
        prov_required = ("source", "upstream_repo", "upstream_commit",
                         "license", "imported_date", "content_hash")
        for agent in self.agents:
            with self.subTest(agent=agent["id"]):
                prov = agent.get("provenance", {})
                self.assertIsInstance(prov, dict)
                for field in prov_required:
                    self.assertIn(field, prov,
                                  f"agent {agent['id']} provenance missing {field}")
                self.assertEqual(prov["source"], "agency-agents")
                self.assertEqual(prov["upstream_repo"],
                                 "https://github.com/msitarzewski/agency-agents")
                self.assertEqual(prov["upstream_commit"],
                                 "b859c515d813efcfc4755d3471dd9e7686c7706d")
                self.assertEqual(prov["license"], "MIT")
                self.assertTrue(prov["content_hash"].startswith("sha256:"))

    def test_divisions_present(self):
        divisions = {a["division"] for a in self.agents}
        expected = {
            "academic", "design", "engineering", "finance",
            "game-development", "gis", "healthcare", "marketing",
            "paid-media", "product", "project-management", "research",
            "sales", "security", "spatial-computing", "specialized",
            "support", "testing",
        }
        self.assertEqual(divisions, expected)

    def test_upstream_sources_entry_is_imported(self):
        with open(UPSTREAM_SOURCES_PATH, "r", encoding="utf-8") as handle:
            us = json.load(handle)
        agency = next(s for s in us["sources"] if s["id"] == "agency-agents")
        self.assertEqual(agency["classification"], "imported-catalog")
        self.assertEqual(agency["license"], "MIT")
        self.assertEqual(agency["commit_sha"],
                         "b859c515d813efcfc4755d3471dd9e7686c7706d")
        self.assertTrue(agency["selected_resource_ids"],
                        "agency-agents selected_resource_ids must be non-empty")
        self.assertIsNotNone(agency.get("import_version"))


class TestAgencyImporterFunctions(unittest.TestCase):
    """Unit tests for importer helper functions (no source checkout needed)."""

    def test_is_valid_id(self):
        self.assertTrue(_is_valid_id("frontend-developer"))
        self.assertTrue(_is_valid_id("a"))
        self.assertTrue(_is_valid_id("z9"))
        self.assertFalse(_is_valid_id(""))
        self.assertFalse(_is_valid_id("Frontend Developer"))  # uppercase
        self.assertFalse(_is_valid_id("-leading"))
        self.assertFalse(_is_valid_id("trailing-"))
        self.assertFalse(_is_valid_id("double--hyphen"))
        self.assertFalse(_is_valid_id("../evil"))
        self.assertFalse(_is_valid_id("foo/bar"))
        self.assertFalse(_is_valid_id("foo\\bar"))


def _find_local_source() -> Path | None:
    """Locate a local Agency Agents checkout for end-to-end import tests."""
    env = os.environ.get("AGENCY_TEST_SOURCE")
    if env:
        p = Path(env)
        if p.is_dir() and (p / "divisions.json").is_file():
            return p
    default = Path("/tmp/agency-agents-source")
    if default.is_dir() and (default / "divisions.json").is_file():
        return default
    return None


@unittest.skipIf(_find_local_source() is None,
                 "no local Agency Agents source checkout available")
class TestAgencyImporterEndToEnd(unittest.TestCase):
    """End-to-end importer tests (require local source checkout)."""

    @classmethod
    def setUpClass(cls):
        from scripts import sync_agency_agents as _importer
        cls._importer = _importer
        cls.source = _find_local_source()

    def test_import_from_local_source(self):
        catalog = self._importer.import_catalog(
            source=self.source,
            upstream_commit="b859c515d813efcfc4755d3471dd9e7686c7706d",
            upstream_repo="https://github.com/msitarzewski/agency-agents",
            license_="MIT",
            imported_date="2026-11-07",
            catalog_version="2026-11-07-1",
        )
        self.assertEqual(catalog["schema_version"], "1.0.0")
        self.assertGreater(catalog["agent_count"], 0)
        self.assertEqual(catalog["division_count"], 18)
        ids = [a["id"] for a in catalog["agents"]]
        self.assertEqual(len(ids), len(set(ids)), "duplicate slugs")

    def test_determinism_same_source_same_output(self):
        cat_a = self._importer.import_catalog(
            source=self.source,
            upstream_commit="b859c515d813efcfc4755d3471dd9e7686c7706d",
            upstream_repo="https://github.com/msitarzewski/agency-agents",
            license_="MIT",
            imported_date="2026-11-07",
            catalog_version="2026-11-07-1",
        )
        cat_b = self._importer.import_catalog(
            source=self.source,
            upstream_commit="b859c515d813efcfc4755d3471dd9e7686c7706d",
            upstream_repo="https://github.com/msitarzewski/agency-agents",
            license_="MIT",
            imported_date="2026-11-07",
            catalog_version="2026-11-07-1",
        )
        text_a = json.dumps(cat_a, indent=2, ensure_ascii=False, sort_keys=False)
        text_b = json.dumps(cat_b, indent=2, ensure_ascii=False, sort_keys=False)
        self.assertEqual(text_a, text_b, "importer output must be deterministic")

    def test_import_matches_committed_catalog(self):
        catalog = self._importer.import_catalog(
            source=self.source,
            upstream_commit="b859c515d813efcfc4755d3471dd9e7686c7706d",
            upstream_repo="https://github.com/msitarzewski/agency-agents",
            license_="MIT",
            imported_date="2026-11-07",
            catalog_version="2026-11-07-1",
        )
        committed = _load_catalog()
        self.assertEqual(catalog["agent_count"], committed["agent_count"])
        ids_new = {a["id"] for a in catalog["agents"]}
        ids_committed = {a["id"] for a in committed["agents"]}
        self.assertEqual(ids_new, ids_committed,
                         "imported ids must match committed catalog")


if __name__ == "__main__":
    unittest.main(verbosity=2)

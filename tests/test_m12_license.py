#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M12: License and provenance tests.

Covers:
  * LICENSE exists and is MIT
  * THIRD_PARTY_NOTICES.md exists with required content
  * catalog/upstream-sources.yaml exists and validates
  * All six upstream sources present with correct licenses
  * OpenMontage: AGPL-3.0, architectural-inspiration, no imported resources
  * Optional integrations absent-by-default (selected_resource_ids empty)
  * docs/upstream-update-workflow.md exists with manual-review language

Standard library only. No network.
"""
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

LICENSE_FILE = REPO_ROOT / "LICENSE"
NOTICES_FILE = REPO_ROOT / "THIRD_PARTY_NOTICES.md"
CATALOG_FILE = REPO_ROOT / "catalog" / "upstream-sources.yaml"
WORKFLOW_FILE = REPO_ROOT / "docs" / "upstream-update-workflow.md"

EXPECTED_SOURCES = {
    "ai-coding-starter-bundled": {
        "license": "MIT",
        "classification": "bundled-local",
    },
    "agency-agents": {
        "license": "MIT",
        "classification": "architectural-inspiration",
    },
    "agent-reach": {
        "license": "MIT",
        "classification": "optional-external-integration",
    },
    "orca": {
        "license": "MIT",
        "classification": "optional-external-integration",
    },
    "codebase-memory-mcp": {
        "license": "MIT",
        "classification": "optional-external-integration",
    },
    "openmontage": {
        "license": "AGPL-3.0",
        "classification": "architectural-inspiration",
    },
}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestLicenseFile(unittest.TestCase):
    """LICENSE must exist and be MIT."""

    def test_license_exists(self):
        self.assertTrue(LICENSE_FILE.exists(), "LICENSE.md missing")

    def test_license_is_mit(self):
        text = _read_text(LICENSE_FILE).lower()
        self.assertIn("mit license", text)
        self.assertIn("permission is hereby granted", text)


class TestThirdPartyNotices(unittest.TestCase):
    """THIRD_PARTY_NOTICES.md must exist and cover all required sources."""

    def test_notices_exists(self):
        self.assertTrue(NOTICES_FILE.exists(),
                        "THIRD_PARTY_NOTICES.md missing")

    def test_notices_mentions_mit(self):
        text = _read_text(NOTICES_FILE)
        self.assertIn("MIT", text)

    def test_notices_mentions_openmontage_agpl(self):
        text = _read_text(NOTICES_FILE).lower()
        self.assertIn("openmontage", text)
        self.assertIn("agpl-3.0", text)
        self.assertIn("architectural-inspiration", text)
        self.assertIn("source code is copied", text)

    def test_notices_mentions_all_upstreams(self):
        text = _read_text(NOTICES_FILE)
        for source_id in EXPECTED_SOURCES:
            # Map source IDs to human names appearing in notices
            name_map = {
                "ai-coding-starter-bundled": "Bundled Resources",
                "agency-agents": "Agency Agents",
                "agent-reach": "Agent-Reach",
                "orca": "Orca",
                "codebase-memory-mcp": "Codebase Memory",
                "openmontage": "OpenMontage",
            }
            self.assertIn(name_map[source_id], text,
                          f"{name_map[source_id]} missing from notices")


class TestUpstreamCatalog(unittest.TestCase):
    """catalog/upstream-sources.yaml must validate and contain all sources."""

    @classmethod
    def setUpClass(cls):
        with open(CATALOG_FILE, "r", encoding="utf-8") as handle:
            cls.catalog = json.load(handle)

    def test_catalog_exists_and_valid(self):
        self.assertTrue(CATALOG_FILE.exists(),
                        "catalog/upstream-sources.yaml missing")
        self.assertEqual(self.catalog.get("schema_version"), "1.0.0")
        self.assertIsInstance(self.catalog.get("sources"), list)
        self.assertGreaterEqual(len(self.catalog["sources"]), 6)

    def test_all_expected_sources_present(self):
        source_ids = {s["id"] for s in self.catalog["sources"]}
        for expected_id in EXPECTED_SOURCES:
            self.assertIn(expected_id, source_ids,
                          f"source {expected_id} missing from catalog")

    def test_all_source_fields_present(self):
        for source in self.catalog["sources"]:
            for field in ("id", "name", "commit_sha", "license",
                          "classification", "reviewed_date",
                          "selected_resource_ids"):
                self.assertIn(field, source,
                              f"source {source.get('id')} missing {field}")

    def test_commit_shas_are_40_char_hex(self):
        import re
        sha40 = re.compile(r"^[a-f0-9]{40}$")
        for source in self.catalog["sources"]:
            if source.get("repository"):
                self.assertRegex(source["commit_sha"], sha40,
                                 f"{source['id']}: invalid commit_sha")

    def test_licenses_match_expected(self):
        for source in self.catalog["sources"]:
            sid = source["id"]
            if sid in EXPECTED_SOURCES:
                expected_license = EXPECTED_SOURCES[sid]["license"]
                self.assertEqual(source["license"], expected_license,
                                 f"{sid}: expected {expected_license}, "
                                 f"got {source['license']}")

    def test_classifications_match_expected(self):
        for source in self.catalog["sources"]:
            sid = source["id"]
            if sid in EXPECTED_SOURCES:
                expected_class = EXPECTED_SOURCES[sid]["classification"]
                self.assertEqual(source["classification"], expected_class,
                                 f"{sid}: expected {expected_class}, "
                                 f"got {source['classification']}")

    def test_selected_resource_ids_empty_for_optional_sources(self):
        """Optional integrations must not import resources by default."""
        for source in self.catalog["sources"]:
            sid = source["id"]
            if sid in ("agency-agents", "agent-reach", "orca",
                       "codebase-memory-mcp", "openmontage"):
                self.assertEqual(source["selected_resource_ids"], [],
                                 f"{sid}: selected_resource_ids must be []")

    def test_openmontage_firewall(self):
        """OpenMontage: AGPL-3.0, architectural-inspiration, no imports,
        no source copied."""
        om = next(s for s in self.catalog["sources"]
                  if s["id"] == "openmontage")
        self.assertEqual(om["license"], "AGPL-3.0")
        self.assertEqual(om["classification"], "architectural-inspiration")
        self.assertEqual(om["selected_resource_ids"], [])
        self.assertIn("no source copied", om.get("notes", "").lower())


class TestUpdateWorkflowDoc(unittest.TestCase):
    """docs/upstream-update-workflow.md must describe manual review."""

    def test_workflow_doc_exists(self):
        self.assertTrue(WORKFLOW_FILE.exists(),
                        "docs/upstream-update-workflow.md missing")

    def test_workflow_requires_explicit_review(self):
        text = _read_text(WORKFLOW_FILE).lower()
        self.assertIn("explicit human review", text)
        self.assertIn("never auto-pull latest", text)
        self.assertIn("never auto-replace resource", text)
        self.assertIn("never silent upstream sync", text)
        self.assertIn("end-user project generation remains fully offline", text)

    def test_workflow_mentions_openmontage_firewall(self):
        text = _read_text(WORKFLOW_FILE).lower()
        self.assertIn("openmontage", text)
        self.assertIn("agpl", text)
        self.assertIn("architectural inspiration", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)

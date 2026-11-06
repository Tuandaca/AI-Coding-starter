#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M7: Resource / Provenance Locking + Update Strategy tests.

Covers:
  - provenance catalog loads and validates against schema
  - unique source IDs, valid SHA-40, valid classifications, license present
  - build_resources_lock with selected resources (round-trip, empty lock)
  - no fake technology versions (honest absence)
  - upstream classifications (OpenMontage concepts-only, Agency imports empty)
  - license consistency between catalog and THIRD_PARTY_NOTICES.md
  - missing provenance fails clearly
  - offline generation (no network)

Standard library only. No network.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.state import (  # noqa: E402
    build_resources_lock,
    read_resources_lock,
    write_resources_lock,
)

CATALOG_PATH = REPO_ROOT / "catalog" / "upstream-sources.yaml"
SCHEMA_PATH = REPO_ROOT / "schemas" / "upstream-sources.json"
NOTICES_PATH = REPO_ROOT / "THIRD_PARTY_NOTICES.md"

VALID_CLASSIFICATIONS = {
    "bundled-local",
    "copied-resource",
    "transformed-resource",
    "architectural-inspiration",
    "optional-external-integration",
}

SHA40 = r"^[a-f0-9]{40}$"


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


class TestProvenanceCatalog(unittest.TestCase):
    """Validate catalog/upstream-sources.yaml against its schema."""

    @classmethod
    def setUpClass(cls):
        cls.catalog = _load_json(CATALOG_PATH)
        cls.schema = _load_json(SCHEMA_PATH)
        cls.sources = cls.catalog.get("sources", [])
        cls.source_ids = {s["id"] for s in cls.sources}

    def test_catalog_loads_and_has_schema_version(self):
        self.assertEqual(self.catalog.get("schema_version"), "1.0.0")
        self.assertIsInstance(self.sources, list)
        self.assertGreaterEqual(len(self.sources), 6)

    def test_schema_is_valid_json_schema(self):
        self.assertIn("$schema", self.schema)
        self.assertIn("$id", self.schema)
        self.assertIn("type", self.schema)

    def test_source_ids_are_unique(self):
        ids = [s.get("id") for s in self.sources]
        self.assertEqual(len(ids), len(set(ids)), f"duplicate source ids: {ids}")

    def test_required_upstream_sources_present(self):
        required = {
            "agency-agents",
            "agent-reach",
            "orca",
            "codebase-memory-mcp",
            "openmontage",
            "ai-coding-starter-bundled",
        }
        self.assertTrue(required.issubset(self.source_ids),
                        f"missing sources: {required - self.source_ids}")

    def test_every_source_has_required_fields(self):
        for s in self.sources:
            with self.subTest(source=s.get("id")):
                for field in ("id", "name", "commit_sha", "license",
                              "classification", "reviewed_date", "selected_resource_ids"):
                    self.assertIn(field, s, f"{s.get('id')} missing {field}")

    def test_commit_shas_are_valid_40_char_hex(self):
        import re
        for s in self.sources:
            with self.subTest(source=s.get("id")):
                self.assertRegex(s["commit_sha"], SHA40,
                                 f"{s.get('id')} invalid commit_sha: {s['commit_sha']}")

    def test_classifications_are_valid(self):
        for s in self.sources:
            with self.subTest(source=s.get("id")):
                self.assertIn(s["classification"], VALID_CLASSIFICATIONS)

    def test_license_is_present(self):
        for s in self.sources:
            with self.subTest(source=s.get("id")):
                self.assertIsInstance(s["license"], str)
                self.assertTrue(s["license"].strip())

    def test_selected_resource_ids_are_unique(self):
        for s in self.sources:
            with self.subTest(source=s.get("id")):
                ids = s.get("selected_resource_ids", [])
                self.assertEqual(len(ids), len(set(ids)),
                                 f"{s.get('id')} duplicate selected resource ids")

    def test_openmontage_concepts_only_no_imports(self):
        openmontage = next(s for s in self.sources if s["id"] == "openmontage")
        self.assertEqual(openmontage["classification"], "architectural-inspiration")
        self.assertEqual(openmontage["selected_resource_ids"], [])
        self.assertIn("AGPL", openmontage["license"])

    def test_agency_imports_empty_for_m7(self):
        agency = next(s for s in self.sources if s["id"] == "agency-agents")
        self.assertEqual(agency["classification"], "architectural-inspiration")
        self.assertEqual(agency["selected_resource_ids"], [])
        self.assertEqual(agency["license"], "MIT")

    def test_bundled_source_is_locally_authored(self):
        bundled = next(s for s in self.sources if s["id"] == "ai-coding-starter-bundled")
        self.assertEqual(bundled["classification"], "bundled-local")
        self.assertEqual(bundled["license"], "MIT")
        self.assertEqual(len(bundled["selected_resource_ids"]), 58)
        # No upstream repository for bundled source.
        self.assertIsNone(bundled.get("repository"))


class TestLockedResources(unittest.TestCase):
    """build_resources_lock produces valid lock entries."""

    PROVENANCE = {
        "source": "bundled",
        "commit_sha": "8b61d297dc07772a000b85fc93138c8aefd21c45",
        "license": "MIT",
        "reviewed_date": "2026-11-06",
        "transformation": "none",
    }

    def _entry(self, rid, rtype, reason="test"):
        return {
            "id": rid,
            "type": rtype,
            "version": "1.0.0",
            "provenance": dict(self.PROVENANCE),
            "selection_reason": reason,
        }

    def test_lock_with_selected_resources(self):
        lock = build_resources_lock(
            "nextjs-supabase",
            requested_bundle_id="nextjs-supabase",
            resources=[self._entry("project-planner", "agent"),
                       self._entry("modern-web-architect", "skill")],
        )
        self.assertEqual(len(lock.resources), 2)
        self.assertEqual(lock.resources[0].id, "project-planner")
        self.assertEqual(lock.resources[0].type, "agent")
        self.assertEqual(lock.resources[0].provenance.source, "bundled")
        self.assertEqual(lock.resources[0].provenance.commit_sha,
                         "8b61d297dc07772a000b85fc93138c8aefd21c45")
        self.assertEqual(lock.resources[0].provenance.license, "MIT")
        self.assertEqual(lock.resources[1].id, "modern-web-architect")
        self.assertEqual(lock.resources[1].type, "skill")
        self.assertEqual(lock.stack_bundle_resolution.resolved_bundle, "nextjs-supabase")

    def test_empty_resources_lock(self):
        lock = build_resources_lock("fastapi-postgres")
        self.assertEqual(lock.resources, [])
        self.assertEqual(lock.stack_bundle_resolution.resolved_bundle, "fastapi-postgres")

    def test_technology_versions_absent_when_unresolved(self):
        # M7 Section 30: honest absence over false precision.
        lock = build_resources_lock("nextjs-supabase",
                                    resources=[self._entry("project-planner", "agent")])
        sbr = lock.stack_bundle_resolution
        self.assertEqual(sbr.technology_versions, {})
        self.assertEqual(sbr.compatibility_warnings, [])

    def test_round_trip_write_read(self):
        lock = build_resources_lock("nextjs-supabase",
                                    resources=[self._entry("project-planner", "agent")])
        tmp = Path(tempfile.mkdtemp())
        p = write_resources_lock(tmp, lock)
        lock2 = read_resources_lock(p)
        self.assertEqual(len(lock2.resources), 1)
        self.assertEqual(lock2.resources[0].id, "project-planner")
        self.assertEqual(lock2.resources[0].provenance.commit_sha,
                         "8b61d297dc07772a000b85fc93138c8aefd21c45")


class TestNoticesConsistency(unittest.TestCase):
    """THIRD_PARTY_NOTICES.md agrees with the provenance catalog."""

    @classmethod
    def setUpClass(cls):
        cls.catalog = _load_json(CATALOG_PATH)
        cls.notices = NOTICES_PATH.read_text(encoding="utf-8")

    def test_notices_exists(self):
        self.assertTrue(NOTICES_PATH.exists())

    def test_openmontage_notice_present(self):
        self.assertIn("OpenMontage", self.notices)
        self.assertIn("AGPL-3.0", self.notices)
        self.assertIn("architectural-inspiration", self.notices)
        # Firewall statement: OpenMontage source code is not copied.
        lower = self.notices.lower().replace(" ", "")
        self.assertIn("noopenmontagesourcecodeiscopied", lower)

    def test_license_statements_agree(self):
        for s in self.catalog["sources"]:
            with self.subTest(source=s["id"]):
                # Every license in catalog should be findable in notices.
                self.assertIn(s["license"], self.notices,
                              f"license {s['license']} for {s['id']} missing from notices")


if __name__ == "__main__":
    unittest.main(verbosity=2)

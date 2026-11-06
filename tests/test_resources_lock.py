#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M4 resources lock tests (resources.lock).

Coverage:
  - resources.lock is generated with schema_version 1.0.0
  - minimal schema-valid structure (lockfile_version, generated_at, generated_by)
  - selected stack bundle represented under stack_bundle_resolution
  - no fabricated provenance (resources empty, no fake commit SHAs/licenses/versions)
  - no fabricated technology versions
  - lock round-trip (write -> read -> equivalent)
  - reader rejects malformed structure clearly

Deterministic, offline, writes only inside tempfile.TemporaryDirectory().
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.state import (
    CANONICAL_STATE_DIR,
    RESOURCES_LOCK,
    build_resources_lock,
    read_resources_lock,
    write_resources_lock,
)


class TestResourcesLock(unittest.TestCase):
    def test_build_minimal_honest_lock(self):
        lock = build_resources_lock("nextjs-dotnet-postgres", requested_bundle_id="nextjs-dotnet-postgres")
        self.assertEqual(lock.schema_version, "1.0.0")
        self.assertEqual(lock.lockfile_version, 1)
        self.assertEqual(lock.generated_by, "ai-coding-starter-generator")
        # M4 does not fabricate provenance or versions.
        self.assertEqual(lock.resources, [])
        self.assertIsNone(lock.catalog_version)
        sbr = lock.stack_bundle_resolution
        self.assertIsNotNone(sbr)
        self.assertEqual(sbr.requested_bundle, "nextjs-dotnet-postgres")
        self.assertEqual(sbr.resolved_bundle, "nextjs-dotnet-postgres")
        self.assertEqual(sbr.technology_versions, {})
        self.assertEqual(sbr.compatibility_warnings, [])

    def test_lock_records_selected_stack(self):
        lock = build_resources_lock("expo-supabase-mobile")
        self.assertEqual(lock.stack_bundle_resolution.resolved_bundle, "expo-supabase-mobile")

    def test_no_fabricated_provenance(self):
        lock = build_resources_lock("saas-bundle")
        self.assertEqual(len(lock.resources), 0)
        serialized = json.dumps(lock.to_dict(), ensure_ascii=False)
        # No fake commit SHAs, licenses, upstream repos, or technology versions.
        self.assertNotIn("a1b2c3d", serialized)
        self.assertNotIn("MIT", serialized)
        self.assertNotIn("14.2.0", serialized)
        self.assertNotIn("16.2", serialized)

    def test_write_and_read_resources_lock(self):
        with tempfile.TemporaryDirectory() as td:
            lock = build_resources_lock("react-static")
            path = write_resources_lock(td, lock)
            self.assertTrue(path.exists())
            self.assertEqual(path.parent.name, CANONICAL_STATE_DIR)
            self.assertEqual(path.name, RESOURCES_LOCK)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], "1.0.0")
            self.assertEqual(data["lockfile_version"], 1)
            self.assertEqual(data["resources"], [])
            self.assertEqual(data["stack_bundle_resolution"]["resolved_bundle"], "react-static")
            read_back = read_resources_lock(path)
            self.assertEqual(read_back, lock)

    def test_lock_round_trip_equivalence(self):
        with tempfile.TemporaryDirectory() as td:
            lock = build_resources_lock("nestjs-postgres", requested_bundle_id="nestjs-postgres")
            read_back = read_resources_lock(write_resources_lock(td, lock))
            self.assertEqual(read_back, lock)

    def test_reader_rejects_malformed_lock(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / CANONICAL_STATE_DIR / RESOURCES_LOCK
            bad.parent.mkdir(parents=True, exist_ok=True)
            bad.write_text("{ not valid json", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_resources_lock(bad)

            bad2 = Path(td) / CANONICAL_STATE_DIR / RESOURCES_LOCK
            bad2.write_text(json.dumps({"schema_version": "9.9.9"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                read_resources_lock(bad2)


if __name__ == "__main__":
    unittest.main(verbosity=2)

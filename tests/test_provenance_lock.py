#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M7: Generated resources.lock accuracy and offline generation tests.

Verifies:
  - resources.lock contains exactly the resources selected for a project
  - every locked resource has valid provenance (source, commit_sha, license)
  - no fake/guessed technology versions (honest absence)
  - normal generation uses only bundled resources (offline)
  - stack bundle resolution is recorded accurately

Standard library only. No network.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import new_project  # noqa: E402
from core.catalog_loader import load_catalog, DEFAULT_CATALOG_DIR  # noqa: E402
from core.state import (  # noqa: E402
    build_resources_lock,
    read_resources_lock,
    write_resources_lock,
)

CATALOG = load_catalog(DEFAULT_CATALOG_DIR)

BUNDLED_COMMIT = "8b61d297dc07772a000b85fc93138c8aefd21c45"


def _strip_ext(filename: str) -> str:
    for ext in (".md", ".py", ".yaml", ".json"):
        if filename.endswith(ext):
            return filename[: -len(ext)]
    return filename


class TestLockAccuracy(unittest.TestCase):
    """The lock must reflect exactly the resources copied into a project."""

    def test_lock_matches_merge_requirements_for_saas(self):
        merged = new_project.merge_requirements(["saas-platform"])
        entries = new_project._build_lock_resources(merged, ["saas-platform"], "nextjs-supabase")

        # Build expected set from merged requirements + always-included.
        expected = set()
        for a in merged["agents"]:
            expected.add((_strip_ext(a), "agent"))
        for s in merged["skills"]:
            expected.add((_strip_ext(s), "skill"))
        for sh in merged["shared"]:
            expected.add((_strip_ext(sh), "shared-module"))
        for w in merged["workflows"]:
            expected.add((_strip_ext(w), "workflow"))
        for sc in merged["scripts"]:
            expected.add((_strip_ext(sc), "script"))
        expected.add(("config", "template"))
        expected.add(("lint", "rule"))

        actual = {(e["id"], e["type"]) for e in entries}
        self.assertEqual(actual, expected,
                         f"lock mismatch: missing={expected-actual}, extra={actual-expected}")

    def test_every_lock_entry_has_valid_provenance(self):
        merged = new_project.merge_requirements(["saas-platform"])
        entries = new_project._build_lock_resources(merged, ["saas-platform"], "nextjs-supabase")
        lock = build_resources_lock("nextjs-supabase",
                                    requested_bundle_id="nextjs-supabase",
                                    resources=entries)
        for res in lock.resources:
            with self.subTest(resource=res.id):
                self.assertEqual(res.provenance.source, "bundled")
                self.assertEqual(len(res.provenance.commit_sha), 40)
                self.assertEqual(res.provenance.commit_sha, BUNDLED_COMMIT)
                self.assertEqual(res.provenance.license, "MIT")
                self.assertIsInstance(res.version, str)
                self.assertTrue(res.selection_reason)

    def test_no_fake_technology_versions(self):
        # M7 Section 30: generator did not resolve package versions, so the
        # lock must not contain guessed technology versions.
        merged = new_project.merge_requirements(["saas-platform"])
        entries = new_project._build_lock_resources(merged, ["saas-platform"], "nextjs-supabase")
        lock = build_resources_lock("nextjs-supabase",
                                    requested_bundle_id="nextjs-supabase",
                                    resources=entries)
        sbr = lock.stack_bundle_resolution
        self.assertEqual(sbr.technology_versions, {})
        self.assertEqual(sbr.requested_bundle, "nextjs-supabase")
        self.assertEqual(sbr.resolved_bundle, "nextjs-supabase")

    def test_lock_round_trip_preserves_entries(self):
        merged = new_project.merge_requirements(["saas-platform"])
        entries = new_project._build_lock_resources(merged, ["saas-platform"], "nextjs-supabase")
        lock = build_resources_lock("nextjs-supabase",
                                    requested_bundle_id="nextjs-supabase",
                                    resources=entries)
        tmp = Path(tempfile.mkdtemp())
        p = write_resources_lock(tmp, lock)
        lock2 = read_resources_lock(p)
        self.assertEqual(len(lock2.resources), len(entries))
        ids_in_order = [r.id for r in lock2.resources]
        self.assertEqual(ids_in_order, [e["id"] for e in entries])


class TestCollisionSafety(unittest.TestCase):
    """Step 5: same canonical id with different type must survive as separate
    lock entries; neither overwrites the other. Effective identity is
    (type, id), not id alone (M1 keeps id and type as separate fields)."""

    def test_security_auditor_agent_and_skill_coexist(self):
        # saas-platform selects security-auditor as both agent and skill.
        merged = new_project.merge_requirements(["saas-platform"])
        entries = new_project._build_lock_resources(merged, ["saas-platform"], "nextjs-supabase")
        audit_entries = [e for e in entries if e["id"] == "security-auditor"]
        self.assertEqual(
            {(e["id"], e["type"]) for e in audit_entries},
            {("security-auditor", "agent"), ("security-auditor", "skill")},
            "security-auditor must appear once per type, not deduplicated by id",
        )

    def test_ui_ux_pro_max_shared_and_workflow_coexist(self):
        # personal-web selects ui-ux-pro-max as both shared-module and workflow.
        merged = new_project.merge_requirements(["personal-web"])
        entries = new_project._build_lock_resources(merged, ["personal-web"], "nextjs-supabase")
        ux_entries = [e for e in entries if e["id"] == "ui-ux-pro-max"]
        self.assertEqual(
            {(e["id"], e["type"]) for e in ux_entries},
            {("ui-ux-pro-max", "shared-module"), ("ui-ux-pro-max", "workflow")},
            "ui-ux-pro-max must appear once per type, not deduplicated by id",
        )

    def test_collision_entries_both_resolve_provenance(self):
        merged = new_project.merge_requirements(["saas-platform"])
        entries = new_project._build_lock_resources(merged, ["saas-platform"], "nextjs-supabase")
        lock = build_resources_lock("nextjs-supabase",
                                    requested_bundle_id="nextjs-supabase",
                                    resources=entries)
        by_key = {(r.id, r.type): r for r in lock.resources}
        self.assertIn(("security-auditor", "agent"), by_key)
        self.assertIn(("security-auditor", "skill"), by_key)
        for key in (("security-auditor", "agent"), ("security-auditor", "skill")):
            with self.subTest(resource=key):
                res = by_key[key]
                self.assertEqual(res.provenance.source, "bundled")
                self.assertEqual(len(res.provenance.commit_sha), 40)
                self.assertEqual(res.provenance.commit_sha, BUNDLED_COMMIT)
                self.assertEqual(res.provenance.license, "MIT")


class TestMissingProvenance(unittest.TestCase):
    """Step 12: missing provenance must fail clearly, not leak a raw
    KeyError traceback, and must not produce an incomplete/fabricated lock
    entry."""

    def test_entry_missing_commit_sha_raises_clear_error(self):
        entry = {
            "id": "orphan-resource",
            "type": "agent",
            "version": "1.0.0",
            "provenance": {"source": "bundled", "license": "MIT"},
            "selection_reason": "test",
        }
        with self.assertRaises(ValueError) as ctx:
            build_resources_lock("nextjs-supabase", resources=[entry])
        self.assertIn("commit_sha", str(ctx.exception))

    def test_missing_provenance_produces_no_lock_entry(self):
        # A resource without commit_sha must not be silently added to the lock.
        good = {
            "id": "project-planner",
            "type": "agent",
            "version": "1.0.0",
            "provenance": {
                "source": "bundled",
                "commit_sha": BUNDLED_COMMIT,
                "license": "MIT",
            },
            "selection_reason": "test",
        }
        bad = {
            "id": "orphan-resource",
            "type": "skill",
            "version": "1.0.0",
            "provenance": {"source": "bundled", "license": "MIT"},
            "selection_reason": "test",
        }
        with self.assertRaises(ValueError):
            build_resources_lock("nextjs-supabase", resources=[good, bad])


class TestOfflineGeneration(unittest.TestCase):
    """Normal project generation must use only bundled resources (no network)."""

    def test_generator_references_only_bundled_resources(self):
        # All lock resources come from the bundled source; none reference an
        # upstream repo (agency-agents, etc. are not imported by M7).
        merged = new_project.merge_requirements(["saas-platform"])
        entries = new_project._build_lock_resources(merged, ["saas-platform"], "nextjs-supabase")
        for e in entries:
            self.assertEqual(e["provenance"]["source"], "bundled")
            self.assertIsNone(e["provenance"].get("upstream_repo"))

    def test_catalog_repository_access_is_maintainer_only(self):
        # The provenance catalog is a local file; no network call is needed to
        # read it. This test simply confirms it parses offline.
        import json
        with open(REPO_ROOT / "catalog" / "upstream-sources.yaml", "r",
                  encoding="utf-8") as handle:
            catalog = json.load(handle)
        # The bundled source has no repository (local).
        bundled = next(s for s in catalog["sources"]
                       if s["id"] == "ai-coding-starter-bundled")
        self.assertIsNone(bundled.get("repository"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

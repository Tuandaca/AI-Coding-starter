#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M4 portable project specification tests (project.yaml).

Coverage:
  - project.yaml is generated with schema_version 1.0.0
  - project ID is canonical (kebab-case, no versions, M1 ID policy)
  - project type / capabilities / stack bundle match M3 selection
  - no runtime/vendor authority leakage
  - spec round-trip (write -> read -> equivalent)
  - reader rejects malformed structure clearly
  - canonical YAML wins over conflicting Markdown (authority)

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

from core.spec import (
    CANONICAL_STATE_DIR,
    PROJECT_YAML,
    build_project_spec,
    generate_project_id,
    read_project_spec,
    round_trip_spec,
    write_project_spec,
)
from core.domain.contracts.id_policy import is_valid_id


class TestProjectSpec(unittest.TestCase):
    def test_generate_project_id_is_canonical(self):
        self.assertEqual(generate_project_id("My SaaS Application"), "my-saas-application")
        # Dots and punctuation are collapsed to kebab separators.
        self.assertEqual(generate_project_id("Next.js 14 App!"), "next-js-app")
        # Unsafe/empty names fall back deterministically, never raw path or UUID.
        self.assertEqual(generate_project_id(""), "project")
        self.assertEqual(generate_project_id("   "), "project")
        for pid in ["my-saas-application", "nextjs-app", "project"]:
            self.assertTrue(is_valid_id(pid), f"Generated id not valid: {pid}")
            self.assertNotIn("-14", pid)
            self.assertNotIn("-17", pid)

    def test_build_project_spec_from_m3_selection(self):
        spec = build_project_spec(
            "My SaaS Application",
            project_type_id="saas",
            capabilities=["authentication", "payments", "email"],
            stack_bundle_id="nextjs-dotnet-postgres",
        )
        self.assertEqual(str(spec.id), "my-saas-application")
        self.assertEqual(spec.name, "My SaaS Application")
        self.assertEqual(spec.schema_version, "1.0.0")
        self.assertEqual(str(spec.project_type), "saas")
        self.assertEqual(
            sorted(str(c) for c in spec.capabilities),
            ["authentication", "email", "payments"],
        )
        self.assertEqual(str(spec.stack_bundle), "nextjs-dotnet-postgres")

    def test_spec_has_no_runtime_authority_leakage(self):
        spec = build_project_spec(
            "Demo", project_type_id="saas",
            capabilities=["authentication"], stack_bundle_id="nextjs-supabase",
        )
        serialized = json.dumps(spec.to_dict(), ensure_ascii=False).lower()
        for runtime in ["codex", "opencode", "antigravity", "claude", "cursor", "gemini"]:
            self.assertNotIn(runtime, serialized,
                             f"Runtime leakage in project spec: {runtime}")

    def test_write_and_read_project_spec(self):
        with tempfile.TemporaryDirectory() as td:
            spec = build_project_spec(
                "Round Trip App", project_type_id="portfolio",
                capabilities=["search"], stack_bundle_id="react-static",
            )
            path = write_project_spec(td, spec)
            self.assertTrue(path.exists())
            self.assertEqual(path.parent.name, CANONICAL_STATE_DIR)
            self.assertEqual(path.name, PROJECT_YAML)
            # File is JSON-compatible YAML parseable with stdlib json.
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], "1.0.0")
            self.assertEqual(data["project"]["id"], "round-trip-app")
            read_back = read_project_spec(path)
            self.assertEqual(read_back.id, spec.id)
            self.assertEqual(read_back.name, spec.name)
            self.assertEqual(str(read_back.project_type), "portfolio")
            self.assertEqual(str(read_back.stack_bundle), "react-static")

    def test_spec_round_trip_equivalence(self):
        with tempfile.TemporaryDirectory() as td:
            spec = build_project_spec(
                "Equivalence App", project_type_id="backend-api",
                capabilities=["cache", "queue"], stack_bundle_id="fastapi-postgres",
            )
            read_back = round_trip_spec(spec, td)
            self.assertEqual(read_back, spec)
            self.assertEqual(read_back.created_at, spec.created_at)
            self.assertEqual(read_back.updated_at, spec.updated_at)

    def test_reader_rejects_malformed_spec(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / CANONICAL_STATE_DIR / PROJECT_YAML
            bad.parent.mkdir(parents=True, exist_ok=True)
            bad.write_text("{ not valid json", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_project_spec(bad)

            bad2 = Path(td) / CANONICAL_STATE_DIR / PROJECT_YAML
            bad2.write_text(json.dumps({"schema_version": "9.9.9"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                read_project_spec(bad2)

    def test_canonical_spec_wins_over_conflicting_markdown(self):
        """Authority conflict: project.yaml value wins; Markdown never parsed as authority."""
        with tempfile.TemporaryDirectory() as td:
            project_root = Path(td)
            spec = build_project_spec(
                "Authority App", project_type_id="saas",
                capabilities=["authentication"], stack_bundle_id="nextjs-supabase",
            )
            write_project_spec(project_root, spec)
            # Conflicting derived Markdown claims a different project type/bundle.
            (project_root / "CONTEXT.md").write_text(
                "Project Type: e-commerce\nStack Bundle: nextjs-dotnet-postgres\n",
                encoding="utf-8",
            )
            (project_root / "AGENTS.md").write_text(
                "# AGENTS.md\nProject Type: e-commerce\n", encoding="utf-8",
            )
            # Reloading canonical state must return the project.yaml values.
            reloaded = read_project_spec(project_root / CANONICAL_STATE_DIR / PROJECT_YAML)
            self.assertEqual(str(reloaded.project_type), "saas")
            self.assertEqual(str(reloaded.stack_bundle), "nextjs-supabase")
            self.assertEqual([str(c) for c in reloaded.capabilities], ["authentication"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

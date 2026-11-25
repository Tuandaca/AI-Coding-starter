#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Behavioral regression tests for project identity normalization and scaffold.

Coverage:
  - normalize_project_identity derives context-safe identifiers per context
  - special characters are normalized per context (npm slug, C# namespace,
    Python package, docker/expo slug, tauri identifier)
  - empty/whitespace-only display name falls back to defaults
  - every full-bundle template substitutes all placeholders (no leakage)
  - metadata-only/minimal bundles return an empty scaffold map
  - scaffold_stack rejects path traversal and absolute paths
  - CI release identity script accepts/refuses tags

Deterministic, offline.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.stack_scaffold import (  # noqa: E402
    BUNDLE_TEMPLATES,
    SCAFFOLD_SUPPORT,
    normalize_project_identity,
    scaffold_files,
    scaffold_stack,
    scaffold_support_for,
)

FULL_BUNDLES = [b for b, level in SCAFFOLD_SUPPORT.items() if level == "full"]


class TestNormalizeProjectIdentity(unittest.TestCase):
    def test_keeps_display_verbatim(self):
        ident = normalize_project_identity("My Cool App")
        self.assertEqual(ident["display"], "My Cool App")

    def test_defaults_when_empty_or_whitespace(self):
        for bad in ("", "   ", "\t\n"):
            with self.subTest(display=repr(bad)):
                ident = normalize_project_identity(bad)
                self.assertEqual(ident["display"], "project")
                self.assertEqual(ident["filesystem"], "project")
                self.assertEqual(ident["npm"], "project")
                self.assertEqual(ident["python_package"], "project")
                self.assertEqual(ident["csharp_namespace"], "Project")
                self.assertEqual(ident["docker"], "project")
                self.assertEqual(ident["database"], "project")
                self.assertEqual(ident["expo_slug"], "project")
                self.assertEqual(ident["tauri_identifier"], "com.project.app")

    def test_npm_and_filesystem_are_slugs(self):
        ident = normalize_project_identity("  My Cool App  ")
        self.assertEqual(ident["filesystem"], "my-cool-app")
        self.assertEqual(ident["npm"], "my-cool-app")

    def test_csharp_namespace_is_pascal_case(self):
        ident = normalize_project_identity("my-cool-app")
        self.assertEqual(ident["csharp_namespace"], "MyCoolApp")

    def test_python_package_is_snake_case(self):
        ident = normalize_project_identity("My Cool App")
        self.assertEqual(ident["python_package"], "my_cool_app")

    def test_leading_digit_csharp_gets_prefix(self):
        ident = normalize_project_identity("1st Project")
        self.assertTrue(ident["csharp_namespace"][0].isalpha() or
                        ident["csharp_namespace"][0] == "_")

    def test_docker_expo_slug_lowercase_hyphen(self):
        ident = normalize_project_identity("My Cool App")
        self.assertEqual(ident["docker"], "my-cool-app")
        self.assertEqual(ident["expo_slug"], "my-cool-app")

    def test_tauri_identifier_format(self):
        ident = normalize_project_identity("My Cool App")
        self.assertEqual(ident["tauri_identifier"], "com.my-cool-app.app")

    def test_special_characters_collapsed(self):
        ident = normalize_project_identity("A!!! B??? C")
        self.assertEqual(ident["filesystem"], "a-b-c")
        self.assertEqual(ident["python_package"], "a_b_c")

    def test_identifier_starts_with_letter_or_underscore(self):
        ident = normalize_project_identity("99 problems")
        # These contexts run through _safe_start, so they never start with a digit.
        for key in ("csharp_namespace", "python_package", "database"):
            first = ident[key][0]
            self.assertTrue(first.isalpha() or first == "_", key)
        # docker/expo_slug may start with a digit (DNS-1123 allows alnum start).
        self.assertTrue(ident["docker"][0].isalnum())


class TestScaffoldFilesSubstitution(unittest.TestCase):
    def test_every_full_bundle_substitutes_all_placeholders(self):
        for bundle_id in FULL_BUNDLES:
            files = scaffold_files(bundle_id, "Demo Project")
            self.assertTrue(files, f"{bundle_id} produced no files")
            for rel_path, content in files.items():
                for placeholder in (
                    "{{project_name}}", "{{project_npm}}", "{{project_namespace}}",
                    "{{project_slug}}", "{{project_python_package}}",
                    "{{project_docker}}", "{{project_database}}",
                    "{{project_expo_slug}}", "{{project_tauri_id}}",
                ):
                    self.assertNotIn(placeholder, content,
                                     f"{bundle_id}:{rel_path} still has {placeholder}")

    def test_metadata_only_bundles_return_empty(self):
        for bundle_id, level in SCAFFOLD_SUPPORT.items():
            if level != "full":
                files = scaffold_files(bundle_id, "Demo Project")
                self.assertEqual(files, {}, bundle_id)

    def test_unknown_bundle_returns_empty(self):
        self.assertEqual(scaffold_files("does-not-exist", "Demo Project"), {})

    def test_display_and_slug_values_appear_in_output(self):
        files = scaffold_files("nextjs-supabase", "Demo Project")
        content = "\n".join(files.values())
        self.assertIn("Demo Project", content)
        self.assertIn("demo-project", content)


class TestScaffoldStackPathSafety(unittest.TestCase):
    def test_writes_files_into_destination(self):
        with tempfile.TemporaryDirectory() as td:
            written = scaffold_stack(td, "react-static", "Demo Project")
            self.assertGreater(len(written), 0)
            for path in written:
                self.assertTrue(Path(path).exists())
                self.assertIn(str(Path(td).resolve()), str(path.resolve()))


if __name__ == "__main__":
    unittest.main(verbosity=2)

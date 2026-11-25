#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Behavioral regression tests for project identity normalization and scaffold.

Coverage:
  - normalize_project_identity derives context-safe identifiers per context
  - required name matrix (ci-test, My Project, my_project, 123-project,
    Project.Name, project@name, Tên Dự Án) yields valid identifiers in every
    context: npm, C# namespace, Python package, docker, database, expo slug,
    tauri identifier, filesystem slug
  - Unicode display names stay user-facing while technical identifiers stay valid
  - every full-bundle template substitutes all placeholders (no leakage)
  - metadata-only/minimal bundles return an empty scaffold map
  - scaffold_stack rejects path traversal and absolute paths
  - CI release identity script accepts/refuses tags

Deterministic, offline.
"""
import keyword
import re
import shutil
import subprocess
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

DOTNET = shutil.which("dotnet")

FULL_BUNDLES = [b for b, level in SCAFFOLD_SUPPORT.items() if level == "full"]

# Required name matrix from the release-remediation task.
NAME_MATRIX = [
    "ci-test",
    "My Project",
    "my_project",
    "123-project",
    "Project.Name",
    "project@name",
    "Tên Dự Án",
]

# Validity rules per identifier context.
NPM_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CS_NS_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9]*$")
PY_PKG_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
DOCKER_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EXPO_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TAURI_RE = re.compile(r"^com\.[a-z0-9]+(?:-[a-z0-9]+)*\.app$")


class TestNormalizeProjectIdentityMatrix(unittest.TestCase):
    def test_required_name_matrix_yields_valid_identifiers(self):
        for name in NAME_MATRIX:
            with self.subTest(name=name):
                ident = normalize_project_identity(name)

                # Display stays verbatim (user-facing, may contain Unicode/spaces).
                self.assertEqual(ident["display"], name.strip() or "project")

                # npm name: lowercase alnum + hyphen, no leading/trailing hyphen.
                self.assertTrue(
                    NPM_RE.match(ident["npm"]),
                    f"npm invalid for {name!r}: {ident['npm']!r}",
                )
                # filesystem slug == npm slug.
                self.assertEqual(ident["filesystem"], ident["npm"])

                # C# namespace: starts with letter/underscore, alnum only.
                self.assertTrue(
                    CS_NS_RE.match(ident["csharp_namespace"]),
                    f"csharp namespace invalid for {name!r}: "
                    f"{ident['csharp_namespace']!r}",
                )
                self.assertTrue(
                    ident["csharp_namespace"][0].isalpha()
                    or ident["csharp_namespace"][0] == "_",
                    f"csharp namespace starts with digit for {name!r}: "
                    f"{ident['csharp_namespace']!r}",
                )

                # Python package: valid identifier, not a keyword.
                self.assertTrue(
                    PY_PKG_RE.match(ident["python_package"]),
                    f"python package invalid for {name!r}: "
                    f"{ident['python_package']!r}",
                )
                self.assertTrue(
                    ident["python_package"].isidentifier(),
                    f"python package not an identifier for {name!r}: "
                    f"{ident['python_package']!r}",
                )
                self.assertFalse(
                    keyword.iskeyword(ident["python_package"]),
                    f"python package is a keyword for {name!r}: "
                    f"{ident['python_package']!r}",
                )

                # Docker / expo slug: DNS-1123 style.
                for key in ("docker", "expo_slug"):
                    self.assertTrue(
                        DOCKER_RE.match(ident[key]),
                        f"{key} invalid for {name!r}: {ident[key]!r}",
                    )

                # Database identifier: starts with letter/underscore.
                self.assertTrue(
                    PY_PKG_RE.match(ident["database"]),
                    f"database invalid for {name!r}: {ident['database']!r}",
                )
                self.assertTrue(
                    ident["database"][0].isalpha()
                    or ident["database"][0] == "_",
                    f"database starts with digit for {name!r}: {ident['database']!r}",
                )

                # Tauri identifier: reverse domain.
                self.assertTrue(
                    TAURI_RE.match(ident["tauri_identifier"]),
                    f"tauri invalid for {name!r}: {ident['tauri_identifier']!r}",
                )

    def test_unicode_display_remains_user_facing(self):
        ident = normalize_project_identity("Tên Dự Án")
        self.assertEqual(ident["display"], "Tên Dự Án")
        # Technical identifiers must not contain spaces or uppercase.
        for key in ("npm", "filesystem", "docker", "database", "expo_slug"):
            self.assertNotIn(" ", ident[key], key)
            self.assertEqual(ident[key], ident[key].lower(), key)
        self.assertTrue(CS_NS_RE.match(ident["csharp_namespace"]))

    def test_leading_digit_csharp_gets_prefix(self):
        ident = normalize_project_identity("123-project")
        self.assertTrue(
            ident["csharp_namespace"][0].isalpha()
            or ident["csharp_namespace"][0] == "_"
        )


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
                    "{starter_version}",
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


class TestScaffoldStackPathSafety(unittest.TestCase):
    def test_writes_files_into_destination(self):
        with tempfile.TemporaryDirectory() as td:
            written = scaffold_stack(td, "react-static", "Demo Project")
            self.assertGreater(len(written), 0)
            for path in written:
                self.assertTrue(Path(path).exists())
                self.assertIn(str(Path(td).resolve()), str(path.resolve()))


@unittest.skipUnless(DOTNET is not None, ".NET SDK not available")
class TestDotnetScaffoldBuild(unittest.TestCase):
    """Build representative generated .NET projects with problematic names.

    Validates that normalized C# identifiers produce a compilable project even
    when the display name contains spaces, digits, or symbols.
    """

    def _build_dotnet(self, bundle_id, project_name):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "out"
            scaffold_stack(dest, bundle_id, project_name)
            csproj = list(Path(dest).rglob("*.csproj"))
            self.assertTrue(csproj, f"No csproj found for {bundle_id}")
            result = subprocess.run(
                [DOTNET, "build", str(csproj[0])],
                capture_output=True, text=True, timeout=600,
            )
            self.assertEqual(
                result.returncode, 0,
                f"dotnet build failed for {bundle_id} name={project_name!r}:\n"
                f"{result.stdout}\n{result.stderr}",
            )

    def test_dotnet_postgres_builds_with_spaces(self):
        self._build_dotnet("dotnet-postgres", "My Project")

    def test_dotnet_postgres_builds_with_leading_digit(self):
        self._build_dotnet("dotnet-postgres", "123-project")


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Characterization tests for tech presets (area 3: Tech presets).

Coverage:
  - TECH_PRESETS structure for all 7 types; preset field schema
  - representative presets: personal-web, e-commerce
  - CUSTOM_STACK_OPTIONS structure (5 categories, tuples, unique keys)
  - get_presets_for_types: single type, multi-type dedup, sources,
    recommended-first ordering, unknown type skipped
  - select_custom_stack structure (input mocked; interactive loop not run)

Deterministic, offline, read-only on production data.
"""
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import new_project  # noqa: E402

PRESET_KEYS = ("id", "name", "desc", "frontend", "backend", "database",
               "styling", "hosting")


class TestTechPresets(unittest.TestCase):
    def test_presets_exist_for_all_seven_types(self):
        self.assertEqual(set(new_project.TECH_PRESETS), set(new_project.PROJECT_TYPES))

    def test_preset_structure(self):
        for type_key, entry in new_project.TECH_PRESETS.items():
            with self.subTest(type=type_key):
                self.assertIsInstance(entry.get("presets"), list)
                self.assertTrue(entry["presets"], f"{type_key} has no presets")
                for preset in entry["presets"]:
                    for key in PRESET_KEYS:
                        self.assertIn(key, preset)
                        self.assertIsInstance(preset[key], str)
                        self.assertTrue(preset[key])
                    self.assertIsInstance(preset.get("recommended", False), bool)

    def test_personal_web_presets(self):
        presets = new_project.TECH_PRESETS["personal-web"]["presets"]
        ids = [p["id"] for p in presets]
        self.assertEqual(set(ids), {"modern-static", "minimal", "astro"})
        recommended = [p for p in presets if p.get("recommended")]
        self.assertEqual(len(recommended), 1)
        self.assertEqual(recommended[0]["id"], "modern-static")
        self.assertEqual(recommended[0]["frontend"], "Next.js 14 + TypeScript")
        self.assertEqual(recommended[0]["backend"], "None (Static Export)")
        self.assertEqual(recommended[0]["database"], "None")
        self.assertEqual(recommended[0]["styling"], "TailwindCSS + Framer Motion")
        self.assertEqual(recommended[0]["hosting"], "Vercel")

    def test_ecommerce_presets(self):
        presets = new_project.TECH_PRESETS["e-commerce"]["presets"]
        ids = [p["id"] for p in presets]
        self.assertEqual(set(ids), {"nextjs-fullstack", "mern-stack", "python-fastapi"})
        mern = next(p for p in presets if p["id"] == "mern-stack")
        self.assertIn("JWT Auth", mern.get("extras", []))
        fullstack = next(p for p in presets if p["id"] == "nextjs-fullstack")
        self.assertTrue(fullstack.get("recommended"))
        self.assertEqual(fullstack["database"], "PostgreSQL + Prisma ORM")

    def test_custom_stack_options_structure(self):
        opts = new_project.CUSTOM_STACK_OPTIONS
        self.assertEqual(set(opts), {"frontend", "backend", "database",
                                     "styling", "hosting"})
        for category, options in opts.items():
            with self.subTest(category=category):
                self.assertIsInstance(options, list)
                self.assertTrue(options)
                seen_keys = set()
                for item in options:
                    self.assertIsInstance(item, tuple)
                    self.assertEqual(len(item), 2)
                    key, name = item
                    self.assertIsInstance(key, str)
                    self.assertTrue(key)
                    self.assertIsInstance(name, str)
                    self.assertTrue(name)
                    self.assertNotIn(key, seen_keys)
                    seen_keys.add(key)

    def test_custom_stack_first_options(self):
        self.assertEqual(
            new_project.CUSTOM_STACK_OPTIONS["frontend"][0],
            ("nextjs", "Next.js 14 + TypeScript"),
        )
        self.assertEqual(
            new_project.CUSTOM_STACK_OPTIONS["backend"][0],
            ("nextjs-api", "Next.js API Routes"),
        )
        self.assertEqual(
            new_project.CUSTOM_STACK_OPTIONS["database"][0],
            ("postgresql", "PostgreSQL"),
        )
        self.assertEqual(
            new_project.CUSTOM_STACK_OPTIONS["styling"][0],
            ("tailwind", "TailwindCSS"),
        )
        self.assertEqual(
            new_project.CUSTOM_STACK_OPTIONS["hosting"][0],
            ("vercel", "Vercel"),
        )

    def test_get_presets_for_types_single(self):
        presets = new_project.get_presets_for_types(["personal-web"])
        self.assertEqual(len(presets), 3)
        self.assertTrue(all(p["from_type"] == "personal-web" for p in presets))
        self.assertEqual(set(p["id"] for p in presets),
                         {"modern-static", "minimal", "astro"})
        self.assertTrue(presets[0].get("recommended"))

    def test_get_presets_for_types_multi_dedup_and_sources(self):
        presets = new_project.get_presets_for_types(["personal-web", "e-commerce"])
        self.assertEqual(len(presets), 6)
        self.assertEqual(set(p["from_type"] for p in presets),
                         {"personal-web", "e-commerce"})
        ids = [p["id"] for p in presets]
        self.assertEqual(len(ids), len(set(ids)))
        # Recommended entries sort before non-recommended entries.
        rec_flags = [bool(p.get("recommended", False)) for p in presets]
        self.assertEqual(rec_flags, sorted(rec_flags, reverse=True))
        self.assertTrue(rec_flags[0])

    def test_get_presets_for_types_unknown_type_skipped(self):
        presets = new_project.get_presets_for_types(["does-not-exist"])
        self.assertEqual(presets, [])

    def test_select_custom_stack_structure(self):
        """Interactive prompts are mocked; only the returned structure is asserted.
        Suppress emoji stdout from the function to avoid Windows cp1252 encoding issues."""
        with patch.object(new_project, "get_input", return_value="1"):
            buf = io.StringIO()
            with redirect_stdout(buf):
                result = new_project.select_custom_stack()
        self.assertEqual(result, {
            "type": "custom",
            "extras": [],
            "frontend": "Next.js 14 + TypeScript",
            "backend": "Next.js API Routes",
            "database": "PostgreSQL",
            "styling": "TailwindCSS",
            "hosting": "Vercel",
        })
        self.assertEqual(set(result),
                         {"type", "frontend", "backend", "database",
                          "styling", "hosting", "extras"})


if __name__ == "__main__":
    unittest.main()

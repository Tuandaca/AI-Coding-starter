#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Characterization tests for merge_tech_stacks (area 4: Multi-preset merge).

These tests CAPTURE the current blind-merge behavior and must NOT be
changed to "fix" it:
  - values are joined with " + "
  - dedup is exact-string only (prefix/substring overlaps survive)
  - up to 3 presets are merged
  - missing fields become "TDD"... no, become "TBD"

merge_tech_stacks is intentionally not a compatibility resolver here.
"""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import new_project  # noqa: E402


class TestMergeTechStacks(unittest.TestCase):
    def test_single_preset_returns_its_fields(self):
        presets = new_project.TECH_PRESETS["personal-web"]["presets"]
        modern = next(p for p in presets if p["id"] == "modern-static")
        merged = new_project.merge_tech_stacks([modern])
        self.assertEqual(merged["type"], "preset")
        self.assertEqual(merged["preset_name"], "🚀 Modern Static")
        self.assertEqual(merged["frontend"], "Next.js 14 + TypeScript")
        self.assertEqual(merged["backend"], "None (Static Export)")
        self.assertEqual(merged["database"], "None")
        self.assertEqual(merged["styling"], "TailwindCSS + Framer Motion")
        self.assertEqual(merged["hosting"], "Vercel")
        self.assertEqual(merged["extras"], [])

    def test_all_personal_web_presets_blind_merge_output(self):
        """Current output: unique exact-string values joined with ' + '."""
        presets = new_project.TECH_PRESETS["personal-web"]["presets"]
        merged = new_project.merge_tech_stacks(presets)
        self.assertEqual(merged["type"], "preset")
        self.assertEqual(
            merged["preset_name"],
            "🚀 Modern Static + 🎯 Minimal Pure + ⚡ Astro Islands",
        )
        self.assertEqual(
            merged["frontend"],
            "Next.js 14 + TypeScript + HTML + CSS + Vanilla JS + "
            "Astro + React/Vue components",
        )
        self.assertEqual(
            merged["backend"],
            "None (Static Export) + None + None (Static)",
        )
        # "None" is an exact duplicate across all three presets.
        self.assertEqual(merged["database"], "None")
        # "TailwindCSS" != "TailwindCSS + Framer Motion" (exact-string dedup).
        self.assertEqual(
            merged["styling"],
            "TailwindCSS + Framer Motion + Custom CSS + TailwindCSS",
        )
        self.assertEqual(
            merged["hosting"],
            "Vercel + GitHub Pages / Netlify + Vercel / Cloudflare",
        )
        self.assertEqual(merged["extras"], [])

    def test_cross_type_merge_dedups_only_exact_duplicates(self):
        ecomm = new_project.TECH_PRESETS["e-commerce"]["presets"]
        nextjs_fullstack = next(p for p in ecomm if p["id"] == "nextjs-fullstack")
        mern = next(p for p in ecomm if p["id"] == "mern-stack")
        merged = new_project.merge_tech_stacks([nextjs_fullstack, mern])
        self.assertEqual(merged["type"], "preset")
        self.assertEqual(merged["preset_name"],
                         "🛒 Next.js Fullstack + 🔥 MERN Stack")
        self.assertEqual(
            merged["frontend"],
            "Next.js 14 + TypeScript + React + TypeScript",
        )
        self.assertEqual(
            merged["backend"],
            "Next.js API Routes + Node.js + Express",
        )
        self.assertEqual(
            merged["database"],
            "PostgreSQL + Prisma ORM + MongoDB + Mongoose",
        )
        # Exact-string dedup: both stylings differ, so both survive.
        self.assertEqual(
            merged["styling"],
            "TailwindCSS + shadcn/ui + TailwindCSS",
        )
        self.assertEqual(
            merged["hosting"],
            "Vercel + Supabase + Railway / Render",
        )
        self.assertEqual(
            merged["extras"],
            ["Stripe Payments", "NextAuth", "Redis Cache",
             "JWT Auth", "Stripe/PayOS"],
        )

    def test_empty_list_returns_tbd_fields(self):
        merged = new_project.merge_tech_stacks([])
        self.assertEqual(merged["type"], "preset")
        self.assertEqual(merged["preset_name"], "")
        for field in ("frontend", "backend", "database", "styling", "hosting"):
            self.assertEqual(merged[field], "TBD")
        self.assertEqual(merged["extras"], [])

    def test_returned_shape(self):
        preset = new_project.TECH_PRESETS["saas-platform"]["presets"][0]
        merged = new_project.merge_tech_stacks([preset])
        self.assertIsInstance(merged, dict)
        self.assertEqual(set(merged), {
            "type", "preset_name", "frontend", "backend", "database",
            "styling", "hosting", "extras",
        })
        self.assertIsInstance(merged["extras"], list)


if __name__ == "__main__":
    unittest.main()

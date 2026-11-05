#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Characterization tests for merge_requirements (area 5: Requirement merging).

Coverage:
  - single type: sorted lists, exact known content for personal-web
  - multiple types: union, de-duplication across types, sorted output
  - duplicates in input: set-based fields dedup; focus list appends per entry
  - empty input: only EXTRA_WORKFLOWS are added to workflows
  - ordering: every list key sorted ascending
  - unknown type raises KeyError (current behavior, captured as-is)

Deterministic, offline, read-only on production data.
"""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import new_project  # noqa: E402

LIST_KEYS = ("agents", "skills", "shared", "workflows", "scripts")


class TestMergeRequirements(unittest.TestCase):
    def assert_sorted_lists(self, merged):
        for key in LIST_KEYS:
            self.assertEqual(merged[key], sorted(merged[key]))

    def test_single_type(self):
        merged = new_project.merge_requirements(["personal-web"])
        self.assertEqual(merged["agents"], [
            "frontend-specialist.md", "orchestrator.md",
            "project-planner.md", "seo-specialist.md",
        ])
        self.assertEqual(merged["skills"], [
            "cro-expert-kit", "modern-web-architect", "seo-expert-kit",
        ])
        self.assertEqual(merged["shared"], [
            "design-system", "seo-master", "ui-ux-pro-max", "vitals-templates",
        ])
        self.assertEqual(merged["workflows"], [
            "commit.md", "create.md", "deploy.md", "enhance.md", "fix.md",
            "preview.md", "progress.md", "seo.md", "status.md",
            "ui-ux-pro-max.md",
        ])
        self.assertEqual(merged["scripts"], ["auto_preview.py", "checklist.py"])
        self.assertEqual(merged["focus"], [
            "Premium UI/UX, SEO optimization, fast performance",
        ])
        self.assert_sorted_lists(merged)

    def test_multiple_types_dedup_and_sort(self):
        merged = new_project.merge_requirements(["personal-web", "e-commerce"])
        self.assertEqual(merged["agents"], [
            "backend-specialist.md", "frontend-specialist.md",
            "orchestrator.md", "project-planner.md", "security-auditor.md",
            "seo-specialist.md", "test-engineer.md",
        ])
        self.assertEqual(merged["skills"], [
            "api-documenter", "cro-expert-kit", "database-migration",
            "modern-web-architect", "security-auditor", "seo-expert-kit",
            "tdd-master-workflow",
        ])
        self.assertEqual(merged["scripts"], [
            "auto_preview.py", "checklist.py", "verify_all.py",
        ])
        # Every item appears exactly once; lists are sorted.
        for key in LIST_KEYS:
            items = merged[key]
            self.assertEqual(items, sorted(items))
            self.assertEqual(len(items), len(set(items)))

    def test_empty_input(self):
        merged = new_project.merge_requirements([])
        self.assertEqual(merged["agents"], [])
        self.assertEqual(merged["skills"], [])
        self.assertEqual(merged["shared"], [])
        self.assertEqual(merged["scripts"], [])
        self.assertEqual(merged["workflows"],
                         sorted(new_project.EXTRA_WORKFLOWS))
        self.assertEqual(merged["focus"], [])

    def test_three_types(self):
        merged = new_project.merge_requirements(
            ["personal-web", "e-commerce", "saas-platform"])
        self.assertIsInstance(merged["agents"], list)
        self.assertTrue(all(isinstance(a, str) for a in merged["agents"]))
        self.assertEqual(len(merged["focus"]), 3)
        self.assert_sorted_lists(merged)

    def test_duplicate_types_in_input(self):
        merged = new_project.merge_requirements(["personal-web", "personal-web"])
        single = new_project.merge_requirements(["personal-web"])
        self.assertEqual(merged["agents"], single["agents"])
        self.assertEqual(merged["skills"], single["skills"])
        self.assertEqual(merged["shared"], single["shared"])
        self.assertEqual(merged["workflows"], single["workflows"])
        self.assertEqual(merged["scripts"], single["scripts"])
        # focus is appended per input entry, so duplicates survive there.
        self.assertEqual(len(merged["focus"]), 2)

    def test_unknown_type_raises_key_error(self):
        # Current behavior: PROJECT_TYPES[type_key] raises KeyError.
        with self.assertRaises(KeyError):
            new_project.merge_requirements(["does-not-exist"])


if __name__ == "__main__":
    unittest.main()

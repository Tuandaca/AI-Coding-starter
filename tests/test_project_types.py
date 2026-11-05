#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Characterization tests for PROJECT_TYPES (area 2: Project types).

Coverage:
  - exactly 7 project types
  - required structure per type (name, description, agents, skills, shared,
    workflows, scripts, focus) with non-empty values
  - file extension conventions (.md agents/workflows, .py scripts)
  - no duplicates within any requirement list
  - representative types: personal-web, e-commerce, fullstack
  - type id set matches TECH_PRESETS key set

Deterministic, offline, read-only on production data.
"""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import new_project  # noqa: E402

EXPECTED_TYPES = {
    "personal-web",
    "e-commerce",
    "saas-platform",
    "mobile-app",
    "game-dev",
    "ai-ml",
    "fullstack",
}

REQUIRED_KEYS = {
    "name", "description", "agents", "skills", "shared",
    "workflows", "scripts", "focus",
}

LIST_KEYS = ("agents", "skills", "shared", "workflows", "scripts")


class TestProjectTypes(unittest.TestCase):
    def test_exactly_seven_types(self):
        self.assertEqual(set(new_project.PROJECT_TYPES), EXPECTED_TYPES)

    def test_each_type_has_required_structure(self):
        for type_key, cfg in new_project.PROJECT_TYPES.items():
            with self.subTest(type=type_key):
                self.assertEqual(set(cfg), REQUIRED_KEYS)
                self.assertIsInstance(cfg["name"], str)
                self.assertTrue(cfg["name"])
                self.assertIsInstance(cfg["description"], str)
                self.assertTrue(cfg["description"])
                self.assertIsInstance(cfg["focus"], str)
                self.assertTrue(cfg["focus"])
                for key in LIST_KEYS:
                    self.assertIsInstance(cfg[key], list)
                    self.assertTrue(cfg[key], f"{type_key}.{key} is empty")
                    for item in cfg[key]:
                        self.assertIsInstance(item, str)
                        self.assertTrue(item)

    def test_agent_filenames_end_with_md(self):
        for cfg in new_project.PROJECT_TYPES.values():
            for agent in cfg["agents"]:
                self.assertTrue(agent.endswith(".md"))

    def test_workflow_filenames_end_with_md(self):
        for cfg in new_project.PROJECT_TYPES.values():
            for workflow in cfg["workflows"]:
                self.assertTrue(workflow.endswith(".md"))

    def test_script_filenames_end_with_py(self):
        for cfg in new_project.PROJECT_TYPES.values():
            for script in cfg["scripts"]:
                self.assertTrue(script.endswith(".py"))

    def test_no_duplicates_within_each_list(self):
        for type_key, cfg in new_project.PROJECT_TYPES.items():
            with self.subTest(type=type_key):
                for key in LIST_KEYS:
                    items = cfg[key]
                    self.assertEqual(
                        len(items), len(set(items)),
                        f"duplicate entries in {type_key}.{key}",
                    )

    def test_personal_web_representative(self):
        cfg = new_project.PROJECT_TYPES["personal-web"]
        self.assertEqual(cfg["agents"], [
            "frontend-specialist.md",
            "project-planner.md",
            "orchestrator.md",
            "seo-specialist.md",
        ])
        self.assertIn("seo-expert-kit", cfg["skills"])
        self.assertIn("cro-expert-kit", cfg["skills"])
        self.assertIn("seo.md", cfg["workflows"])
        self.assertIn("auto_preview.py", cfg["scripts"])
        self.assertIn("checklist.py", cfg["scripts"])

    def test_e_commerce_representative(self):
        cfg = new_project.PROJECT_TYPES["e-commerce"]
        self.assertIn("security-auditor.md", cfg["agents"])
        self.assertIn("test-engineer.md", cfg["agents"])
        self.assertIn("test.md", cfg["workflows"])
        self.assertIn("deploy.md", cfg["workflows"])
        self.assertIn("security.md", cfg["workflows"])
        self.assertIn("verify_all.py", cfg["scripts"])

    def test_fullstack_representative(self):
        cfg = new_project.PROJECT_TYPES["fullstack"]
        self.assertIn("debugger.md", cfg["agents"])
        self.assertIn("database-migration", cfg["skills"])
        self.assertIn("debug.md", cfg["workflows"])
        self.assertIn("verify_all.py", cfg["scripts"])

    def test_type_ids_match_tech_presets_keys(self):
        self.assertEqual(set(new_project.PROJECT_TYPES), set(new_project.TECH_PRESETS))


if __name__ == "__main__":
    unittest.main()

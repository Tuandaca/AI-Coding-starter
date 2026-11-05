#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Characterization tests for generated files (area 7: generate_gemini_md /
generate_context_md).

Coverage:
  - GEMINI.md contains project name, agent identity, project types,
    types footer, active agents/workflows
  - GEMINI.md contains tech stack metadata (frontend, backend, database,
    styling, hosting, extras) when a stack is provided
  - GEMINI.md falls back to placeholder when stack is None or "skip"
  - GEMINI.md environment context section when env_info provided
  - CONTEXT.md contains project name, types, tech info, and a date stamp
  - CONTEXT.md placeholder when no tech stack

Targeted substring/regex assertions only — no giant snapshot comparisons.
All output goes into tempfile.TemporaryDirectory().
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import new_project  # noqa: E402

MERGED = new_project.merge_requirements(["personal-web", "saas-platform"])

TECH_STACK = {
    "type": "preset",
    "preset_name": "☁️ Next.js SaaS Starter",
    "frontend": "Next.js 14 + TypeScript",
    "backend": "Next.js API + Supabase Edge Functions",
    "database": "Supabase PostgreSQL",
    "styling": "TailwindCSS + shadcn/ui",
    "hosting": "Vercel",
    "extras": ["Supabase Auth", "Stripe Subscriptions", "Resend Email"],
}


class TestGeneratedFiles(unittest.TestCase):
    def _generate_gemini(self, tech_stack=None, env_info=None):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td)
            new_project.generate_gemini_md(
                dest, "My Project", ["personal-web"], MERGED,
                tech_stack=tech_stack, env_info=env_info,
            )
            return (dest / "GEMINI.md").read_text(encoding="utf-8")

    def test_gemini_md_contains_project_name_and_types(self):
        content = self._generate_gemini()
        self.assertIn("# GEMINI.md - My Project", content)
        self.assertIn("My ProjectAgent", content)
        self.assertIn("Personal Web / Portfolio", content)
        self.assertIn("*Types: personal-web*", content)

    def test_gemini_md_contains_tech_stack_metadata(self):
        content = self._generate_gemini(tech_stack=TECH_STACK)
        self.assertIn("## 🛠️ Tech Stack", content)
        self.assertIn("Next.js 14 + TypeScript", content)
        self.assertIn("Supabase PostgreSQL", content)
        self.assertIn("Vercel", content)
        self.assertIn("Supabase Auth, Stripe Subscriptions, Resend Email", content)

    def test_gemini_md_skip_or_none_uses_placeholder(self):
        for tech_stack in (None, {"type": "skip"}):
            with self.subTest(tech_stack=tech_stack):
                content = self._generate_gemini(tech_stack=tech_stack)
                self.assertIn("Tech stack chưa được định nghĩa", content)

    def test_gemini_md_lists_agents_and_workflows(self):
        content = self._generate_gemini()
        self.assertIn("## Active Agents", content)
        self.assertIn("- `frontend-specialist`", content)
        self.assertIn("## Available Workflows", content)
        self.assertIn("- `/create`", content)

    def test_gemini_md_env_info_section(self):
        env_info = {
            "git_user": {"name": "QA Engineer", "email": "qa@example.com"},
            "tools": {"python": "3.11.9"},
            "os_info": {"os": "Windows 11", "shell": "powershell"},
        }
        content = self._generate_gemini(env_info=env_info)
        self.assertIn("## 🌍 Environment Context", content)
        self.assertIn("QA Engineer", content)
        self.assertIn("qa@example.com", content)

    def test_context_md_contains_project_and_tech_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td)
            new_project.generate_context_md(
                dest, "My Project", ["personal-web", "saas-platform"],
                tech_stack=TECH_STACK,
            )
            content = (dest / "CONTEXT.md").read_text(encoding="utf-8")
            self.assertIn("# 📋 PROJECT CONTEXT - My Project", content)
            self.assertIn("Personal Web / Portfolio", content)
            self.assertIn("SaaS Platform", content)
            self.assertIn("Next.js 14 + TypeScript", content)
            self.assertIn("Supabase PostgreSQL", content)
            self.assertIn("Vercel", content)
            self.assertRegex(content, r"\d{4}-\d{2}-\d{2}")

    def test_context_md_no_stack_placeholder(self):
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td)
            new_project.generate_context_md(dest, "X", ["personal-web"],
                                            tech_stack=None)
            content = (dest / "CONTEXT.md").read_text(encoding="utf-8")
            self.assertIn("(Chưa định nghĩa - AI sẽ đề xuất)", content)


if __name__ == "__main__":
    unittest.main()

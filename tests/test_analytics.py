#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Characterization tests for analytics.py (area 8: Analytics).

Coverage:
  - calculate_progress: [x], [X], [ ], [/] checkbox parsing
  - empty input file
  - missing sections (progress calculation still proceeds)
  - malformed / binary input (no crash)
  - missing CONTEXT.md file (no-context status)
  - oversized file (error status)
  - valid case (progress, status, current_phase)
  - load_analytics / save_analytics / track_project round trips

All analytics I/O is redirected to temp directories; the real
~/.vibecoding store is never touched, and log_error is silenced so no
files are written outside the temp dirs.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import analytics  # noqa: E402


class TestAnalytics(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="analytics_test_"))
        self.analytics_file = self.temp_dir / "analytics.json"
        self._patches = [
            patch.object(analytics, "get_analytics_dir",
                         return_value=self.temp_dir),
            patch.object(analytics, "get_analytics_path",
                         return_value=self.analytics_file),
            patch.object(analytics, "log_error", return_value=None),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in reversed(self._patches):
            p.stop()

    # --- calculate_progress ---

    def test_missing_context_file(self):
        result = analytics.calculate_progress(self.temp_dir / "CONTEXT.md")
        self.assertEqual(result["status"], "no-context")
        self.assertEqual(result["current_phase"], "No CONTEXT.md")
        self.assertEqual(result["progress"], 0)
        self.assertEqual(result["done"], 0)
        self.assertEqual(result["total"], 0)

    def test_empty_file_is_paused(self):
        p = self.temp_dir / "CONTEXT.md"
        p.write_text("", encoding="utf-8")
        result = analytics.calculate_progress(p)
        self.assertEqual(result["progress"], 0)
        self.assertEqual(result["status"], "paused")
        self.assertEqual(result["done"], 0)
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["current_phase"], "Unknown")

    def test_checkbox_parsing_all_variants(self):
        content = """# 📋 PROJECT CONTEXT - X

## 📊 Project Status
| Phase | Planning |

## 🎯 Current Focus
> Testing checkboxes

- [x] done lowercase
- [X] done uppercase
- [ ] pending
- [/] in progress
"""
        p = self.temp_dir / "CONTEXT.md"
        p.write_text(content, encoding="utf-8")
        result = analytics.calculate_progress(p)
        self.assertEqual(result["done"], 2)
        self.assertEqual(result["in_progress"], 1)
        self.assertEqual(result["total"], 4)
        self.assertEqual(result["progress"], 50)
        self.assertEqual(result["status"], "in-progress")
        self.assertEqual(result["current_phase"], "Testing checkboxes")

    def test_missing_sections_still_calculates_progress(self):
        content = """Random notes without required sections.

- [x] first task
- [X] second task
- [ ] still open
"""
        p = self.temp_dir / "CONTEXT.md"
        p.write_text(content, encoding="utf-8")
        result = analytics.calculate_progress(p)
        self.assertEqual(result["done"], 2)
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["progress"], 67)
        self.assertEqual(result["status"], "in-progress")
        self.assertEqual(result["current_phase"], "Unknown")

    def test_all_done_is_complete(self):
        content = "## 🎯 Current Focus\n> Finishing\n\n- [x] a\n- [X] b\n"
        p = self.temp_dir / "CONTEXT.md"
        p.write_text(content, encoding="utf-8")
        result = analytics.calculate_progress(p)
        self.assertEqual(result["progress"], 100)
        self.assertEqual(result["status"], "complete")

    def test_malformed_binary_input_does_not_crash(self):
        p = self.temp_dir / "CONTEXT.md"
        p.write_bytes(b"\x00\x01\x02\xff\xfe malformed \x80\x99 bytes here")
        result = analytics.calculate_progress(p)
        self.assertIn("status", result)
        self.assertIn("progress", result)
        self.assertEqual(result["progress"], 0)
        self.assertEqual(result["done"], 0)

    def test_oversized_file_is_error(self):
        p = self.temp_dir / "CONTEXT.md"
        p.write_bytes(b"x" * (1024 * 1024 + 1))
        result = analytics.calculate_progress(p)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["current_phase"], "File too large")
        self.assertEqual(result["progress"], 0)

    # --- load_analytics / save_analytics / track_project ---

    def test_load_analytics_missing_file_default(self):
        data = analytics.load_analytics()
        self.assertEqual(data, {"projects": [], "version": "1.0"})

    def test_load_analytics_malformed_json_default(self):
        self.analytics_file.write_text("{ not json", encoding="utf-8")
        data = analytics.load_analytics()
        self.assertEqual(data, {"projects": [], "version": "1.0"})

    def test_load_analytics_valid_data(self):
        self.analytics_file.write_text(
            json.dumps({"projects": [{"project_name": "A"}], "version": "1.0"}),
            encoding="utf-8",
        )
        data = analytics.load_analytics()
        self.assertEqual(data["version"], "1.0")
        self.assertEqual(len(data["projects"]), 1)

    def test_save_and_load_round_trip(self):
        data = {
            "projects": [{"project_name": "RoundTrip", "project_types": ["personal-web"]}],
            "version": "1.0",
        }
        self.assertTrue(analytics.save_analytics(data))
        loaded = analytics.load_analytics()
        self.assertEqual(loaded["projects"][0]["project_name"], "RoundTrip")

    def test_track_project_persists_and_returns_id(self):
        pid = analytics.track_project({
            "project_name": "Tracked",
            "project_path": str(self.temp_dir),
            "project_types": ["e-commerce", "fullstack"],
            "tech_stack": {"frontend": "Next.js 14 + TypeScript"},
            "environment": {"os": "Windows"},
        })
        self.assertIsInstance(pid, str)
        self.assertTrue(pid)
        loaded = analytics.load_analytics()
        self.assertEqual(len(loaded["projects"]), 1)
        stored = loaded["projects"][0]
        self.assertEqual(stored["project_name"], "Tracked")
        self.assertEqual(stored["project_types"], ["e-commerce", "fullstack"])
        self.assertEqual(stored["tech_stack"], {"frontend": "Next.js 14 + TypeScript"})


if __name__ == "__main__":
    unittest.main()

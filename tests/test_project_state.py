#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M4 portable state tests (state.yaml).

Coverage:
  - state.yaml is generated with schema_version 1.0.0
  - initial phase is planning (no false development/production claims)
  - no fake completed tasks for a freshly generated project
  - pointers (decisions/handoff) valid
  - branch/worktree behavior: no Git -> canonical_branch absent honestly
  - state round-trip (write -> read -> equivalent)
  - reader rejects malformed structure clearly

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

from core.state import (
    CANONICAL_STATE_DIR,
    STATE_YAML,
    ProjectState,
    TaskEntry,
    build_initial_state,
    read_state,
    write_state,
)


class TestProjectState(unittest.TestCase):
    def test_build_initial_state_is_planning(self):
        state = build_initial_state("my-app", phase="planning", focus="")
        self.assertEqual(state.schema_version, "1.0.0")
        self.assertEqual(state.phase, "planning")
        self.assertEqual(state.focus, "")
        self.assertEqual(state.active_tasks, [])
        self.assertEqual(state.completed_tasks, [])
        self.assertEqual(state.decisions_pointer, "DECISIONS.md")
        self.assertEqual(state.handoff_pointer, "HANDOFF.md")
        self.assertIsNone(state.canonical_branch)
        self.assertEqual(state.active_worktrees, [])
        self.assertIsNone(state.last_session)

    def test_initial_state_claims_no_fake_work(self):
        state = build_initial_state("my-app")
        self.assertEqual(state.phase, "planning")
        self.assertNotIn("development", state.phase)
        self.assertNotIn("production", state.phase)
        self.assertEqual(len(state.completed_tasks), 0)

    def test_phase_must_be_valid(self):
        with self.assertRaises(ValueError):
            build_initial_state("my-app", phase="deploying-to-mars")

    def test_write_and_read_state(self):
        with tempfile.TemporaryDirectory() as td:
            state = build_initial_state(
                "my-app", phase="planning", focus="Set up project scaffolding",
                canonical_branch=None,
            )
            path = write_state(td, state)
            self.assertTrue(path.exists())
            self.assertEqual(path.parent.name, CANONICAL_STATE_DIR)
            self.assertEqual(path.name, STATE_YAML)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], "1.0.0")
            self.assertEqual(data["state"]["phase"], "planning")
            self.assertEqual(data["state"]["completed_tasks"], [])
            read_back = read_state(path)
            self.assertEqual(read_back.phase, "planning")
            self.assertEqual(read_back.focus, "Set up project scaffolding")
            self.assertIsNone(read_back.canonical_branch)

    def test_state_round_trip_equivalence(self):
        with tempfile.TemporaryDirectory() as td:
            task = TaskEntry(id="setup-auth", title="Configure auth", status="in-progress")
            completed = ProjectState if False else None
            state = ProjectState(
                phase="architecture",
                focus="Design stack",
                active_tasks=[task],
                completed_tasks=[],
                canonical_branch="main",
                active_worktrees=[],
                last_session=None,
            )
            read_back = read_state(write_state(td, state))
            self.assertEqual(read_back, state)
            self.assertEqual(read_back.active_tasks[0].id, "setup-auth")

    def test_reader_rejects_malformed_state(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / CANONICAL_STATE_DIR / STATE_YAML
            bad.parent.mkdir(parents=True, exist_ok=True)
            bad.write_text("{ not valid json", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_state(bad)

            bad2 = Path(td) / CANONICAL_STATE_DIR / STATE_YAML
            bad2.write_text(json.dumps({"schema_version": "9.9.9"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                read_state(bad2)

    def test_no_git_represented_honestly(self):
        """Newly generated project is not a Git repo -> canonical_branch absent."""
        state = build_initial_state("my-app")
        self.assertIsNone(state.canonical_branch)
        self.assertEqual(state.active_worktrees, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

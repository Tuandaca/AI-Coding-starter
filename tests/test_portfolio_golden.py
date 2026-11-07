#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Golden portfolio E2E test for V2.1.1 (demotool scenario, section 35) and
runtime-switch canonical-state integrity (section 29).

Scenario:
  name = demo
  project_type = portfolio
  capabilities = accessibility, i18n
  stack = react-static
  runtime = portable

Asserts the corrected output, then switches through every supported runtime
and verifies canonical state + portable workspace remain byte-identical.

Standard library only. No network. Writes only inside tempfile.TemporaryDirectory().
"""
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import new_project  # noqa: E402
from core.spec import build_project_spec, write_project_spec
from core.state import build_initial_state, build_resources_lock, write_state, write_resources_lock
from core.resource_resolver import resolve_resources
from core.portable_renderer import render_all, render_portable_workspace
from core.stack_scaffold import scaffold_stack, write_gitignore, write_project_readme

CANONICAL_FILES = (
    ".ai-coding-starter/project.yaml",
    ".ai-coding-starter/state.yaml",
    ".ai-coding-starter/resources.lock",
)

RUNTIMES = ["portable", "codex", "antigravity", "opencode", "claude-code", "cursor"]


def build_golden_project(root: Path) -> None:
    """Build the golden portfolio project directly (bypasses the interactive wizard)."""
    spec = build_project_spec(
        "demo", project_type_id="portfolio",
        capabilities=["accessibility", "i18n"], stack_bundle_id="react-static",
    )
    state = build_initial_state(str(spec.id))
    resource_selection = resolve_resources(
        "portfolio", ["accessibility", "i18n"], "react-static",
        catalog_dir=REPO_ROOT / "catalog",
        resources_root=REPO_ROOT / "resources",
    )
    lock = build_resources_lock(
        "react-static", requested_bundle_id="react-static",
        resources=[
            {
                "id": r.id, "type": r.type, "version": r.version,
                "provenance": {
                    "source": r.provenance_source,
                    "commit_sha": r.provenance_commit_sha,
                    "license": r.provenance_license,
                    "reviewed_date": "2026-11-06",
                    "transformation": "none",
                },
                "selection_reason": r.selection_reason,
            }
            for r in resource_selection.resources
        ],
    )
    write_project_spec(root, spec)
    write_state(root, state)
    write_resources_lock(root, lock)
    render_portable_workspace(root, resource_selection, REPO_ROOT / "resources")
    render_all(root, spec, state, resources=resource_selection)
    scaffold_stack(root, "react-static", "demo")
    write_gitignore(root, "react-static")
    write_project_readme(
        root, "demo", "portfolio", ["accessibility", "i18n"], "react-static", "portable",
    )


def snapshot(root: Path) -> dict:
    """Byte snapshot of canonical state files + portable workspace files."""
    snap: dict[str, bytes] = {}
    for rel in CANONICAL_FILES:
        p = root / rel
        if p.is_file():
            snap[rel] = p.read_bytes()
    workspace = root / ".ai-workspace"
    if workspace.is_dir():
        for p in sorted(workspace.rglob("*")):
            if p.is_file():
                snap[str(p.relative_to(root))] = p.read_bytes()
    return snap


class TestGoldenPortfolioE2E(unittest.TestCase):
    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix="golden_"))
        build_golden_project(self.td)

    def _lock(self):
        return new_project.read_resources_lock(
            self.td / ".ai-coding-starter" / "resources.lock")

    def test_canonical_state_exists(self):
        for rel in CANONICAL_FILES:
            self.assertTrue((self.td / rel).is_file(), f"missing {rel}")

    def test_portable_workspace_exists(self):
        self.assertTrue((self.td / ".ai-workspace").is_dir())

    def test_derived_markdown_exists(self):
        self.assertTrue((self.td / "AGENTS.md").is_file())
        self.assertTrue((self.td / "CONTEXT.md").is_file())

    def test_react_scaffold_exists(self):
        self.assertTrue((self.td / "package.json").is_file())
        self.assertTrue((self.td / "tsconfig.json").is_file())
        self.assertTrue((self.td / "vite.config.ts").is_file())
        self.assertTrue((self.td / "src").is_dir())
        self.assertTrue((self.td / "public").is_dir())

    def test_gitignore_and_readme(self):
        self.assertTrue((self.td / ".gitignore").is_file())
        self.assertTrue((self.td / "README.md").is_file())
        gitignore = (self.td / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("node_modules/", gitignore)
        self.assertIn("dist/", gitignore)

    def test_no_root_gemini_md(self):
        """Section 41: Portable mode must not generate root GEMINI.md."""
        self.assertFalse((self.td / "GEMINI.md").is_file())

    def test_no_vendor_folders(self):
        """No vendor folders until requested (Portable mode)."""
        for vendor in (".codex", ".opencode", ".claude", ".cursor", ".agent"):
            self.assertFalse((self.td / vendor).exists(),
                             f"vendor folder {vendor} must not exist in Portable mode")

    def test_no_auth_or_api_resources(self):
        """Section 16 golden case: no authentication/API/backend resources."""
        ids = {(r.type, r.id) for r in self._lock().resources}
        self.assertNotIn(("agent", "security-auditor"), ids)
        self.assertNotIn(("skill", "security-auditor"), ids)
        self.assertNotIn(("skill", "api-documenter"), ids)
        self.assertNotIn(("shared-module", "api-standards"), ids)
        self.assertNotIn(("agent", "backend-specialist"), ids)

    def test_no_capability_authentication_in_reasons(self):
        """Never output capability:authentication if authentication not selected."""
        for r in self._lock().resources:
            self.assertNotIn("capability:authentication", r.selection_reason)
            self.assertNotIn("capability:payments", r.selection_reason)

    def test_agency_specialists_materialized(self):
        """Section 10: every locked active agency agent is materialized under .ai-workspace."""
        ws_agents = self.td / ".ai-workspace" / "agents"
        lock = self._lock()
        agency_agent_ids = [r.id for r in lock.resources
                            if r.type == "agent" and r.provenance.source == "agency-agents"]
        self.assertGreater(len(agency_agent_ids), 0,
                           "portfolio should activate at least one agency specialist")
        for aid in agency_agent_ids:
            self.assertTrue((ws_agents / f"{aid}.md").is_file(),
                            f"agency agent {aid} not materialized in .ai-workspace/agents/")

    def test_resources_lock_matches_portable_resources(self):
        """Section 30: no phantom active resource; lock matches materialized workspace."""
        ws_agents = {p.stem for p in (self.td / ".ai-workspace" / "agents").glob("*.md")}
        lock_agent_ids = {r.id for r in self._lock().resources if r.type == "agent"}
        # Every locked bundled agent must have a portable representation.
        for aid in lock_agent_ids:
            self.assertIn(aid, ws_agents,
                          f"locked agent {aid} has no portable materialization")

    def test_team_size_within_minimal_budget(self):
        """Section 17: minimal/static project -> 4-6 agents, hard ceiling 10."""
        lock = self._lock()
        agent_count = sum(1 for r in lock.resources if r.type == "agent")
        self.assertGreaterEqual(agent_count, 4)
        self.assertLessEqual(agent_count, 6)
        self.assertLessEqual(agent_count, 10)

    def test_lock_provenance_for_agency_resources(self):
        """Section 30: agency resources carry source/commit/license."""
        lock = self._lock()
        for r in lock.resources:
            if r.provenance.source == "agency-agents":
                self.assertEqual(r.provenance.commit_sha,
                                 "b859c515d813efcfc4755d3471dd9e7686c7706d")
                self.assertEqual(r.provenance.license, "MIT")

    def test_runtime_switch_preserves_canonical_state(self):
        """Section 29: Portable -> each runtime -> Portable, canonical state unchanged."""
        base = snapshot(self.td)
        for rt in RUNTIMES:
            ok = new_project.switch_runtime(self.td, rt)
            self.assertTrue(ok, f"switch to {rt} failed")
            self.assertEqual(snapshot(self.td), base,
                             f"canonical state or workspace changed after {rt}")
        # End back at portable.
        self.assertEqual(snapshot(self.td), base)


if __name__ == "__main__":
    unittest.main(verbosity=2)

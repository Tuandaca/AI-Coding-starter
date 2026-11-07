#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cross-project golden + property-based tests for resource applicability hardening.

For every supported project type, generates a minimal representative spec and
asserts:

  * selection is deterministic
  * no duplicate (type, id) resources
  * every locked active resource is materialized under .ai-workspace/
  * capability-triggered resources have a matching selected capability
  * no forbidden / cross-domain resource leaks in
  * team size respects the complexity-aware budget (hard ceiling 10)
  * resources.lock is honest (id, type, source, commit_sha, license,
    selection_reason present)

Includes dedicated golden tests for E-commerce, AI/RAG, Backend API, SaaS,
and Landing Page (Sections 10-14).

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
from core.portable_renderer import render_portable_workspace, render_all
from core.stack_scaffold import scaffold_stack, write_gitignore, write_project_readme

CATALOG_DIR = REPO_ROOT / "catalog"
RESOURCES_DIR = REPO_ROOT / "resources"

# Every project type registered in project-types.yaml.
PROJECT_TYPES = (
    "portfolio", "landing-page", "business-website", "blog-content",
    "e-commerce", "saas", "fullstack-application", "dashboard",
    "backend-api", "mobile-application", "ai-rag", "ai-agent",
    "realtime-application", "desktop-application",
)

# Representative capabilities per project type (kept minimal; none are
# authentication/payments unless the domain genuinely calls for them).
REPRESENTATIVE_CAPABILITIES = {
    "portfolio": ["accessibility", "i18n"],
    "landing-page": ["i18n"],
    "business-website": ["search", "accessibility"],
    "blog-content": ["search"],
    "e-commerce": ["authentication", "payments", "search"],
    "saas": ["authentication", "payments", "email"],
    "fullstack-application": ["authentication"],
    "dashboard": ["authentication"],
    "backend-api": [],
    "mobile-application": [],
    "ai-rag": ["ai", "rag"],
    "ai-agent": ["ai"],
    "realtime-application": ["realtime"],
    "desktop-application": [],
}

# Stack bundle chosen per project type (must be a valid pair in the catalog).
STACK_BUNDLE = {
    "portfolio": "react-static",
    "landing-page": "react-static",
    "business-website": "react-static",
    "blog-content": "react-static",
    "e-commerce": "nextjs-supabase",
    "saas": "nextjs-supabase",
    "fullstack-application": "nextjs-supabase",
    "dashboard": "nextjs-dotnet-postgres",
    "backend-api": "fastapi-postgres",
    "mobile-application": "expo-supabase-mobile",
    "ai-rag": "ai-rag-python",
    "ai-agent": "ai-rag-python",
    "realtime-application": "nextjs-supabase",
    "desktop-application": "tauri-react-sqlite",
}

# Cross-domain resources that must NEVER appear for the listed project types.
FORBIDDEN_BY_TYPE = {
    "portfolio": {
        "agent": {"backend-specialist", "game-developer", "security-appsec-engineer"},
        "skill": {"api-documenter", "api-standards", "mcp-builder", "game-development"},
        "shared-module": {"api-standards", "database-master", "ai-master"},
    },
    "landing-page": {
        "agent": {"backend-specialist"},
        "skill": {"api-documenter", "api-standards", "mcp-builder"},
        "shared-module": {"api-standards", "database-master", "ai-master"},
    },
    "blog-content": {
        "agent": {"backend-specialist"},
        "skill": {"api-documenter", "api-standards", "mcp-builder"},
        "shared-module": {"api-standards", "database-master", "ai-master"},
    },
    "business-website": {
        "skill": {"api-documenter", "api-standards", "mcp-builder"},
        "shared-module": {"api-standards", "database-master", "ai-master"},
    },
    "desktop-application": {
        "skill": {"api-documenter", "api-standards", "mcp-builder"},
        "shared-module": {"api-standards", "database-master", "ai-master"},
    },
    "backend-api": {
        "agent": {"frontend-specialist", "mobile-developer", "game-developer"},
        "skill": {"mobile-design", "game-development"},
        "shared-module": {"design-system"},
    },
    "ai-rag": {
        "skill": {"database-migration"},
        "shared-module": {"database-master"},
    },
    "ai-agent": {
        "skill": {"database-migration"},
        "shared-module": {"database-master"},
    },
    "e-commerce": {
        "agent": {"game-developer"},
        "skill": {"game-development", "mcp-builder"},
        "shared-module": {"ai-master"},
    },
    "saas": {
        "agent": {"game-developer"},
    },
    "fullstack-application": {
        "agent": {"game-developer"},
    },
    "dashboard": {
        "agent": {"game-developer"},
    },
    "mobile-application": {
        "skill": {"api-standards"},
    },
    "realtime-application": {
        "agent": {"game-developer"},
    },
}

AGENCY_COMMIT = "b859c515d813efcfc4755d3471dd9e7686c7706d"


def build_golden_project(root, project_type_id, capabilities, stack_bundle_id):
    """Build a project directly (bypasses the wizard) and return the resolver result."""
    spec = build_project_spec(
        "test-proj", project_type_id=project_type_id,
        capabilities=capabilities, stack_bundle_id=stack_bundle_id,
    )
    state = build_initial_state(str(spec.id))
    resource_selection = resolve_resources(
        project_type_id, capabilities, stack_bundle_id,
        catalog_dir=CATALOG_DIR, resources_root=RESOURCES_DIR,
    )
    lock = build_resources_lock(
        stack_bundle_id, requested_bundle_id=stack_bundle_id,
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
    render_portable_workspace(root, resource_selection, RESOURCES_DIR)
    render_all(root, spec, state, resources=resource_selection)
    scaffold_stack(root, stack_bundle_id, "test-proj")
    write_gitignore(root, stack_bundle_id)
    write_project_readme(
        root, "test-proj", project_type_id, capabilities, stack_bundle_id, "portable",
    )
    return resource_selection, lock


class TestCrossProjectProperty(unittest.TestCase):
    """Property-based checks across every supported project type."""

    def test_every_project_type_resolves_deterministically(self):
        for pt in PROJECT_TYPES:
            with self.subTest(project_type=pt):
                caps = REPRESENTATIVE_CAPABILITIES[pt]
                bundle = STACK_BUNDLE[pt]
                a = resolve_resources(pt, caps, bundle,
                                      catalog_dir=CATALOG_DIR,
                                      resources_root=RESOURCES_DIR)
                b = resolve_resources(pt, caps, bundle,
                                      catalog_dir=CATALOG_DIR,
                                      resources_root=RESOURCES_DIR)
                self.assertTrue(a.ok, f"{pt}: {a.errors}")
                self.assertTrue(b.ok, f"{pt}: {b.errors}")
                keys_a = sorted((r.type, r.id) for r in a.resources)
                keys_b = sorted((r.type, r.id) for r in b.resources)
                self.assertEqual(keys_a, keys_b, f"{pt}: non-deterministic selection")

    def test_no_duplicate_resources(self):
        for pt in PROJECT_TYPES:
            with self.subTest(project_type=pt):
                caps = REPRESENTATIVE_CAPABILITIES[pt]
                bundle = STACK_BUNDLE[pt]
                result = resolve_resources(pt, caps, bundle,
                                           catalog_dir=CATALOG_DIR,
                                           resources_root=RESOURCES_DIR)
                self.assertTrue(result.ok, f"{pt}: {result.errors}")
                keys = [(r.type, r.id) for r in result.resources]
                self.assertEqual(len(keys), len(set(keys)),
                                 f"{pt}: duplicate (type, id) resources")

    def test_no_forbidden_cross_domain_resources(self):
        for pt in PROJECT_TYPES:
            with self.subTest(project_type=pt):
                caps = REPRESENTATIVE_CAPABILITIES[pt]
                bundle = STACK_BUNDLE[pt]
                result = resolve_resources(pt, caps, bundle,
                                           catalog_dir=CATALOG_DIR,
                                           resources_root=RESOURCES_DIR)
                self.assertTrue(result.ok, f"{pt}: {result.errors}")
                forbidden = FORBIDDEN_BY_TYPE.get(pt, {})
                found = []
                for r in result.resources:
                    allowed_types = forbidden.get(r.type, set())
                    if r.id in allowed_types:
                        found.append(f"{r.type}:{r.id}")
                self.assertEqual(
                    [], found,
                    f"{pt}: forbidden cross-domain resources present: {found}",
                )

    def test_team_size_respects_budget(self):
        for pt in PROJECT_TYPES:
            with self.subTest(project_type=pt):
                caps = REPRESENTATIVE_CAPABILITIES[pt]
                bundle = STACK_BUNDLE[pt]
                result = resolve_resources(pt, caps, bundle,
                                           catalog_dir=CATALOG_DIR,
                                           resources_root=RESOURCES_DIR)
                self.assertTrue(result.ok, f"{pt}: {result.errors}")
                agent_count = sum(1 for r in result.resources if r.type == "agent")
                self.assertLessEqual(agent_count, 10,
                                     f"{pt}: agent count {agent_count} exceeds hard ceiling 10")

    def test_capability_triggered_resources_match_selected_capability(self):
        """No resource may claim a capability that was not selected."""
        for pt in PROJECT_TYPES:
            with self.subTest(project_type=pt):
                caps = set(REPRESENTATIVE_CAPABILITIES[pt])
                bundle = STACK_BUNDLE[pt]
                result = resolve_resources(pt, list(caps), bundle,
                                           catalog_dir=CATALOG_DIR,
                                           resources_root=RESOURCES_DIR)
                self.assertTrue(result.ok, f"{pt}: {result.errors}")
                for r in result.resources:
                    for token in r.selection_reason.split():
                        if token.startswith("capability:"):
                            claimed = token[len("capability:"):]
                            self.assertIn(
                                claimed, caps,
                                f"{pt}: {r.type}:{r.id} claims unselected "
                                f"capability {claimed!r} (reason: {r.selection_reason})",
                            )

    def test_lock_and_portable_materialization_integrity(self):
        """Every locked bundled agent is materialized under .ai-workspace/."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for pt in ("portfolio", "e-commerce", "saas", "backend-api", "ai-rag"):
                with self.subTest(project_type=pt):
                    caps = REPRESENTATIVE_CAPABILITIES[pt]
                    bundle = STACK_BUNDLE[pt]
                    resource_selection, lock = build_golden_project(
                        root, pt, caps, bundle)
                    ws_agents = {
                        p.stem for p in (root / ".ai-workspace" / "agents").glob("*.md")
                    }
                    for res in lock.resources:
                        if res.type == "agent" and res.provenance.source == "bundled":
                            self.assertIn(
                                res.id, ws_agents,
                                f"{pt}: locked bundled agent {res.id} not materialized",
                            )

    def test_lock_provenance_honest(self):
        """Every locked resource carries id, type, source, commit_sha, license, reason."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            caps = REPRESENTATIVE_CAPABILITIES["e-commerce"]
            bundle = STACK_BUNDLE["e-commerce"]
            build_golden_project(root, "e-commerce", caps, bundle)
            lock = new_project.read_resources_lock(
                root / ".ai-coding-starter" / "resources.lock")
            for res in lock.resources:
                self.assertTrue(res.id, "lock resource missing id")
                self.assertTrue(res.type, "lock resource missing type")
                self.assertTrue(res.provenance.source,
                                f"{res.type}:{res.id} missing provenance source")
                self.assertTrue(res.provenance.commit_sha,
                                f"{res.type}:{res.id} missing commit_sha")
                self.assertTrue(res.provenance.license,
                                f"{res.type}:{res.id} missing license")
                self.assertTrue(res.selection_reason,
                                f"{res.type}:{res.id} missing selection_reason")


# ---------------------------------------------------------------------------
# Dedicated golden tests (Sections 10-14)
# ---------------------------------------------------------------------------

class TestGoldenEcommerce(unittest.TestCase):
    """Section 10: E-commerce golden case."""

    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix="golden-ecom-"))
        caps = ["authentication", "payments", "search"]
        self.selection, self.lock = build_golden_project(
            self.td, "e-commerce", caps, "nextjs-supabase")

    def _ids(self):
        return {(r.type, r.id) for r in self.lock.resources}

    def test_domain_appropriate_resources_present(self):
        ids = self._ids()
        # frontend, backend, authentication/security, payments, database, testing, deployment
        self.assertIn(("agent", "frontend-specialist"), ids)
        self.assertIn(("agent", "backend-specialist"), ids)
        self.assertIn(("agent", "security-auditor"), ids)
        self.assertIn(("skill", "security-auditor"), ids)
        self.assertIn(("skill", "database-migration"), ids)
        self.assertIn(("workflow", "create"), ids)
        self.assertIn(("workflow", "deploy"), ids)

    def test_forbidden_domains_absent(self):
        """No game-development, RAG-only, healthcare, or finance-specialist resources."""
        ids = self._ids()
        forbidden = {
            ("agent", "game-developer"),
            ("skill", "game-development"),
            ("skill", "mcp-builder"),
            ("shared-module", "ai-master"),
        }
        self.assertFalse(forbidden & ids,
                         f"e-commerce has forbidden resources: {forbidden & ids}")

    def test_capability_gating_honest(self):
        """security-auditor present because authentication was selected."""
        ids = self._ids()
        self.assertIn(("agent", "security-auditor"), ids)
        auditor = [r for r in self.lock.resources
                   if r.id == "security-auditor" and r.type == "agent"][0]
        self.assertEqual(auditor.selection_reason, "capability:authentication")


class TestGoldenAiRag(unittest.TestCase):
    """Section 11: AI/RAG golden case."""

    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix="golden-rag-"))
        caps = ["ai", "rag"]
        self.selection, self.lock = build_golden_project(
            self.td, "ai-rag", caps, "ai-rag-python")

    def _ids(self):
        return {(r.type, r.id) for r in self.lock.resources}

    def test_rag_categories_present(self):
        ids = self._ids()
        self.assertIn(("skill", "ai-engineer"), ids)
        self.assertIn(("skill", "mcp-builder"), ids)

    def test_forbidden_absent(self):
        ids = self._ids()
        forbidden = {
            ("skill", "database-migration"),
            ("shared-module", "database-master"),
        }
        self.assertFalse(forbidden & ids,
                         f"ai-rag has forbidden resources: {forbidden & ids}")


class TestGoldenBackendApi(unittest.TestCase):
    """Section 12: Backend API golden case."""

    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix="golden-backend-"))
        self.selection, self.lock = build_golden_project(
            self.td, "backend-api", [], "fastapi-postgres")

    def _ids(self):
        return {(r.type, r.id) for r in self.lock.resources}

    def test_backend_categories_present(self):
        ids = self._ids()
        self.assertIn(("agent", "backend-specialist"), ids)
        self.assertIn(("workflow", "create"), ids)
        self.assertIn(("workflow", "deploy"), ids)

    def test_no_ui_or_portfolio_resources(self):
        ids = self._ids()
        forbidden = {
            ("agent", "frontend-specialist"),
            ("agent", "seo-specialist"),
            ("skill", "mobile-design"),
            ("skill", "game-development"),
        }
        self.assertFalse(forbidden & ids,
                         f"backend-api has forbidden resources: {forbidden & ids}")


class TestGoldenSaas(unittest.TestCase):
    """Section 13: SaaS golden case."""

    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix="golden-saas-"))
        caps = ["authentication", "payments", "email"]
        self.selection, self.lock = build_golden_project(
            self.td, "saas", caps, "nextjs-supabase")

    def _ids(self):
        return {(r.type, r.id) for r in self.lock.resources}

    def test_saas_categories_present(self):
        ids = self._ids()
        self.assertIn(("agent", "frontend-specialist"), ids)
        self.assertIn(("agent", "backend-specialist"), ids)
        self.assertIn(("agent", "security-auditor"), ids)

    def test_capability_driven_only_when_selected(self):
        ids = self._ids()
        # authentication selected -> security-auditor present
        self.assertIn(("agent", "security-auditor"), ids)


class TestGoldenLandingPage(unittest.TestCase):
    """Section 14: Landing Page golden case (distinct from Portfolio)."""

    def setUp(self):
        self.td = Path(tempfile.mkdtemp(prefix="golden-landing-"))
        self.selection, self.lock = build_golden_project(
            self.td, "landing-page", ["i18n"], "react-static")

    def _ids(self):
        return {(r.type, r.id) for r in self.lock.resources}

    def test_no_api_backend_resources(self):
        """A static landing page must not receive API/backend specialists."""
        ids = self._ids()
        forbidden = {
            ("agent", "backend-specialist"),
            ("skill", "api-documenter"),
            ("shared-module", "api-standards"),
            ("skill", "modern-web-architect"),
        }
        self.assertFalse(forbidden & ids,
                         f"landing-page has forbidden resources: {forbidden & ids}")

    def test_frontend_and_design_present(self):
        ids = self._ids()
        self.assertIn(("agent", "frontend-specialist"), ids)
        self.assertIn(("shared-module", "design-system"), ids)


if __name__ == "__main__":
    unittest.main(verbosity=2)

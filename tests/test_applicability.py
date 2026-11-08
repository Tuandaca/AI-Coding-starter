#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Section 4 / Section 5: resource applicability engine tests.

Direct unit tests for every applicability axis:

  * project_types_include / project_types_exclude
  * capabilities_any / capabilities_all / capabilities_none
  * stack_tags_any / stack_tags_all (incl. explainable diagnostics)
  * task_tags_any (declared unsupported at project level)
  * requires / conflicts_with (see resources selected earlier in resolution)
  * global resources: exempt from project-type/capability/stack gating, but
    NOT exempt from dependency/conflict safety constraints
  * no metadata -> eligible by default (backward compatibility)
  * canonical catalog loads and is keyed by (type, id)

Standard library only. No network.
"""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.applicability import (
    Applicability,
    ApplicabilityContext,
    ApplicabilityCatalog,
    is_resource_eligible,
)


def ctx(
    project_type="saas",
    capabilities=None,
    stack_tags=None,
    task_tags=None,
    selected=None,
) -> ApplicabilityContext:
    return ApplicabilityContext(
        project_type=project_type,
        capabilities=frozenset(capabilities or []),
        stack_tags=frozenset(stack_tags or []),
        task_tags=frozenset(task_tags or []),
        selected=frozenset(selected or []),
    )


class TestApplicabilityAxes(unittest.TestCase):
    """One test per applicability axis, with explainable reasons."""

    def test_project_types_include_or(self):
        app = Applicability(
            id="frontend-specialist", type="agent",
            project_types_include=frozenset({"portfolio", "landing-page"}),
        )
        self.assertTrue(app.is_eligible(ctx("portfolio", [])))
        self.assertTrue(app.is_eligible(ctx("landing-page", [])))
        self.assertFalse(app.is_eligible(ctx("saas", [])))

    def test_project_types_exclude_wins_over_include(self):
        app = Applicability(
            id="backend-specialist", type="agent",
            project_types_include=frozenset({"saas", "backend-api"}),
            project_types_exclude=frozenset({"backend-api"}),
        )
        self.assertTrue(app.is_eligible(ctx("saas", [])))
        # Exclusion wins even though the type is also in include.
        self.assertFalse(app.is_eligible(ctx("backend-api", [])))

    def test_capabilities_any_or(self):
        app = Applicability(
            id="security-auditor", type="agent",
            capabilities_any=frozenset({"authentication", "authorization"}),
        )
        self.assertTrue(app.is_eligible(ctx("saas", {"authentication"})))
        self.assertTrue(app.is_eligible(ctx("saas", {"authorization"})))
        self.assertTrue(app.is_eligible(ctx("saas", {"authentication", "authorization"})))
        self.assertFalse(app.is_eligible(ctx("saas", {"payments"})))

    def test_capabilities_all_and(self):
        app = Applicability(
            id="resilient-backend", type="skill",
            capabilities_all=frozenset({"authentication", "authorization"}),
        )
        self.assertFalse(app.is_eligible(ctx("saas", {"authentication"})))
        self.assertFalse(app.is_eligible(ctx("saas", {"authorization"})))
        self.assertTrue(app.is_eligible(ctx("saas", {"authentication", "authorization"})))

    def test_capabilities_none_forbid(self):
        app = Applicability(
            id="legacy-mode", type="skill",
            capabilities_none=frozenset({"ai"}),
        )
        self.assertTrue(app.is_eligible(ctx("saas", {"authentication"})))
        self.assertFalse(app.is_eligible(ctx("ai-rag", {"ai", "rag"})))

    def test_stack_tags_any_or(self):
        app = Applicability(
            id="mobile-developer", type="agent",
            stack_tags_any=frozenset({"expo-supabase-mobile"}),
        )
        self.assertTrue(app.is_eligible(ctx("mobile-application", [], stack_tags=["expo-supabase-mobile"])))
        self.assertFalse(app.is_eligible(ctx("mobile-application", [], stack_tags=["react-static"])))

    def test_stack_tags_all_and_with_diagnostic(self):
        app = Applicability(
            id="polyglot-backend", type="skill",
            stack_tags_all=frozenset({"postgresql", "redis"}),
        )
        self.assertTrue(app.is_eligible(ctx("saas", [], stack_tags=["postgresql", "redis"])))

        result = is_resource_eligible(app, ctx("saas", [], stack_tags=["postgresql"]))
        self.assertFalse(result.applicable)
        reason = is_resource_eligible(app, ctx("saas", [], stack_tags=["postgresql"])).reason
        self.assertIn("requires all stack tags", reason)
        self.assertIn("postgresql", reason)
        self.assertIn("redis", reason)

    def test_task_tags_unsupported_at_project_level(self):
        """task_tags_any never fires because project-level context passes
        an empty task_tags set (declared unsupported for project-level
        resolution)."""
        app = Applicability(
            id="ux-specialist", type="agent",
            task_tags_any=frozenset({"design", "ux"}),
        )
        # Even though the resource declares task tags, a project-level
        # context carries no task tags, so it is ineligible.
        result = is_resource_eligible(
            app, ctx("portfolio", [], task_tags=[])
        )
        self.assertFalse(result.applicable)
        self.assertIn("task tag", result.reason)

    def test_requires_and_sees_selected_resources(self):
        app = Applicability(
            id="mcp-builder", type="skill",
            requires=frozenset({("skill", "ai-engineer")}),
        )
        # Requirement not yet selected -> ineligible.
        self.assertFalse(
            app.is_eligible(ctx("ai-rag", {"rag"}, selected=[]))
        )
        # Requirement selected earlier in the same resolution -> eligible.
        self.assertTrue(
            app.is_eligible(
                ctx("ai-rag", {"rag"}, selected=[("skill", "ai-engineer")])
            )
        )
        result = is_resource_eligible(
            app, ctx("ai-rag", {"rag"}, selected=[])
        )
        self.assertFalse(result.applicable)
        self.assertIn("requires already-selected", result.reason)

    def test_conflicts_with_or_forbid(self):
        app = Applicability(
            id="database-master", type="shared-module",
            conflicts_with=frozenset({("shared-module", "ai-master")}),
        )
        self.assertTrue(
            app.is_eligible(ctx("backend-api", {"payments"}, selected=[]))
        )
        self.assertFalse(
            app.is_eligible(
                ctx("backend-api", {"payments"},
                    selected=[("shared-module", "ai-master")])
            )
        )
        result = is_resource_eligible(
            app, ctx("backend-api", {"payments"},
                    selected=[("shared-module", "ai-master")])
        )
        self.assertFalse(result.applicable)
        self.assertIn("conflicts with already-selected", result.reason)

    def test_global_exempt_from_project_type_but_not_conflicts(self):
        app = Applicability(
            id="project-planner", type="agent", is_global=True,
            project_types_exclude=frozenset({"not-decided"}),
        )
        # Global: exempt from project-type exclusion.
        self.assertTrue(app.is_eligible(ctx("not-decided", [])))
        self.assertTrue(app.is_eligible(ctx("other", [])))

        # Global: NOT exempt from conflicts_with.
        app_conflict = Applicability(
            id="global-guard", type="agent", is_global=True,
            conflicts_with=frozenset({("skill", "security-auditor")}),
        )
        self.assertFalse(
            app_conflict.is_eligible(
                ctx("saas", [], selected=[("skill", "security-auditor")])
            )
        )

    def test_global_not_exempt_from_requires(self):
        app = Applicability(
            id="global-with-dep", type="workflow", is_global=True,
            requires=frozenset({("agent", "project-planner")}),
        )
        self.assertFalse(app.is_eligible(ctx("saas", [], selected=[])))
        self.assertTrue(
            app.is_eligible(
                ctx("saas", [], selected=[("agent", "project-planner")])
            )
        )

    def test_no_metadata_eligible_by_default(self):
        result = is_resource_eligible(None, ctx("does-not-exist", []))
        self.assertTrue(result.applicable)
        self.assertIn("eligible by default", result.reason)


class TestApplicabilityCatalog(unittest.TestCase):
    """The canonical catalog loads and is keyed by (type, id)."""

    @classmethod
    def setUpClass(cls):
        cls.catalog = ApplicabilityCatalog.load()

    def test_catalog_loads_non_empty(self):
        self.assertGreater(len(self.catalog), 0)

    def test_keyed_by_type_and_id(self):
        key = ("agent", "security-auditor")
        self.assertIn(key, self.catalog)
        app = self.catalog.get("agent", "security-auditor")
        self.assertIsNotNone(app)
        self.assertEqual(app.id, "security-auditor")
        self.assertEqual(app.capabilities_any, frozenset({"authentication", "authorization"}))

    def test_missing_record_returns_none(self):
        self.assertIsNone(self.catalog.get("agent", "does-not-exist"))
        self.assertIsNone(self.catalog.get("skill", "does-not-exist"))

    def test_duplicate_keys_collapsed(self):
        # Each (type, id) appears once in the canonical catalog.
        keys = [(r.type, r.id) for r in self.catalog._records.values()]
        self.assertEqual(len(keys), len(set(keys)), "duplicate (type, id) in applicability catalog")


if __name__ == "__main__":
    unittest.main(verbosity=2)

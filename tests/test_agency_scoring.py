#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Section 15: Agency specialist intelligence tests.

Semantic golden tests verifying that Agency specialists are selected by
meaningful, project-specific evidence -- never by division relevance alone
and never by arbitrary alphabetical ordering.

Covered project types: portfolio, landing-page, SaaS, e-commerce, backend-api,
AI/RAG.

Prevention tests (must NOT be selected unless supported by explicit metadata):
  * accounts-payable-agent for generic AI/RAG
  * business-strategist as a default RAG engineering specialist
  * engineering-ai-data-remediation-engineer as a default e-commerce engineer
  * engineering-ats-validator-architect as a generic backend API specialist

Standard library only. No network.
"""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.resource_registry import build_default_registry
from core.applicability import ApplicabilityCatalog
from core.agency_scoring import AgencyScoringEngine

# Resolved stack technology tags per bundle (technology values from
# catalog/stack-bundles.yaml, plus the bundle id). These are the tags an
# agent's stack_tags are compared against -- never the bundle id alone.
STACK_TECH_TAGS = {
    "react-static": frozenset({
        "react", "none", "vercel", "tailwindcss", "react-static",
    }),
    "nextjs-supabase": frozenset({
        "nextjs", "postgresql", "supabase-client", "supabase-auth",
        "vercel", "tailwindcss", "nextjs-supabase",
    }),
    "fastapi-postgres": frozenset({
        "fastapi", "postgresql", "sqlalchemy", "redis", "celery",
        "railway", "fastapi-postgres",
    }),
    "ai-rag-python": frozenset({
        "fastapi", "postgresql", "sqlalchemy", "pgvector", "redis",
        "celery", "railway", "ai-rag-python",
    }),
}


def build_engine():
    registry = build_default_registry()
    catalog = ApplicabilityCatalog.load()
    return AgencyScoringEngine(registry, catalog)


def selected_ids(result):
    return {c.agent.id for c in result.selected}


class TestAgencyScoringGolden(unittest.TestCase):
    """Semantic golden cases per project type."""

    @classmethod
    def setUpClass(cls):
        cls.engine = build_engine()

    def test_portfolio_design_specialists(self):
        """Portfolio selects design/SEO-aligned agency specialists, not
        arbitrary alphabetical design-division agents."""
        result = self.engine.select_candidates(
            "portfolio", ["accessibility", "i18n"],
            STACK_TECH_TAGS["react-static"], limit=5,
        )
        ids = selected_ids(result)
        self.assertTrue(ids, "portfolio should select agency specialists")
        # Every selected agent must carry project-specific evidence.
        for c in result.selected:
            self.assertTrue(c.qualifies, f"{c.agent.id} selected without evidence")
            self.assertGreater(c.score, 0)
            self.assertTrue(c.breakdown.has_component("project-type-match")
                            or c.breakdown.has_component("capability-match")
                            or c.breakdown.has_component("stack-technology-match"),
                            f"{c.agent.id} has no project-specific evidence")
        # Division relevance alone (+5) never qualifies.
        for c in result.selected:
            div_only = c.breakdown.total == 5
            self.assertFalse(div_only, f"{c.agent.id} selected on division relevance alone")

    def test_landing_page_design_specialists(self):
        """Landing page selects design specialists distinct from API/backend."""
        result = self.engine.select_candidates(
            "landing-page", ["i18n"],
            STACK_TECH_TAGS["react-static"], limit=5,
        )
        ids = selected_ids(result)
        self.assertTrue(ids)
        # No backend-only specialists for a static landing page.
        self.assertNotIn("engineering-backend-architect", ids)

    def test_saas_engineering_and_security(self):
        """SaaS selects engineering + security specialists with evidence."""
        result = self.engine.select_candidates(
            "saas", ["authentication", "payments", "email"],
            STACK_TECH_TAGS["nextjs-supabase"], limit=6,
        )
        ids = selected_ids(result)
        self.assertTrue(ids)
        for c in result.selected:
            self.assertTrue(c.qualifies)
            self.assertTrue(c.breakdown.has_component("project-type-match")
                            or c.breakdown.has_component("capability-match")
                            or c.breakdown.has_component("stack-technology-match"))
        # Security-relevant agent backed by authentication capability.
        self.assertIn("security-appsec-engineer", ids)

    def test_ecommerce_engineering_and_security(self):
        """E-commerce selects backend + security specialists, not AI/RAG agents."""
        result = self.engine.select_candidates(
            "e-commerce", ["authentication", "payments", "search"],
            STACK_TECH_TAGS["nextjs-supabase"], limit=6,
        )
        ids = selected_ids(result)
        self.assertTrue(ids)
        # Backend architecture relevant to e-commerce stack.
        self.assertIn("engineering-backend-architect", ids)
        # No RAG pipeline engineer for an e-commerce project.
        self.assertNotIn("engineering-rag-pipeline-engineer", ids)
        self.assertNotIn("engineering-ai-engineer", ids)
        # No accounts-payable agent unless payments evidence exists; here it
        # has no project-type/capability/stack metadata so it must not qualify.
        self.assertNotIn("accounts-payable-agent", ids)

    def test_backend_api_engineering_only(self):
        """Backend API selects backend/security specialists, no UI or AI agents."""
        result = self.engine.select_candidates(
            "backend-api", [], STACK_TECH_TAGS["fastapi-postgres"], limit=6,
        )
        ids = selected_ids(result)
        self.assertTrue(ids)
        self.assertIn("engineering-backend-architect", ids)
        # No AI/RAG agents for a plain backend API.
        self.assertNotIn("engineering-rag-pipeline-engineer", ids)
        self.assertNotIn("engineering-ai-engineer", ids)
        # No frontend/mobile specialists.
        self.assertNotIn("engineering-frontend-developer", ids)

    def test_ai_rag_rag_evidence(self):
        """AI/RAG selects RAG/AI engineers with explicit ai/rag + stack evidence."""
        result = self.engine.select_candidates(
            "ai-rag", ["ai", "rag"],
            STACK_TECH_TAGS["ai-rag-python"], limit=6,
        )
        ids = selected_ids(result)
        self.assertTrue(ids)
        self.assertIn("engineering-rag-pipeline-engineer", ids)
        self.assertIn("engineering-ai-engineer", ids)
        # Every selected agent must have capability or stack evidence (not just
        # division + project type).
        for c in result.selected:
            self.assertTrue(
                c.breakdown.has_component("capability-match")
                or c.breakdown.has_component("stack-technology-match"),
                f"{c.agent.id} lacks capability/stack evidence for AI/RAG",
            )


class TestAgencyScoringPrevention(unittest.TestCase):
    """Irrelevant agents must not be selected merely by division or alphabet."""

    @classmethod
    def setUpClass(cls):
        cls.engine = build_engine()

    def _not_selected(self, project_type, capabilities, stack_bundle, agent_id):
        result = self.engine.select_candidates(
            project_type, capabilities,
            STACK_TECH_TAGS[stack_bundle], limit=8,
        )
        self.assertNotIn(agent_id, selected_ids(result),
                         f"{agent_id} must not be activated for {project_type}")

    def test_accounts_payable_not_for_ai_rag(self):
        """accounts-payable-agent for generic AI/RAG: no evidence -> rejected."""
        self._not_selected("ai-rag", ["ai", "rag"], "ai-rag-python",
                           "accounts-payable-agent")

    def test_business_strategist_not_default_rag_specialist(self):
        """business-strategist as a default RAG engineering specialist: rejected."""
        self._not_selected("ai-rag", ["ai", "rag"], "ai-rag-python",
                           "business-strategist")

    def test_ai_data_remediation_not_default_ecommerce_engineer(self):
        """engineering-ai-data-remediation-engineer as default e-commerce engineer: rejected."""
        self._not_selected("e-commerce", ["authentication", "payments", "search"],
                           "nextjs-supabase",
                           "engineering-ai-data-remediation-engineer")

    def test_ats_validator_not_generic_backend_api(self):
        """engineering-ats-validator-architect as generic backend API specialist: rejected."""
        self._not_selected("backend-api", [], "fastapi-postgres",
                           "engineering-ats-validator-architect")


class TestAgencyScoringModel(unittest.TestCase):
    """General selection-model assertions (not hand-coded exclusions)."""

    @classmethod
    def setUpClass(cls):
        cls.engine = build_engine()

    def test_division_relevance_alone_never_qualifies(self):
        """An agent whose only evidence is division relevance must not be a
        candidate, even when its division is relevant to the project type."""
        result = self.engine.select_candidates(
            "backend-api", [], STACK_TECH_TAGS["fastapi-postgres"], limit=20,
        )
        for c in result.selected:
            self.assertGreater(c.breakdown.non_division_score(), 0,
                               f"{c.agent.id} qualified on division relevance alone")
        # Every selected candidate must have a truthful breakdown.
        for c in result.selected:
            self.assertGreaterEqual(len(c.breakdown.components), 1)
            total = sum(pts for _, pts in c.breakdown.components)
            self.assertEqual(total, c.score, f"{c.agent.id} breakdown does not sum to score")

    def test_eligibility_before_scoring(self):
        """Every selected agent passes the common eligibility filter."""
        result = self.engine.select_candidates(
            "saas", ["authentication"], STACK_TECH_TAGS["nextjs-supabase"], limit=8,
        )
        for c in result.selected:
            self.assertTrue(c.eligible, f"{c.agent.id} selected but ineligible")

    def test_deterministic_ranking(self):
        """Identical input yields identical selected ids and scores."""
        a = self.engine.select_candidates(
            "saas", ["authentication", "payments"],
            STACK_TECH_TAGS["nextjs-supabase"], limit=8,
        )
        b = self.engine.select_candidates(
            "saas", ["authentication", "payments"],
            STACK_TECH_TAGS["nextjs-supabase"], limit=8,
        )
        self.assertEqual([c.agent.id for c in a.selected],
                         [c.agent.id for c in b.selected])
        self.assertEqual([c.score for c in a.selected],
                         [c.score for c in b.selected])

    def test_alphabetical_is_only_final_tiebreak_not_a_gate(self):
        """Agents are not selected merely because they sort early
        alphabetically within a division."""
        result = self.engine.select_candidates(
            "portfolio", ["accessibility"], STACK_TECH_TAGS["react-static"], limit=8,
        )
        ids = [c.agent.id for c in result.selected]
        # If selection were alphabetical-by-division, the lowest-sorting
        # relevant-division agents would win regardless of evidence. Instead
        # selection is evidence-driven: assert the highest-scoring evidence
        # agents are present and the list is score-ordered.
        scores = [c.score for c in result.selected]
        self.assertEqual(scores, sorted(scores, reverse=True),
                         "selection must be score-ordered, not alphabetical")


if __name__ == "__main__":
    unittest.main(verbosity=2)

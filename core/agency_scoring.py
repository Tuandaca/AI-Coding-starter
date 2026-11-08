"""
Agency specialist intelligence (Section 15).

Selects and scores Agency agents for a project context. An Agency agent may
become an activation candidate ONLY when there is meaningful, project-specific
evidence. Division relevance may increase a score, but it must never be the
sole reason a normal project automatically activates an agent.

Pipeline (Section 4), applied to every Agency agent:

    ELIGIBILITY FILTER  ->  EVIDENCE THRESHOLD  ->  EXPLAINABLE SCORING  ->  RANKING

1. ELIGIBILITY FILTER: the common applicability/eligibility filter
   (core/applicability.py, is_resource_eligible) is applied first. An
   ineligible Agent agent never enters the ranking stage. This invariant
   applies equally to bundled agents, Agency agents, skills, rules, workflows,
   scripts, shared modules, and templates.
2. EVIDENCE THRESHOLD: a candidate must carry at least one non-division
   evidence component (explicit project-type match, capability match,
   stack/technology match, specialty/task match, or explicit execution-pack
   core role). Division relevance alone (+5) never qualifies an agent.
3. EXPLAINABLE SCORING: every score component is itemized in a truthful
   breakdown. No component is claimed unless it is actually evaluated.
4. RANKING: descending score; agent id is the final deterministic tie-break.

This module is intentionally isolated from core/resource_resolver.py. The Lead
integrator wires it into the resolver pipeline. Agency agents are NOT
special-cased around the eligibility layer.

Standard library only. No network. No LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from core.applicability import (
    ApplicabilityCatalog,
    ApplicabilityContext,
    is_resource_eligible,
)
from core.resource_registry import CanonicalResourceRef, ResourceRegistry


# ---------------------------------------------------------------------------
# Evidence threshold constants
# ---------------------------------------------------------------------------

# A candidate must accumulate at least this much non-division evidence to be
# eligible for activation. Division relevance (DIVISION_RELEVANCE) is a bonus
# only and never counts toward this threshold.
MIN_EVIDENCE_SCORE = 30

EXECUTION_PACK_CORE_ROLE = 100   # explicit execution-pack core role
PROJECT_TYPE_MATCH = 40          # agent declares the project type
CAPABILITY_MATCH = 30            # at least one selected capability matches
STACK_TECHNOLOGY_MATCH = 20      # agent stack_tags match resolved stack tags
SPECIALTY_TAG_MATCH = 10         # agent specialties/tags match task context
DIVISION_RELEVANCE = 5           # division relevance bonus only

# Component labels used in score breakdowns (kept stable for golden tests).
COMP_EXECUTION_PACK_CORE_ROLE = "execution-pack-core-role"
COMP_PROJECT_TYPE_MATCH = "project-type-match"
COMP_CAPABILITY_MATCH = "capability-match"
COMP_STACK_TECHNOLOGY_MATCH = "stack-technology-match"
COMP_SPECIALTY_TAG_MATCH = "specialty-tag-match"
COMP_DIVISION_RELEVANCE = "division-relevance"


# ---------------------------------------------------------------------------
# Division -> relevant project type IDs (explicit, deterministic).
#
# Used ONLY as a +5 relevance bonus. It is never a gate and never sufficient
# for activation on its own.
# ---------------------------------------------------------------------------

DIVISION_PROJECT_TYPE_RELEVANCE: dict[str, set[str]] = {
    "engineering": {
        "saas", "fullstack-application", "backend-api", "ai-rag", "ai-agent",
        "realtime-application", "desktop-application", "mobile-application",
        "e-commerce",
    },
    "design": {
        "portfolio", "landing-page", "business-website", "saas",
        "fullstack-application",
    },
    "security": {
        "e-commerce", "saas", "backend-api", "fullstack-application",
    },
    "testing": {
        "saas", "fullstack-application", "e-commerce", "backend-api",
    },
    "product": {
        "saas", "fullstack-application", "business-website",
    },
    "project-management": {
        "saas", "fullstack-application",
    },
    "support": {
        "saas", "e-commerce", "fullstack-application",
    },
    "research": {
        "ai-rag", "ai-agent",
    },
    "specialized": {
        "saas", "fullstack-application", "ai-agent", "ai-rag",
    },
}


@dataclass(frozen=True)
class ScoreBreakdown:
    """Itemized, truthful score for one Agency agent."""

    total: int
    components: list[tuple[str, int]] = field(default_factory=list)

    def component(self, label: str) -> int:
        for lbl, pts in self.components:
            if lbl == label:
                return pts
        return 0

    def has_component(self, label: str) -> bool:
        return any(lbl == label for lbl, _ in self.components)

    def non_division_score(self) -> int:
        return self.total - self.component(COMP_DIVISION_RELEVANCE)


@dataclass(frozen=True)
class AgencyCandidate:
    """One Agency agent considered for activation."""

    agent: CanonicalResourceRef
    score: int
    breakdown: ScoreBreakdown
    eligible: bool
    eligibility_reason: str
    qualifies: bool
    qualification_reason: str


@dataclass(frozen=True)
class AgencyScoringResult:
    """Outcome of scoring the Agency catalog for one project context."""

    candidates: list[AgencyCandidate] = field(default_factory=list)
    selected: list[AgencyCandidate] = field(default_factory=list)
    rejected_insufficient_evidence: list[str] = field(default_factory=list)
    rejected_ineligible: list[str] = field(default_factory=list)


class AgencyScoringEngine:
    """Scores Agency agents against a resolved project context.

    Parameters:
        registry: canonical resource registry (bundled + agency-agents).
        applicability_catalog: resource-centric applicability catalog.
        pack_core_roles: execution-pack core role ids active for this project.
    """

    def __init__(
        self,
        registry: ResourceRegistry,
        applicability_catalog: Optional[ApplicabilityCatalog] = None,
        pack_core_roles: Optional[list[str]] = None,
    ) -> None:
        self.registry = registry
        self.applicability_catalog = applicability_catalog or ApplicabilityCatalog.load()
        self.pack_core_roles = set(pack_core_roles or [])

    # -- eligibility ---------------------------------------------------------

    def eligible_agents(
        self,
        project_type_id: str,
        selected_caps: list[str],
        stack_tags: frozenset[str],
    ) -> list[CanonicalResourceRef]:
        """Return Agency agents that pass the common eligibility filter.

        Ineligible agents never enter scoring (Section 6 invariant).
        """
        ctx = ApplicabilityContext(
            project_type=project_type_id,
            capabilities=frozenset(str(c) for c in (selected_caps or [])),
            stack_tags=stack_tags,
            task_tags=frozenset(),  # task_tags unsupported at project level
            selected=frozenset(),
        )
        eligible: list[CanonicalResourceRef] = []
        for agent in self.registry.list_agents():
            if agent.source != "agency-agents":
                continue
            applicability = self.applicability_catalog.get("agent", agent.id)
            result = is_resource_eligible(applicability, ctx)
            if result.applicable:
                eligible.append(agent)
        return eligible

    # -- scoring -------------------------------------------------------------

    def score_agent(
        self,
        agent: CanonicalResourceRef,
        project_type_id: str,
        selected_caps: list[str],
        stack_tags: frozenset[str],
    ) -> ScoreBreakdown:
        """Explainable deterministic score for one Agency agent.

        Every component is itemized. Division relevance is a bonus only and
        never counts toward the evidence threshold.
        """
        score = 0
        components: list[tuple[str, int]] = []
        selected_caps_set = set(str(c) for c in (selected_caps or []))
        stack_tags_set = set(stack_tags)
        agent_id = str(agent.id)

        # 1. Explicit execution-pack core role (+100).
        if agent_id in self.pack_core_roles:
            score += EXECUTION_PACK_CORE_ROLE
            components.append((COMP_EXECUTION_PACK_CORE_ROLE, EXECUTION_PACK_CORE_ROLE))

        # 2. Explicit project-type match (+40).
        agent_ptypes = set(str(p) for p in (agent.project_types or []))
        if project_type_id and project_type_id in agent_ptypes:
            score += PROJECT_TYPE_MATCH
            components.append((COMP_PROJECT_TYPE_MATCH, PROJECT_TYPE_MATCH))

        # 3. Capability match (+30): selected capability declared by agent.
        agent_caps = set(str(c) for c in (agent.capabilities or []))
        cap_matches = agent_caps & selected_caps_set
        if cap_matches:
            score += CAPABILITY_MATCH
            components.append((COMP_CAPABILITY_MATCH, CAPABILITY_MATCH))

        # 4. Stack/technology match (+20): agent.stack_tags compared against
        #    the resolved stack TECHNOLOGY tags, not merely the bundle id.
        agent_stack_tags = set(str(t) for t in (agent.stack_tags or []))
        stack_matches = agent_stack_tags & stack_tags_set
        if stack_matches:
            score += STACK_TECHNOLOGY_MATCH
            components.append((COMP_STACK_TECHNOLOGY_MATCH, STACK_TECHNOLOGY_MATCH))

        # 5. Specialty/task match (+10): agent specialties/tags match the
        #    project's task context (selected capabilities act as the task
        #    signal at project level).
        agent_specialties = set(str(s) for s in (agent.specialties or []))
        agent_tags = set(str(t) for t in (agent.tags or []))
        specialty_matches = (
            (agent_specialties & selected_caps_set)
            | (agent_tags & stack_tags_set)
        )
        if specialty_matches:
            score += SPECIALTY_TAG_MATCH
            components.append((COMP_SPECIALTY_TAG_MATCH, SPECIALTY_TAG_MATCH))

        # 6. Division relevance (+5): bonus only, never sufficient alone.
        division = str(agent.division or "")
        relevant_divisions = {
            div for div, pts in DIVISION_PROJECT_TYPE_RELEVANCE.items()
            if project_type_id in pts
        }
        if division and division in relevant_divisions:
            score += DIVISION_RELEVANCE
            components.append((COMP_DIVISION_RELEVANCE, DIVISION_RELEVANCE))

        return ScoreBreakdown(total=score, components=components)

    # -- candidate selection -------------------------------------------------

    def select_candidates(
        self,
        project_type_id: str,
        selected_caps: list[str],
        stack_tags: frozenset[str],
        limit: int = 5,
    ) -> AgencyScoringResult:
        """Rank eligible Agency agents and return qualified candidates.

        An agent qualifies for activation only when it carries meaningful
        project-specific evidence (see MIN_EVIDENCE_SCORE) or holds an
        explicit execution-pack core role. Division relevance alone never
        qualifies an agent.

        Returns candidates in ranking order (descending score, id tie-break)
        plus the selected subset (up to ``limit``).
        """
        ctx = ApplicabilityContext(
            project_type=project_type_id,
            capabilities=frozenset(str(c) for c in (selected_caps or [])),
            stack_tags=stack_tags,
            task_tags=frozenset(),
            selected=frozenset(),
        )

        scored: list[AgencyCandidate] = []
        rejected_ineligible: list[str] = []
        rejected_insufficient_evidence: list[str] = []

        for agent in self.registry.list_agents():
            if agent.source != "agency-agents":
                continue
            applicability = self.applicability_catalog.get("agent", agent.id)
            eligibility = is_resource_eligible(applicability, ctx)
            if not eligibility.applicable:
                rejected_ineligible.append(agent.id)
                continue
            breakdown = self.score_agent(
                agent, project_type_id, selected_caps, stack_tags
            )
            evidence = breakdown.non_division_score()
            has_core_role = breakdown.has_component(COMP_EXECUTION_PACK_CORE_ROLE)
            qualifies = has_core_role or evidence >= MIN_EVIDENCE_SCORE
            if qualifies:
                qualification_reason = (
                    "execution-pack core role"
                    if has_core_role
                    else f"evidence score {evidence} >= threshold {MIN_EVIDENCE_SCORE}"
                )
            else:
                qualification_reason = (
                    f"insufficient evidence: {evidence} < threshold "
                    f"{MIN_EVIDENCE_SCORE} (division relevance alone)"
                )
                rejected_insufficient_evidence.append(agent.id)
            scored.append(
                AgencyCandidate(
                    agent=agent,
                    score=breakdown.total,
                    breakdown=breakdown,
                    eligible=eligibility.applicable,
                    eligibility_reason=eligibility.reason,
                    qualifies=qualifies,
                    qualification_reason=qualification_reason,
                )
            )

        # Descending score; final tie-break ascending id (deterministic).
        scored.sort(
            key=lambda c: (-c.score, str(c.agent.id))
        )
        selected = [c for c in scored if c.qualifies][: max(0, limit)]
        return AgencyScoringResult(
            candidates=scored,
            selected=selected,
            rejected_insufficient_evidence=rejected_insufficient_evidence,
            rejected_ineligible=rejected_ineligible,
        )

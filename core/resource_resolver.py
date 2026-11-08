"""
Resource resolver for AI-Coding-starter V2 Milestone M12 / M6.3-M6.4.

Resolves project type + capabilities + stack bundle (+ optional execution
pack) to a bounded set of resource selections (id, type, version, provenance,
selection_reason).

Architecture:
    project type ID + capabilities + stack bundle ID [+ execution pack]
            ↓
    ResourceRegistry  (bundled + agency-agents canonical resources)
    ExecutionPackRegistry  (validated execution packs)
            ↓
    ResourceResolver  (deterministic, bounded team selection)
            ↓
    ResourceSelectionResult

Resolution pipeline (Section 4):

    PROJECT CONTEXT
        → CANDIDATE DISCOVERY (resource-requirements.yaml per project type,
           execution packs, Agency catalog)
        → RESOURCE APPLICABILITY / ELIGIBILITY FILTER  (Section 5 single
           evaluator; catalog/resource-applicability.yaml is the canonical
           (type, id)-keyed source of truth)
        → RELEVANCE / SPECIALTY SCORING  (Agency agents via
           core/agency_scoring.py; bundled resources score 0)
        → DEPENDENCY + CONFLICT VALIDATION  (requires / conflicts_with see
           resources selected earlier during the same resolution via a
           deterministic fixed-point)
        → TEAM / RESOURCE BUDGET  (complexity-aware agent ceiling)
        → DETERMINISTIC FINAL SELECTION
        → resources.lock + portable materialization  (caller side)
        → optional runtime rendering

Design principles:
  * Runtime-agnostic. No vendor branches.
  * Offline. No network, no LLM.
  * Stdlib-only.
  * Honest inference: never guesses resource IDs; validates against registry.
  * (type, id) collision-safe.
  * INELIGIBLE RESOURCE MUST NEVER ENTER SCORING. This invariant applies
    equally to bundled agents, Agency agents, skills, rules, workflows,
    scripts, shared modules, and templates. Agency agents are NOT
    special-cased around the eligibility layer.
  * Bounded activation: full catalog is knowledge base; resolver activates only
    a small team per project. Agent count follows a complexity-aware budget
    (minimal/static 4-6, balanced 5-8, complex 6-10, hard ceiling 10).
  * Specialty-aware: Agency agents are ranked by an explainable deterministic
    score; alphabetical id is only the final tie-break.

`when` versus applicability (unambiguous semantics):
  * ``when`` (per entry in resource-requirements.yaml) is the per-entry
    ACTIVATION TRIGGER: does this resource fire for the current project
    context (capability, stack bundle, project type, always)? It is evaluated
    by _matches_conditions and describes the immediate trigger via
    _selection_reason.
  * applicability (catalog/resource-applicability.py, single evaluator
    is_resource_eligible) is the resource-centric ELIGIBILITY GATE: is this
    resource allowed to apply to this project context at all (project type,
    capabilities, stack tags, requires, conflicts_with, global)? It blocks
    cross-domain leakage regardless of which project type listed the resource.
  * A resource is activated only when BOTH the eligibility gate passes AND the
    ``when`` trigger matches. The two are deliberately separate; applicability
    metadata is never re-derived from ``when``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from core.resource_registry import (
    ResourceCatalogLoader,
    ResourceRegistry,
)
from core.execution_pack_registry import (
    ExecutionPackRegistry,
    build_default_pack_registry,
)
from core.applicability import (
    ApplicabilityContext,
    ApplicabilityCatalog,
    is_resource_eligible,
)
from core.agency_scoring import AgencyScoringEngine

# Canonical location of the resource requirements catalog relative to this module.
DEFAULT_CATALOG_DIR = Path(__file__).resolve().parent.parent / "catalog"

# Mapping from resource type ID to directory name under resources/.
RESOURCE_TYPE_TO_DIR = {
    "agent": "agents",
    "skill": "skills",
    "shared-module": "shared",
    "workflow": "workflows",
    "script": "scripts",
    "template": "core",
    "rule": "rules",
}

# Team size policy (M6.4 / Section 13 / Section 17).
DEFAULT_TEAM_CEILING = 8      # typical total ceiling
HARD_TEAM_CEILING = 10        # hard default ceiling (override only by explicit pack)
CORE_TEAM_MIN = 2             # project-planner + orchestrator
CORE_TEAM_MAX = 5
SPECIALIST_MAX = 5

# Complexity-aware agent budget by stack bundle profile.
# (min agents, max agents). Hard ceiling always applies.
PROFILE_AGENT_BUDGET: dict[str, tuple[int, int]] = {
    "minimal": (4, 6),
    "fastest-mvp": (5, 8),
    "balanced": (5, 8),
    "scalable": (6, 10),
    "custom": (5, 8),
}
DEFAULT_AGENT_BUDGET = (5, 8)  # used when the bundle profile is unknown


@dataclass(frozen=True)
class ResourceSelection:
    """A single resource selection for M5/M7 rendering.

    Identity is (type, id) — never id alone — so same-named resources
    across different types (e.g. agent:security-auditor vs
    skill:security-auditor) are treated as distinct.
    """

    id: str
    type: str  # agent | skill | shared-module | workflow | script | template | rule
    version: str = "1.0.0"
    provenance_source: str = "bundled"
    provenance_commit_sha: str = "8b61d297dc07772a000b85fc93138c8aefd21c45"
    provenance_license: str = "MIT"
    selection_reason: str = ""
    name: str = ""
    description: str = ""
    division: str = ""
    # Specialty-aware scoring (Agency agents). Bundled resources score 0.
    score: int = 0
    score_breakdown: list[tuple[str, int]] = field(default_factory=list)


@dataclass(frozen=True)
class ResourceSelectionResult:
    """Result of resolving project type + capabilities + stack bundle to resources."""

    resources: list[ResourceSelection] = field(default_factory=list)
    project_type_id: str = ""
    selected_capability_ids: list[str] = field(default_factory=list)
    stack_bundle_id: str = ""
    execution_pack_id: Optional[str] = None
    errors: list[str] = field(default_factory=list)
    agent_budget: tuple[int, int] = field(default_factory=lambda: DEFAULT_AGENT_BUDGET)

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def resource_map(self) -> dict[tuple[str, str], ResourceSelection]:
        """Map keyed by (type, id) for collision-safe lookup."""
        return {(r.type, r.id): r for r in self.resources}

    @property
    def agents(self) -> list[ResourceSelection]:
        """Selected agent resources, in result order."""
        return [r for r in self.resources if r.type == "agent"]

    @property
    def agent_count(self) -> int:
        return len(self.agents)


class ResourceResolver:
    """Deterministic, bounded resource resolver.

    Selects a small active team from the full canonical registry
    (bundled + agency-agents). Never activates the entire catalog.

    Team size policy (§13 / §17):
      Agent count follows a complexity-aware budget derived from the stack
      bundle profile, bounded by HARD_TEAM_CEILING (10).
    """

    def __init__(
        self,
        registry: ResourceRegistry,
        pack_registry: Optional[ExecutionPackRegistry] = None,
    ) -> None:
        self.registry = registry
        self.pack_registry = pack_registry

    def resolve(
        self,
        project_type_id: str,
        selected_capability_ids: list[str],
        stack_bundle_id: str,
        execution_pack_id: Optional[str] = None,
    ) -> ResourceSelectionResult:
        """Resolve to a bounded resource selection.

        Args:
            project_type_id: Canonical project type ID.
            selected_capability_ids: Canonical capability IDs chosen by user.
            stack_bundle_id: Canonical stack bundle ID.
            execution_pack_id: Optional execution pack slug. When given, its
                core roles are activated first (highest priority).

        Returns:
            ResourceSelectionResult with bounded resources and selection
            reasons.
        """
        errors: list[str] = []
        resources: list[ResourceSelection] = []
        seen: set[tuple[str, str]] = set()

        project_type_id = str(project_type_id or "")
        selected_caps = sorted({str(c) for c in (selected_capability_ids or [])})
        stack_bundle_id = str(stack_bundle_id or "")

        # --- Complexity-aware agent budget from the stack bundle profile ---
        agent_budget = self._agent_budget_for_bundle(stack_bundle_id)
        agent_ceiling = min(agent_budget[1], HARD_TEAM_CEILING)

        # --- Applicability catalog: single (type, id)-keyed source of truth ---
        # for resource eligibility (Section 5 single evaluator). Loaded once per
        # resolution; it is static catalog data.
        self._applicability_catalog = ApplicabilityCatalog.load()
        # Stack technology tags derived from the selected bundle's technologies,
        # used by the stack_tags eligibility axis and Agency stack scoring.
        self._stack_tags = self._stack_tags_for_bundle(stack_bundle_id)

        # --- Growing selection set (Section 6) ---
        # `selected_so_far` grows as roles are added so `requires` /
        # `conflicts_with` can be evaluated against resources selected earlier
        # during the same resolution. A fresh context is built for every
        # eligibility check so it always sees the current selection.
        selected_so_far: set[tuple[str, str]] = set()

        def _ctx_for(selected: set[tuple[str, str]]) -> ApplicabilityContext:
            return ApplicabilityContext(
                project_type=project_type_id,
                capabilities=frozenset(selected_caps),
                stack_tags=self._stack_tags,
                task_tags=frozenset(),  # task_tags unsupported at project level
                selected=frozenset(selected),
            )

        def _applicability_for(rtype: str, rid: str):
            return self._applicability_catalog.get(rtype, rid)

        def _add_if_eligible(
            rtype: str, rid: str, reason: str
        ) -> bool:
            """Add a resource only if it passes the eligibility gate.

            Returns True when the resource was added. Ineligible resources
            never enter scoring, regardless of reason or source.
            """
            key = (rtype, rid)
            if key in seen:
                return False
            if not self._registry_has(rtype, rid):
                errors.append(f"Resource not found in registry: {rtype}:{rid}")
                return False
            eligibility = is_resource_eligible(
                _applicability_for(rtype, rid), _ctx_for(selected_so_far)
            )
            if not eligibility.applicable:
                # Ineligible: never enters scoring, regardless of source.
                return False
            seen.add(key)
            selected_so_far.add(key)
            resources.append(
                self._make_selection(
                    rtype, rid, reason,
                    pack_core_roles=pack_core_roles,
                    selected_caps=selected_caps,
                    project_type_id=project_type_id,
                    stack_bundle_id=stack_bundle_id,
                )
            )
            return True

        pack_core_roles: list[str] = []

        # --- 1. Execution pack core roles (highest priority) ---------------
        pack = None
        if execution_pack_id is not None and self.pack_registry is not None:
            pack = self.pack_registry.get(execution_pack_id)
            if pack is None:
                errors.append(f"Execution pack not found: {execution_pack_id!r}")
            else:
                pack_core_roles = list(pack.core_roles)
                for role_id in pack_core_roles:
                    _add_if_eligible(
                        "agent", role_id,
                        f"execution-pack:{pack.id} core-role",
                    )

        # --- 2. Execution pack optional roles (trigger-matched) ------------
        if pack is not None:
            for opt_role in pack.optional_roles:
                triggered = False
                if opt_role.activation == "capability-triggered":
                    if any(c in selected_caps for c in opt_role.trigger_capabilities):
                        triggered = True
                elif opt_role.activation == "stack-triggered":
                    if stack_bundle_id in opt_role.trigger_stack_bundles:
                        triggered = True
                elif opt_role.activation == "always":
                    triggered = True
                # as-needed / post-fix are not auto-triggered here

                if not triggered:
                    continue

                _add_if_eligible(
                    "agent", opt_role.resource_id,
                    f"execution-pack:{pack.id} optional-role "
                    f"({opt_role.activation})",
                )

        # --- 3. Project-type + capability/stack-driven bundled resources --
        # Eligibility gate (Section 5) THEN `when` activation trigger. Both
        # must pass. The fixed-point loop re-checks eligibility against
        # `selected_so_far` as it grows, so `requires`/`conflicts_with` see
        # resources selected earlier during the same resolution.
        pt_resources = self._load_project_type_resources(project_type_id)

        changed = True
        while changed:
            changed = False
            for res_def in pt_resources:
                rid = res_def.get("id", "")
                rtype = res_def.get("type", "")
                if not rid or not rtype:
                    errors.append(f"Invalid resource entry: missing id or type: {res_def}")
                    continue
                key = (rtype, rid)
                if key in seen:
                    continue
                if not self._registry_has(rtype, rid):
                    errors.append(f"Resource not found in registry: {rtype}:{rid}")
                    continue
                # ELIGIBILITY FILTER (Section 4 / Section 6).
                eligibility = is_resource_eligible(
                    _applicability_for(rtype, rid), _ctx_for(selected_so_far)
                )
                if not eligibility.applicable:
                    continue
                # WHEN activation trigger (per-entry trigger, separate from
                # eligibility). Condition not met: resource stays inactive.
                if not self._matches_conditions(
                    res_def, project_type_id, selected_caps, stack_bundle_id
                ):
                    continue
                seen.add(key)
                selected_so_far.add(key)
                changed = True
                reason = self._selection_reason(
                    res_def, project_type_id, selected_caps, stack_bundle_id
                )
                resources.append(
                    self._make_selection(
                        rtype, rid, reason,
                        pack_core_roles=pack_core_roles,
                        selected_caps=selected_caps,
                        project_type_id=project_type_id,
                        stack_bundle_id=stack_bundle_id,
                    )
                )

        # --- 4. Agency specialists relevant to project type (scored) -------
        # Agency agents go through the SAME eligibility filter before scoring.
        # An ineligible agent never enters ranking. The Agency scoring engine
        # applies the evidence threshold: division relevance alone never
        # qualifies an agent for activation.
        agent_count = sum(1 for r in resources if r.type == "agent")
        agent_slots_remaining = max(0, agent_ceiling - agent_count)
        if agent_slots_remaining > 0:
            agency_engine = AgencyScoringEngine(
                self.registry,
                self._applicability_catalog,
                pack_core_roles=pack_core_roles,
            )
            scoring_result = agency_engine.select_candidates(
                project_type_id,
                selected_caps,
                self._stack_tags,
                limit=agent_slots_remaining,
            )
            for candidate in scoring_result.selected:
                if agent_count >= agent_ceiling:
                    break
                key = ("agent", candidate.agent.id)
                if key in seen:
                    continue
                # Final eligibility re-check against the current selection
                # (defensive: Agency engine already filters, but the gate
                # applies to every source equally).
                eligibility = is_resource_eligible(
                    _applicability_for("agent", candidate.agent.id),
                    _ctx_for(selected_so_far),
                )
                if not eligibility.applicable:
                    continue
                seen.add(key)
                selected_so_far.add(key)
                agent_count += 1
                resources.append(
                    ResourceSelection(
                        id=candidate.agent.id,
                        type="agent",
                        version="1.0.0",
                        provenance_source=candidate.agent.provenance.get(
                            "source", "agency-agents"
                        ),
                        provenance_commit_sha=candidate.agent.provenance.get(
                            "upstream_commit",
                            "8b61d297dc07772a000b85fc93138c8aefd21c45",
                        ),
                        provenance_license=candidate.agent.provenance.get(
                            "license", "MIT"
                        ),
                        selection_reason=(
                            f"agency:{candidate.qualification_reason} "
                            f"(score {candidate.score})"
                        ),
                        name=candidate.agent.name,
                        description=candidate.agent.description,
                        division=candidate.agent.division,
                        score=candidate.score,
                        score_breakdown=candidate.breakdown.components,
                    )
                )

        # --- 5. Enforce team size ceiling ----------------------------------
        if agent_count > HARD_TEAM_CEILING:
            agent_resources = [r for r in resources if r.type == "agent"]
            non_agent = [r for r in resources if r.type != "agent"]
            resources = non_agent + agent_resources[:HARD_TEAM_CEILING]
            errors.append(
                f"Team size exceeded hard ceiling {HARD_TEAM_CEILING}; "
                f"truncated to top-ranked selections."
            )

        # Deterministic ordering: type then id.
        resources.sort(key=lambda r: (r.type, r.id))

        return ResourceSelectionResult(
            resources=resources,
            project_type_id=project_type_id,
            selected_capability_ids=selected_caps,
            stack_bundle_id=stack_bundle_id,
            execution_pack_id=execution_pack_id,
            errors=errors,
            agent_budget=agent_budget,
        )

    # -- condition evaluation ----------------------------------------------
    def _matches_conditions(
        self,
        defn: dict,
        project_type_id: str,
        selected_caps: list[str],
        stack_bundle_id: str,
    ) -> bool:
        """Evaluate a resource entry's explicit `when` activation condition.

        `when` is the per-entry ACTIVATION TRIGGER, evaluated separately from
        resource eligibility (see module docstring for the unambiguous
        `when` versus applicability semantics). Missing or empty `when`
        defaults to `always` for backward compatibility with older catalog
        entries.
        """
        when = defn.get("when")
        if not when:
            return True
        if not isinstance(when, dict):
            return True
        if when.get("always"):
            return True
        caps_any = when.get("capabilities_any")
        if isinstance(caps_any, list) and caps_any:
            if any(str(c) in selected_caps for c in caps_any):
                return True
        caps_all = when.get("capabilities_all")
        if isinstance(caps_all, list) and caps_all:
            if all(str(c) in selected_caps for c in caps_all):
                return True
        bundles = when.get("stack_bundles")
        if isinstance(bundles, list) and bundles:
            if stack_bundle_id in bundles:
                return True
        ptypes = when.get("project_types")
        if isinstance(ptypes, list) and ptypes:
            if project_type_id in ptypes:
                return True
        return False

    def _selection_reason(
        self,
        defn: dict,
        project_type_id: str,
        selected_caps: list[str],
        stack_bundle_id: str,
    ) -> str:
        """Describe what actually triggered selection of a resource.

        Reports the `when` activation trigger that fired (or the entry's
        static `reason`). Never claims a capability that was not selected.
        """
        reason = defn.get("reason", f"project-type:{project_type_id}")
        when = defn.get("when") or {}
        if not isinstance(when, dict):
            return reason
        if when.get("always"):
            return reason
        caps_any = when.get("capabilities_any")
        if isinstance(caps_any, list) and caps_any:
            matched = [c for c in caps_any if str(c) in selected_caps]
            if matched:
                return f"capability:{matched[0]}"
        caps_all = when.get("capabilities_all")
        if isinstance(caps_all, list) and caps_all:
            return f"capability:{','.join(caps_all)}"
        bundles = when.get("stack_bundles")
        if isinstance(bundles, list) and bundles and stack_bundle_id in bundles:
            return f"stack-bundle:{stack_bundle_id}"
        ptypes = when.get("project_types")
        if isinstance(ptypes, list) and ptypes and project_type_id in ptypes:
            return f"project-type:{project_type_id}"
        return reason

    # -- helpers ------------------------------------------------------------
    def _agent_budget_for_bundle(self, stack_bundle_id: str) -> tuple[int, int]:
        """Derive the complexity-aware agent budget from the stack bundle profile."""
        if not stack_bundle_id:
            return DEFAULT_AGENT_BUDGET
        path = DEFAULT_CATALOG_DIR / "stack-bundles.yaml"
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (FileNotFoundError, json.JSONDecodeError):
            return DEFAULT_AGENT_BUDGET
        bundles = data.get("stack_bundles", [])
        if not isinstance(bundles, list):
            return DEFAULT_AGENT_BUDGET
        for bundle in bundles:
            if str(bundle.get("id")) == stack_bundle_id:
                profile = str(bundle.get("profile", ""))
                return PROFILE_AGENT_BUDGET.get(profile, DEFAULT_AGENT_BUDGET)
        return DEFAULT_AGENT_BUDGET

    def _registry_has(self, rtype: str, rid: str) -> bool:
        return self.registry.get(rtype, rid) is not None

    def _load_project_type_resources(
        self, project_type_id: str
    ) -> list[dict]:
        """Load resource-requirements.yaml entries for a project type.

        Candidate discovery only: returns the resources a project type lists.
        Eligibility is decided separately by the applicability engine, so a
        listed resource is not automatically activated.
        """
        path = DEFAULT_CATALOG_DIR / "resource-requirements.yaml"
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
        if not isinstance(data, dict):
            return []
        requirements = data.get("resource_requirements", [])
        if not isinstance(requirements, list):
            return []
        for entry in requirements:
            if entry.get("project_type") == project_type_id:
                return entry.get("resources", [])
        return []

    def _stack_tags_for_bundle(self, stack_bundle_id: str) -> frozenset[str]:
        """Derive stack technology tags from the bundle's technologies.

        Returns the technology values (e.g. nextjs, postgresql) plus the
        bundle id itself. Agency stack_tags are compared against this set, not
        merely the bundle id.
        """
        if not stack_bundle_id:
            return frozenset()
        path = DEFAULT_CATALOG_DIR / "stack-bundles.yaml"
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (FileNotFoundError, json.JSONDecodeError):
            return frozenset()
        bundles = data.get("stack_bundles", [])
        if not isinstance(bundles, list):
            return frozenset()
        for bundle in bundles:
            if str(bundle.get("id")) != stack_bundle_id:
                continue
            tags: set[str] = set()
            for role_value in bundle.get("technologies", {}).values():
                if role_value:
                    tags.add(str(role_value))
            tags.add(stack_bundle_id)
            return frozenset(tags)
        return frozenset()

    def _make_selection(
        self,
        rtype: str,
        rid: str,
        reason: str,
        pack_core_roles: Optional[list[str]] = None,
        selected_caps: Optional[list[str]] = None,
        project_type_id: str = "",
        stack_bundle_id: str = "",
    ) -> ResourceSelection:
        """Build a ResourceSelection, populating name/description + provenance
        from the registry ref (falls back to bundled defaults when ref absent).

        Bundled resources always score 0; agency agents are scored by the
        Agency scoring engine when relevant.
        """
        DEFAULT_SHA = "8b61d297dc07772a000b85fc93138c8aefd21c45"
        ref = self.registry.get(rtype, rid)
        prov = ref.provenance if ref else {}
        return ResourceSelection(
            id=rid,
            type=rtype,
            version="1.0.0",
            provenance_source=prov.get("source", "bundled"),
            provenance_commit_sha=prov.get("upstream_commit", DEFAULT_SHA),
            provenance_license=prov.get("license", "MIT"),
            selection_reason=reason,
            name=(ref.name if ref else rid),
            description=(ref.description if ref else ""),
            division=(ref.division if ref else ""),
            score=0,
            score_breakdown=[],
        )


# Backward-compatible module-level API (M5/M7).
def resolve_resources(
    project_type_id: str,
    selected_capability_ids: list[str],
    stack_bundle_id: str,
    catalog_dir: Path | None = None,
    resources_root: Path | None = None,
    execution_pack_id: Optional[str] = None,
    pack_registry: Optional[ExecutionPackRegistry] = None,
) -> ResourceSelectionResult:
    """Resolve project type + capabilities + stack bundle to resource selections.

    Backward-compatible wrapper around :class:`ResourceResolver`. Builds the
    default registry (bundled + agency catalog) from ``resources_root`` and
    ``catalog_dir/agency-agents.yaml``.
    """
    if catalog_dir is None:
        catalog_dir = DEFAULT_CATALOG_DIR
    catalog_dir = Path(catalog_dir)
    if resources_root is None:
        resources_root = Path(__file__).resolve().parent.parent / "resources"

    agency_catalog_path = catalog_dir / "agency-agents.yaml"
    enrichment_catalog_path = catalog_dir / "agency-enrichment.yaml"
    registry = ResourceCatalogLoader(
        resources_root, agency_catalog_path, enrichment_catalog_path
    ).load()

    if pack_registry is None:
        pack_registry = build_default_pack_registry(
            resource_registry=registry
        )

    resolver = ResourceResolver(registry, pack_registry=pack_registry)
    return resolver.resolve(
        project_type_id=project_type_id,
        selected_capability_ids=selected_capability_ids,
        stack_bundle_id=stack_bundle_id,
        execution_pack_id=execution_pack_id,
    )


def type_dir_name(rtype: str) -> str:
    """Map canonical resource type ID to directory name under resources/."""
    return RESOURCE_TYPE_TO_DIR.get(rtype, rtype)

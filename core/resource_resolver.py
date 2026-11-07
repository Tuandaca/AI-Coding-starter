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

Design principles:
  * Runtime-agnostic. No vendor branches.
  * Offline. No network, no LLM.
  * Stdlib-only.
  * Honest inference: never guesses resource IDs; validates against registry.
  * (type, id) collision-safe.
  * Capability-gated: a resource is activated ONLY when its explicit `when`
    condition matches the resolved project context. Free-form `selection_reason`
    always describes what actually triggered selection.
  * Bounded activation: full catalog is knowledge base; resolver activates only
    a small team per project. Agent count follows a complexity-aware budget
    (minimal/static 4-6, balanced 5-8, complex 6-10, hard ceiling 10).
  * Specialty-aware: Agency agents are ranked by an explainable deterministic
    score; alphabetical id is only the final tie-break.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from core.resource_registry import (
    ResourceCatalogLoader,
    ResourceRegistry,
    build_default_registry,
)
from core.execution_pack_registry import (
    ExecutionPackRegistry,
    build_default_pack_registry,
)

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

# Agency division → relevant project type IDs (explicit, deterministic).
# Used to rank agency specialists for a given project type. Divisions not
# listed here contribute no agency specialists (empty set).
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

    Resolution priority (§12):
      1. Execution pack core roles (highest priority)
      2. Project-type-relevant bundled resources (when conditions match)
      3. Capability/stack-driven bundled resources (when conditions match)
      4. Agency specialists relevant to project type (scored, specialty-aware)
      5. Quality/safety roles (implied by capabilities)

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

        # --- 1. Execution pack core roles (highest priority) --------------
        pack = None
        pack_core_roles: list[str] = []
        if execution_pack_id is not None and self.pack_registry is not None:
            pack = self.pack_registry.get(execution_pack_id)
            if pack is None:
                errors.append(
                    f"Execution pack not found: {execution_pack_id!r}"
                )
            else:
                pack_core_roles = list(pack.core_roles)
                for role_id in pack_core_roles:
                    key = ("agent", role_id)
                    if key in seen:
                        continue
                    seen.add(key)
                    resources.append(
                        self._make_selection(
                            "agent", role_id,
                            f"execution-pack:{pack.id} core-role",
                            pack_core_roles=pack_core_roles,
                            selected_caps=selected_caps,
                            project_type_id=project_type_id,
                            stack_bundle_id=stack_bundle_id,
                        )
                    )

        # --- 2. Execution pack optional roles (trigger-matched) -----------
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

                key = ("agent", opt_role.resource_id)
                if key in seen:
                    continue
                seen.add(key)
                resources.append(
                    self._make_selection(
                        "agent", opt_role.resource_id,
                        f"execution-pack:{pack.id} optional-role "
                        f"({opt_role.activation})",
                        pack_core_roles=pack_core_roles,
                        selected_caps=selected_caps,
                        project_type_id=project_type_id,
                        stack_bundle_id=stack_bundle_id,
                    )
                )

        # --- 3. Project-type + capability/stack-driven bundled resources --
        # Every base resource carries an explicit `when` condition. A resource
        # is activated ONLY when its condition matches the resolved context.
        # This replaces the old free-form "capability:<id>" reason parsing.
        pt_resources = self._load_project_type_resources(project_type_id)
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
            if not self._matches_conditions(
                res_def, project_type_id, selected_caps, stack_bundle_id
            ):
                # Condition not met: resource stays inactive for this project.
                continue
            seen.add(key)
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

        # --- 4. Agency specialists relevant to project type (scored) ------
        # Count agents so far (pack core + optional + bundled agents).
        agent_count = sum(1 for r in resources if r.type == "agent")
        agent_slots_remaining = max(0, agent_ceiling - agent_count)
        if agent_slots_remaining > 0:
            agency_agents = self._select_agency_specialists(
                project_type_id,
                selected_caps,
                stack_bundle_id,
                pack_core_roles,
                limit=agent_slots_remaining,
            )
            for agent in agency_agents:
                if agent_count >= agent_ceiling:
                    break
                key = ("agent", agent.id)
                if key in seen:
                    continue
                seen.add(key)
                agent_count += 1
                score, breakdown = self._score_agency_agent(
                    agent, project_type_id, selected_caps,
                    stack_bundle_id, pack_core_roles
                )
                reason = (
                    f"agency-division:{agent.division} relevance to "
                    f"project-type:{project_type_id} (score {score})"
                )
                resources.append(
                    ResourceSelection(
                        id=agent.id,
                        type="agent",
                        version="1.0.0",
                        provenance_source=agent.provenance.get("source", "agency-agents"),
                        provenance_commit_sha=agent.provenance.get(
                            "upstream_commit",
                            "8b61d297dc07772a000b85fc93138c8aefd21c45",
                        ),
                        provenance_license=agent.provenance.get("license", "MIT"),
                        selection_reason=reason,
                        name=agent.name,
                        description=agent.description,
                        division=agent.division,
                        score=score,
                        score_breakdown=breakdown,
                    )
                )

        # --- 5. Enforce team size ceiling ---------------------------------
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

        Returns True when the resource should be activated for the resolved
        project context. Missing or empty `when` defaults to `always` for
        backward compatibility with older catalog entries.
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
        """Describe what actually triggered selection of a resource."""
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

    # -- agency scoring ----------------------------------------------------
    def _relevant_divisions(self, project_type_id: str) -> set[str]:
        return {
            div for div, pts in DIVISION_PROJECT_TYPE_RELEVANCE.items()
            if project_type_id in pts
        }

    def _score_agency_agent(
        self,
        agent,
        project_type_id: str,
        selected_caps: list[str],
        stack_bundle_id: str,
        pack_core_roles: list[str],
    ) -> tuple[int, list[tuple[str, int]]]:
        """Explainable deterministic score for an agency agent.

        Relative priority (§15):
          execution-pack core role +100
          capability match +40
          project-type match +30
          stack/technology match +20
          specialty/tag match +10
          division relevance +5
          alphabetical id is the final tie-break (applied by the caller).
        """
        score = 0
        breakdown: list[tuple[str, int]] = []

        agent_id = str(agent.id)
        divisions = set(agent.division) if agent.division else set()
        relevant_divisions = self._relevant_divisions(project_type_id)

        # 1. Execution pack core role match (+100)
        if agent_id in set(pack_core_roles):
            score += 100
            breakdown.append(("execution-pack-core-role", 100))

        # 2. Selected capability match (+40)
        agent_caps = set(str(c) for c in (agent.capabilities or []))
        cap_matches = agent_caps & set(selected_caps)
        if cap_matches:
            score += 40
            breakdown.append(("capability-match", 40))

        # 3. Project-type match (+30)
        agent_ptypes = set(str(p) for p in (agent.project_types or []))
        if project_type_id and project_type_id in agent_ptypes:
            score += 30
            breakdown.append(("project-type-match", 30))

        # 4. Stack/technology match (+20): agent tags matching the stack bundle
        #    id or the project-type-aligned technology hints carried in tags.
        agent_tags = set(str(t) for t in (agent.tags or []))
        stack_hint = {stack_bundle_id} if stack_bundle_id else set()
        stack_matches = agent_tags & stack_hint
        if stack_matches:
            score += 20
            breakdown.append(("stack-technology-match", 20))

        # 5. Specialty/tag match (+10): agent tags matching selected capabilities
        tag_matches = agent_tags & set(selected_caps)
        if tag_matches:
            score += 10
            breakdown.append(("specialty-tag-match", 10))

        # 6. Division relevance (+5)
        if agent.division and agent.division in relevant_divisions:
            score += 5
            breakdown.append(("division-relevance", 5))

        return score, breakdown

    def _select_agency_specialists(
        self,
        project_type_id: str,
        selected_caps: list[str],
        stack_bundle_id: str,
        pack_core_roles: list[str],
        limit: int = SPECIALIST_MAX,
    ) -> list:
        """Select agency agents relevant to the project type, scored.

        Agents are ranked by descending score with the agent id as the final
        deterministic tie-break. Returns up to ``limit`` entries.
        """
        relevant_divisions = self._relevant_divisions(project_type_id)
        if not relevant_divisions or limit <= 0:
            return []

        candidates: list = []
        for agent in self.registry.list_agents():
            if agent.division in relevant_divisions:
                candidates.append(agent)
        if not candidates:
            return []

        pack_core_set = set(pack_core_roles)
        scored = []
        for agent in candidates:
            score, breakdown = self._score_agency_agent(
                agent, project_type_id, selected_caps,
                stack_bundle_id, pack_core_roles,
            )
            scored.append((score, agent.id, agent, breakdown))

        # Descending score; final tie-break ascending id (deterministic).
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [item[2] for item in scored[:limit]]

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
        """Load resource-requirements.yaml entries for a project type."""
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
        caller when relevant.
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

"""
Resource resolver for AI-Coding-starter V2 Milestone M12 / M6.3-M6.4.

Resolves project type + capabilities + stack bundle (+ optional execution
pack) to a bounded set of resource selections (id, type, version,
provenance, selection_reason).

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
  * Bounded activation: full catalog is knowledge base; resolver activates only
    a small team per project (default core 2-5, total <= 8, hard ceiling 10).
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

# Team size policy (M6.4 / Section 13).
DEFAULT_TEAM_CEILING = 8      # typical total ceiling
HARD_TEAM_CEILING = 10        # hard default ceiling (override only by explicit pack)
CORE_TEAM_MIN = 2             # project-planner + orchestrator
CORE_TEAM_MAX = 5
SPECIALIST_MAX = 5

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


@dataclass(frozen=True)
class ResourceSelectionResult:
    """Result of resolving project type + capabilities + stack bundle to resources."""

    resources: list[ResourceSelection] = field(default_factory=list)
    project_type_id: str = ""
    selected_capability_ids: list[str] = field(default_factory=list)
    stack_bundle_id: str = ""
    execution_pack_id: Optional[str] = None
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def resource_map(self) -> dict[tuple[str, str], ResourceSelection]:
        """Map keyed by (type, id) for collision-safe lookup."""
        return {(r.type, r.id): r for r in self.resources}


class ResourceResolver:
    """Deterministic, bounded resource resolver.

    Selects a small active team from the full canonical registry
    (bundled + agency-agents). Never activates the entire catalog.

    Resolution priority (§12):
      1. Execution pack core roles (highest priority)
      2. Project-type-relevant bundled resources
      3. Capability-driven bundled resources
      4. Agency specialists relevant to project type (division match)
      5. Quality/safety roles (implied by capabilities)

    Team size policy (§13):
      Core 2-5 agents, specialists 0-5 agents, total <= 8,
      hard ceiling 10 agents.
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

        # --- 1. Execution pack core roles (highest priority) --------------
        pack = None
        if execution_pack_id is not None and self.pack_registry is not None:
            pack = self.pack_registry.get(execution_pack_id)
            if pack is None:
                errors.append(
                    f"Execution pack not found: {execution_pack_id!r}"
                )
            else:
                for role_id in pack.core_roles:
                    key = ("agent", role_id)
                    if key in seen:
                        continue
                    seen.add(key)
                    resources.append(
                        self._make_selection(
                            "agent", role_id,
                            f"execution-pack:{pack.id} core-role",
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
                    )
                )

        # --- 3. Project-type-relevant bundled resources --------------------
        pt_resources = self._load_project_type_resources(project_type_id)
        for res_def in pt_resources:
            rid = res_def.get("id", "")
            rtype = res_def.get("type", "")
            reason = res_def.get("reason", f"project-type:{project_type_id}")
            if not rid or not rtype:
                errors.append(f"Invalid resource entry: missing id or type: {res_def}")
                continue
            key = (rtype, rid)
            if key in seen:
                continue
            seen.add(key)
            if not self._registry_has(rtype, rid):
                errors.append(f"Resource not found in registry: {rtype}:{rid}")
                continue
            resources.append(self._make_selection(rtype, rid, reason))

        # --- 4. Capability-driven bundled resources -----------------------
        cap_to_resources = self._build_capability_map(pt_resources)
        for cap_id in selected_caps:
            for defn in cap_to_resources.get(cap_id, []):
                rid = defn["id"]
                rtype = defn["type"]
                key = (rtype, rid)
                if key in seen:
                    continue
                if not self._registry_has(rtype, rid):
                    errors.append(
                        f"Resource not found in registry: {rtype}:{rid} "
                        f"(capability: {cap_id})"
                    )
                    continue
                seen.add(key)
                resources.append(self._make_selection(rtype, rid, defn["reason"]))

        # --- 5. Agency specialists relevant to project type --------------
        agency_agents = self._select_agency_specialists(project_type_id)
        # Count agents so far (pack core + optional + bundled agents)
        agent_count = sum(1 for r in resources if r.type == "agent")
        agent_slots_remaining = max(0, HARD_TEAM_CEILING - agent_count)
        for agent in agency_agents[:agent_slots_remaining]:
            if agent_count >= HARD_TEAM_CEILING:
                break
            key = ("agent", agent.id)
            if key in seen:
                continue
            seen.add(key)
            agent_count += 1
            reason = f"agency-division:{agent.division} relevance to project-type:{project_type_id}"
            resources.append(self._make_selection("agent", agent.id, reason))

        # --- 6. Enforce team size ceiling ---------------------------------
        if agent_count > HARD_TEAM_CEILING:
            # Should not happen due to slots logic, but keep as safety net.
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
        )

    # -- helpers ------------------------------------------------------------
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

    def _build_capability_map(
        self, pt_resources: list[dict]
    ) -> dict[str, list[dict]]:
        cap_to_resources: dict[str, list[dict]] = {}
        for defn in pt_resources:
            reason = defn.get("reason", "")
            if reason.startswith("capability:"):
                cap_id = reason[len("capability:"):]
                cap_to_resources.setdefault(cap_id, []).append(defn)
        return cap_to_resources

    def _select_agency_specialists(
        self, project_type_id: str
    ) -> list:
        """Select agency agents relevant to the project type.

        Returns agents sorted deterministically by id. Limited to
        SPECIALIST_MAX entries (caller enforces total ceiling).
        """
        relevant_divisions = {
            div for div, pts in DIVISION_PROJECT_TYPE_RELEVANCE.items()
            if project_type_id in pts
        }
        if not relevant_divisions:
            return []

        candidates: list = []
        for agent in self.registry.list_agents():
            if agent.division in relevant_divisions:
                candidates.append(agent)
        candidates.sort(key=lambda a: a.id)
        return candidates[:SPECIALIST_MAX]

    def _make_selection(
        self,
        rtype: str,
        rid: str,
        reason: str,
    ) -> ResourceSelection:
        """Build a ResourceSelection, populating name/description + provenance
        from the registry ref (falls back to bundled defaults when ref absent)."""
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
    registry = ResourceCatalogLoader(resources_root, agency_catalog_path).load()

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

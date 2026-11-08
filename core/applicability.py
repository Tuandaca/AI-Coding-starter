"""
Generalized resource applicability engine (Section 4 / Section 5).

Implements a single canonical applicability evaluator shared by every resource
type (agents, skills, rules, workflows, scripts, shared modules, templates,
execution packs). No per-type incompatible systems.

Pipeline (Section 4):

    ELIGIBILITY FILTER  ->  RELEVANCE SCORING  ->  TEAM / RESOURCE BUDGET  ->  FINAL SELECTION

A resource that is not eligible must NEVER enter scoring (Section 6).

A resource's applicability is a property of the resource itself (type + id),
not of the project type that lists it as a candidate. Candidate listing
(resource-requirements.yaml per project type) and eligibility
(core/applicability.py) are deliberately separated so cross-domain
contamination is blocked at the filter, not hoped-for at scoring time.

Canonical applicability records live in ``catalog/resource-applicability.yaml``,
keyed by (type, id). The :class:`ApplicabilityCatalog` loads them. Resources
absent from the catalog have no recorded metadata and remain eligible by
default (backward compatibility).

``task_tags`` is reserved for task-scoped resolution and is explicitly
UNSUPPORTED for project-level resolution: the resolver always passes an empty
task_tags context, so the task_tags_any axis never fires during project
creation. It is retained in the schema for a future task-scoped resolution
layer (M9/M10 Advisor), not because it influences project-level selection.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ApplicabilityContext:
    """The resolved project context used to test resource eligibility."""

    project_type: str
    capabilities: frozenset[str]
    stack_tags: frozenset[str]
    task_tags: frozenset[str]
    # Resource (type, id) pairs already selected for this project. Used to
    # evaluate `requires` / `conflicts_with`.
    selected: frozenset[tuple[str, str]] = field(default_factory=frozenset)


@dataclass(frozen=True)
class Applicability:
    """
    Resource-centric applicability metadata.

    A resource is eligible for a project context only when every applicable
    rule below passes. Empty lists mean "no constraint" for that axis.
    """

    id: str
    type: str  # agent | skill | rule | workflow | script | template | shared-module

    # --- Project type axes -------------------------------------------------
    # Non-empty means the resource is ONLY applicable to these project types.
    project_types_include: frozenset[str] = field(default_factory=frozenset)
    # Explicitly forbidden project types (takes precedence over include).
    project_types_exclude: frozenset[str] = field(default_factory=frozenset)

    # --- Capability axes ---------------------------------------------------
    # At least one of these must be selected (when non-empty).
    capabilities_any: frozenset[str] = field(default_factory=frozenset)
    # All of these must be selected (when non-empty).
    capabilities_all: frozenset[str] = field(default_factory=frozenset)
    # None of these may be selected (when non-empty).
    capabilities_none: frozenset[str] = field(default_factory=frozenset)

    # --- Stack tag axes ----------------------------------------------------
    stack_tags_any: frozenset[str] = field(default_factory=frozenset)
    stack_tags_all: frozenset[str] = field(default_factory=frozenset)

    # --- Task tag axes -----------------------------------------------------
    task_tags_any: frozenset[str] = field(default_factory=frozenset)

    # --- Reusability -------------------------------------------------------
    # True: cross-domain resource that may apply to many project types
    # (e.g. accessibility, testing, performance, deployment).
    reusable: bool = False
    # True: applies to every project type regardless of include/exclude.
    is_global: bool = False

    # --- Dependency / conflict axes ----------------------------------------
    # (type, id) resource pairs that must already be selected.
    requires: frozenset[tuple[str, str]] = field(default_factory=frozenset)
    # (type, id) resource pairs that must NOT be selected.
    conflicts_with: frozenset[tuple[str, str]] = field(default_factory=frozenset)

    def is_eligible(self, ctx: ApplicabilityContext) -> bool:
        """Return True when this resource is eligible for the given context.

        Ineligible resources never enter scoring (Section 6 invariant).

        Axis semantics (AND/OR):
          * project_types_include / project_types_exclude: OR within include
            (type must be one of the listed), exclusion wins over inclusion.
          * capabilities_any: OR (at least one selected). capabilities_all: AND
            (every one selected). capabilities_none: OR forbids (none selected).
          * stack_tags_any: OR. stack_tags_all: AND.
          * task_tags_any: OR. Reserved for task-scoped resolution; empty at
            project level (see module note).
          * requires: AND (every listed (type, id) must already be selected).
          * conflicts_with: OR forbids (none may already be selected).

        A global resource is exempt from project-type / capability / stack /
        task gating (it applies to every project type), but it is NOT exempt
        from dependency / conflict safety constraints.
        """
        project_type = ctx.project_type
        caps = ctx.capabilities
        tags = ctx.stack_tags
        selected = ctx.selected

        # Global resources apply everywhere, but still obey requires /
        # conflicts_with (they must not bypass dependency/conflict safety).
        if self.is_global:
            if self.requires and not (self.requires <= selected):
                return False
            if self.conflicts_with and (self.conflicts_with & selected):
                return False
            return True

        # Explicit project-type exclusion wins over inclusion.
        if project_type in self.project_types_exclude:
            return False

        # Project-type inclusion: if declared, the type must be present.
        if self.project_types_include and project_type not in self.project_types_include:
            return False

        # Capability axes.
        if self.capabilities_any and not (caps & self.capabilities_any):
            return False
        if self.capabilities_all and not (caps >= self.capabilities_all):
            return False
        if self.capabilities_none and (caps & self.capabilities_none):
            return False

        # Stack tag axes.
        if self.stack_tags_any and not (tags & self.stack_tags_any):
            return False
        if self.stack_tags_all and not (tags >= self.stack_tags_all):
            return False

        # Task tag axes (reserved for task-scoped resolution; empty at
        # project level, so this axis never fires during project creation).
        if self.task_tags_any and not (ctx.task_tags & self.task_tags_any):
            return False

        # Dependency axes: must see resources selected earlier in the same
        # resolution (ctx.selected is threaded in by the resolver).
        if self.requires and not (self.requires <= selected):
            return False
        if self.conflicts_with and (self.conflicts_with & selected):
            return False

        return True


@dataclass(frozen=True)
class ApplicabilityResult:
    """Outcome of evaluating one resource's eligibility."""

    applicable: bool
    id: str
    type: str
    reason: str  # human-readable explanation of the eligibility decision


def is_resource_eligible(
    applicability: Optional[Applicability],
    ctx: ApplicabilityContext,
) -> ApplicabilityResult:
    """
    Canonical eligibility check (Section 5 concept: is_resource_eligible).

    Every resource type passes through this single evaluator. When
    ``applicability`` is None (no metadata recorded), the resource is treated
    as eligible for backward compatibility.
    """
    if applicability is None:
        return ApplicabilityResult(
            applicable=True,
            id="",
            type="",
            reason="no applicability metadata recorded; eligible by default",
        )
    if applicability.is_eligible(ctx):
        return ApplicabilityResult(
            applicable=True,
            id=applicability.id,
            type=applicability.type,
            reason="applicable to project context",
        )
    # Build a concise ineligibility reason.
    parts: list[str] = []
    if applicability.project_types_exclude and ctx.project_type in applicability.project_types_exclude:
        parts.append(
            f"project-type {ctx.project_type!r} explicitly excluded"
        )
    if (
        applicability.project_types_include
        and ctx.project_type not in applicability.project_types_include
    ):
        parts.append(
            f"project-type {ctx.project_type!r} not in "
            f"include {sorted(applicability.project_types_include)}"
        )
    caps = ctx.capabilities
    if applicability.capabilities_any and not (caps & applicability.capabilities_any):
        parts.append(
            f"requires one of {sorted(applicability.capabilities_any)}"
        )
    if applicability.capabilities_all and not (caps >= applicability.capabilities_all):
        parts.append(
            f"requires all of {sorted(applicability.capabilities_all)}"
        )
    if applicability.capabilities_none and (caps & applicability.capabilities_none):
        parts.append(
            f"forbidden capability in {sorted(applicability.capabilities_none)}"
        )
    tags = ctx.stack_tags
    if applicability.stack_tags_any and not (tags & applicability.stack_tags_any):
        parts.append(
            f"requires one of stack tag {sorted(applicability.stack_tags_any)}"
        )
    if applicability.stack_tags_all and not (tags >= applicability.stack_tags_all):
        parts.append(
            f"requires all stack tags {sorted(applicability.stack_tags_all)}"
        )
    if applicability.task_tags_any and not (ctx.task_tags & applicability.task_tags_any):
        parts.append(
            f"requires one of task tag {sorted(applicability.task_tags_any)}"
        )
    if applicability.requires and not (applicability.requires <= ctx.selected):
        parts.append(
            f"requires already-selected {sorted(applicability.requires)}"
        )
    if applicability.conflicts_with and (applicability.conflicts_with & ctx.selected):
        parts.append(
            f"conflicts with already-selected {sorted(applicability.conflicts_with)}"
        )
    reason = "; ".join(parts) if parts else "ineligible for project context"
    return ApplicabilityResult(
        applicable=False,
        id=applicability.id,
        type=applicability.type,
        reason=reason,
    )


# ---------------------------------------------------------------------------
# Reusable resource declarations (Section 7).
#
# Cross-domain resources that should remain applicable to many project types
# when their capability/stack conditions are met. These are markers used by
# the loader to stamp `reusable=True` on resources that match.
# ---------------------------------------------------------------------------

REUSABLE_RESOURCE_IDS: frozenset[str] = frozenset({
    # Cross-domain concerns applicable to most UI / web project types.
    "accessibility",
    "testing",
    "performance",
    "security",
    "deployment",
    "design-system",
    "seo",
    "observability",
    "code-review",
    # Bundled resource ids that are genuinely reusable infrastructure.
    "project-planner",
    "orchestrator",
    "create",
    "deploy",
    "checklist",
    "auto_preview",
    "lint",
})


# ---------------------------------------------------------------------------
# Canonical applicability catalog loader (Section 5).
# ---------------------------------------------------------------------------

DEFAULT_APPLICABILITY_CATALOG_PATH = (
    Path(__file__).resolve().parent.parent / "catalog" / "resource-applicability.yaml"
)


class ApplicabilityCatalog:
    """Canonical resource-centric applicability records keyed by (type, id).

    Loaded once from ``catalog/resource-applicability.yaml``. The resolver
    consults this catalog (and only this catalog) for applicability metadata;
    per-entry ``when`` activation conditions remain in
    resource-requirements.yaml and are evaluated separately, so there is no
    ambiguous duplicate gating between the two.
    """

    def __init__(self, records: dict[tuple[str, str], Applicability]) -> None:
        self._records = dict(records)

    @classmethod
    def load(cls, path: Path | str = DEFAULT_APPLICABILITY_CATALOG_PATH) -> "ApplicabilityCatalog":
        """Load applicability records from the canonical catalog file.

        Returns an empty catalog (all resources eligible by default) when the
        file is absent or unreadable, so the resolver never hard-fails on
        missing metadata.
        """
        path = Path(path)
        records: dict[tuple[str, str], Applicability] = {}
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            return cls(records)
        if not isinstance(data, dict):
            return cls(records)
        for item in data.get("resources", []):
            if not isinstance(item, dict):
                continue
            rid = item.get("id")
            rtype = item.get("type")
            if not rid or not rtype:
                continue
            key = (str(rtype), str(rid))
            records[key] = Applicability(
                id=str(rid),
                type=str(rtype),
                project_types_include=frozenset(
                    str(p) for p in (item.get("project_types_include") or [])
                ),
                project_types_exclude=frozenset(
                    str(p) for p in (item.get("project_types_exclude") or [])
                ),
                capabilities_any=frozenset(
                    str(c) for c in (item.get("capabilities_any") or [])
                ),
                capabilities_all=frozenset(
                    str(c) for c in (item.get("capabilities_all") or [])
                ),
                capabilities_none=frozenset(
                    str(c) for c in (item.get("capabilities_none") or [])
                ),
                stack_tags_any=frozenset(
                    str(t) for t in (item.get("stack_tags_any") or [])
                ),
                stack_tags_all=frozenset(
                    str(t) for t in (item.get("stack_tags_all") or [])
                ),
                task_tags_any=frozenset(
                    str(t) for t in (item.get("task_tags_any") or [])
                ),
                reusable=bool(item.get("reusable", False)),
                is_global=bool(item.get("is_global", False) or item.get("global", False)),
                requires=frozenset(
                    (str(r[0]), str(r[1]))
                    for r in (item.get("requires") or [])
                    if isinstance(r, list) and len(r) == 2
                ),
                conflicts_with=frozenset(
                    (str(c[0]), str(c[1]))
                    for c in (item.get("conflicts_with") or [])
                    if isinstance(c, list) and len(c) == 2
                ),
            )
        return cls(records)

    def get(self, rtype: str, rid: str) -> Optional[Applicability]:
        """Return the applicability record for ``(type, id)``, or None."""
        return self._records.get((rtype, rid))

    def __contains__(self, key: tuple[str, str]) -> bool:
        return key in self._records

    def __len__(self) -> int:
        return len(self._records)

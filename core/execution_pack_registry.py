"""
Execution pack registry / catalog layer (M6.5).

Loads execution pack definitions from ``catalog/execution-packs.yaml`` and
validates them against the resource registry (every core/optional role slug
must resolve to a real agent in the catalog).

Standard library only. No network. Deterministic.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from core.resource_registry import ResourceRegistry


@dataclass(frozen=True)
class OptionalRoleRef:
    """A specialist role with activation conditions within a pack."""

    resource_id: str
    activation: str  # always, as-needed, post-fix, capability-triggered, stack-triggered
    trigger_capabilities: list[str] = field(default_factory=list)
    trigger_stack_bundles: list[str] = field(default_factory=list)

    VALID_ACTIVATIONS = frozenset([
        "always", "as-needed", "post-fix",
        "capability-triggered", "stack-triggered",
    ])

    def __post_init__(self) -> None:
        if self.activation not in self.VALID_ACTIVATIONS:
            raise ValueError(f"Invalid activation: {self.activation!r}")
        if not self.resource_id:
            raise ValueError("Optional role resource_id cannot be empty")


@dataclass(frozen=True)
class ExecutionPackRef:
    """A resolved execution pack definition."""

    id: str
    name: str
    description: str
    mode: str = "continuous"
    duration: str = ""
    summary: str = ""
    doc: Optional[str] = None
    upstream: Optional[str] = None
    upstream_commit: Optional[str] = None
    core_roles: list[str] = field(default_factory=list)
    optional_roles: list[OptionalRoleRef] = field(default_factory=list)
    activation_project_types: list[str] = field(default_factory=list)
    activation_capabilities: list[str] = field(default_factory=list)
    activation_stack_bundles: list[str] = field(default_factory=list)
    quality_gates: list[str] = field(default_factory=list)
    workflow: list[str] = field(default_factory=list)

    VALID_MODES = frozenset(["continuous", "time-boxed", "event-driven", "on-demand"])

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Execution pack name cannot be empty")
        if self.mode not in self.VALID_MODES:
            raise ValueError(f"Invalid mode: {self.mode!r}")
        if not self.core_roles:
            raise ValueError("Execution pack must have at least one core role")
        # No duplicate core roles
        if len(self.core_roles) != len(set(self.core_roles)):
            raise ValueError(f"Duplicate core roles in pack {self.id!r}")
        # No duplicate optional role resource_ids
        opt_ids = [r.resource_id for r in self.optional_roles]
        if len(opt_ids) != len(set(opt_ids)):
            raise ValueError(f"Duplicate optional roles in pack {self.id!r}")
        # Quality gates non-empty
        if not self.quality_gates:
            raise ValueError(f"Execution pack {self.id!r} must have non-empty quality_gates")
        # Workflow non-empty
        if not self.workflow:
            raise ValueError(f"Execution pack {self.id!r} must have non-empty workflow")


class ExecutionPackRegistry:
    """Registry of validated execution packs keyed by pack id."""

    def __init__(self) -> None:
        self._packs: dict[str, ExecutionPackRef] = {}
        self._errors: list[str] = []

    def add(self, pack: ExecutionPackRef) -> None:
        self._packs[pack.id] = pack

    def get(self, pack_id: str) -> Optional[ExecutionPackRef]:
        return self._packs.get(pack_id)

    def all(self) -> list[ExecutionPackRef]:
        return sorted(self._packs.values(), key=lambda p: p.id)

    def __len__(self) -> int:
        return len(self._packs)

    @property
    def errors(self) -> list[str]:
        return list(self._errors)

    def is_valid(self) -> bool:
        return not self._errors


class ExecutionPackLoader:
    """Loads and validates execution packs from ``catalog/execution-packs.yaml``."""

    def __init__(
        self,
        packs_path: Path,
        resource_registry: ResourceRegistry,
    ) -> None:
        self.packs_path = Path(packs_path)
        self.resource_registry = resource_registry

    def load(self) -> ExecutionPackRegistry:
        """Load packs and validate every role slug against the resource registry.

        Returns a registry (possibly with errors recorded if slugs are stale).
        """
        registry = ExecutionPackRegistry()
        if not self.packs_path.is_file():
            registry._errors.append(f"Execution packs file not found: {self.packs_path}")
            return registry

        with open(self.packs_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)

        packs = data.get("execution_packs", [])
        if not isinstance(packs, list):
            registry._errors.append("'execution_packs' must be a list")
            return registry

        for item in packs:
            if not isinstance(item, dict):
                registry._errors.append("Each execution pack must be an object")
                continue
            try:
                pack = self._build_pack(item)
            except ValueError as exc:
                registry._errors.append(str(exc))
                continue

            # Validate every role slug resolves to a real agent in the registry.
            for role_id in pack.core_roles:
                ref = self.resource_registry.get("agent", role_id)
                if ref is None:
                    registry._errors.append(
                        f"Pack {pack.id}: core role {role_id!r} not found in resource registry"
                    )
            for opt_role in pack.optional_roles:
                ref = self.resource_registry.get("agent", opt_role.resource_id)
                if ref is None:
                    registry._errors.append(
                        f"Pack {pack.id}: optional role {opt_role.resource_id!r} "
                        f"not found in resource registry"
                    )

            registry.add(pack)

        return registry

    def _build_pack(self, item: dict) -> ExecutionPackRef:
        core_roles = list(item.get("core_roles", []) or [])
        optional_raw = list(item.get("optional_roles", []) or [])
        optional_roles: list[OptionalRoleRef] = []
        for opt in optional_raw:
            if not isinstance(opt, dict):
                continue
            optional_roles.append(
                OptionalRoleRef(
                    resource_id=str(opt.get("resource_id", "")),
                    activation=str(opt.get("activation", "as-needed")),
                    trigger_capabilities=list(opt.get("trigger_capabilities", []) or []),
                    trigger_stack_bundles=list(opt.get("trigger_stack_bundles", []) or []),
                )
            )
        activation = item.get("activation_conditions", {}) or {}
        return ExecutionPackRef(
            id=str(item["id"]),
            name=str(item["name"]),
            description=str(item.get("description", "")),
            mode=str(item.get("mode", "continuous")),
            duration=str(item.get("duration", "")),
            summary=str(item.get("summary", "")),
            doc=item.get("doc"),
            upstream=item.get("upstream"),
            upstream_commit=item.get("upstream_commit"),
            core_roles=core_roles,
            optional_roles=optional_roles,
            activation_project_types=list(activation.get("project_types", []) or []),
            activation_capabilities=list(activation.get("capabilities", []) or []),
            activation_stack_bundles=list(activation.get("stack_bundles", []) or []),
            quality_gates=list(item.get("quality_gates", []) or []),
            workflow=list(item.get("workflow", []) or []),
        )


def build_default_pack_registry(
    packs_path: Optional[Path] = None,
    resource_registry: Optional[ResourceRegistry] = None,
) -> ExecutionPackRegistry:
    """Build the default execution pack registry."""
    if packs_path is None:
        packs_path = (
            Path(__file__).resolve().parent.parent.parent / "catalog" / "execution-packs.yaml"
        )
    if resource_registry is None:
        from core.resource_registry import build_default_registry
        resource_registry = build_default_registry()
    loader = ExecutionPackLoader(packs_path, resource_registry)
    return loader.load()

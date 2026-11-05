"""
Domain model for ExecutionPack entity.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from core.domain.contracts.id_policy import CanonicalId, make_id
from core.domain.contracts.errors import ValidationResult, UnknownReferenceError


@dataclass(frozen=True)
class OptionalRole:
    """A specialist role with activation conditions."""
    resource_id: CanonicalId
    activation: str  # always, as-needed, post-fix, capability-triggered, stack-triggered
    trigger_capabilities: List[CanonicalId] = field(default_factory=list)
    trigger_stack_bundles: List[CanonicalId] = field(default_factory=list)

    VALID_ACTIVATIONS = frozenset([
        "always", "as-needed", "post-fix",
        "capability-triggered", "stack-triggered"
    ])

    def __post_init__(self):
        if self.activation not in self.VALID_ACTIVATIONS:
            raise ValueError(f"Invalid activation: {self.activation}. Valid: {self.VALID_ACTIVATIONS}")
        if not isinstance(self.resource_id, CanonicalId):
            raise TypeError("resource_id must be CanonicalId")
        for cap in self.trigger_capabilities:
            if not isinstance(cap, CanonicalId):
                raise TypeError("trigger_capabilities must be CanonicalId")
        for bundle in self.trigger_stack_bundles:
            if not isinstance(bundle, CanonicalId):
                raise TypeError("trigger_stack_bundles must be CanonicalId")

    @classmethod
    def from_dict(cls, data: dict) -> 'OptionalRole':
        return cls(
            resource_id=make_id(data["resource_id"]),
            activation=data["activation"],
            trigger_capabilities=[make_id(c) for c in data.get("trigger_capabilities", [])],
            trigger_stack_bundles=[make_id(b) for b in data.get("trigger_stack_bundles", [])]
        )

    def to_dict(self) -> dict:
        result = {
            "resource_id": str(self.resource_id),
            "activation": self.activation
        }
        if self.trigger_capabilities:
            result["trigger_capabilities"] = [str(c) for c in self.trigger_capabilities]
        if self.trigger_stack_bundles:
            result["trigger_stack_bundles"] = [str(b) for b in self.trigger_stack_bundles]
        return result


@dataclass(frozen=True)
class ActivationConditions:
    """Conditions under which an execution pack is recommended."""
    project_types: List[CanonicalId] = field(default_factory=list)
    capabilities: List[CanonicalId] = field(default_factory=list)
    stack_bundles: List[CanonicalId] = field(default_factory=list)

    def __post_init__(self):
        for lst, field_name in [
            (self.project_types, "project_types"),
            (self.capabilities, "capabilities"),
            (self.stack_bundles, "stack_bundles")
        ]:
            for item in lst:
                if not isinstance(item, CanonicalId):
                    raise TypeError(f"{field_name} must be CanonicalId, got {type(item)}")

    @classmethod
    def from_dict(cls, data: dict) -> 'ActivationConditions':
        return cls(
            project_types=[make_id(p) for p in data.get("project_types", [])],
            capabilities=[make_id(c) for c in data.get("capabilities", [])],
            stack_bundles=[make_id(b) for b in data.get("stack_bundles", [])]
        )

    def to_dict(self) -> dict:
        result = {}
        if self.project_types:
            result["project_types"] = [str(p) for p in self.project_types]
        if self.capabilities:
            result["capabilities"] = [str(c) for c in self.capabilities]
        if self.stack_bundles:
            result["stack_bundles"] = [str(b) for b in self.stack_bundles]
        return result


@dataclass(frozen=True)
class ExecutionPack:
    """
    Canonical ExecutionPack entity.

    Team execution pack — defines roles and activation conditions for a working mode.
    """
    id: CanonicalId
    name: str
    description: str
    schema_version: str = "1.0.0"
    mode: str = "continuous"
    duration: str = ""
    summary: str = ""
    core_roles: List[CanonicalId] = field(default_factory=list)
    optional_roles: List[OptionalRole] = field(default_factory=list)
    activation_conditions: ActivationConditions = field(default_factory=ActivationConditions)
    quality_gates: List[str] = field(default_factory=list)
    workflow: List[str] = field(default_factory=list)

    VALID_MODES = frozenset(["continuous", "time-boxed", "event-driven", "on-demand"])

    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("ExecutionPack name cannot be empty")
        if self.schema_version != "1.0.0":
            raise ValueError(f"Unsupported schema_version: {self.schema_version}")
        if self.mode not in self.VALID_MODES:
            raise ValueError(f"Invalid mode: {self.mode}. Valid: {self.VALID_MODES}")

        if not self.core_roles:
            raise ValueError("ExecutionPack must have at least one core role")

        for role in self.core_roles:
            if not isinstance(role, CanonicalId):
                raise TypeError("core_roles must be CanonicalId")

        for opt_role in self.optional_roles:
            if not isinstance(opt_role, OptionalRole):
                raise TypeError("optional_roles must be OptionalRole")

        if not isinstance(self.activation_conditions, ActivationConditions):
            raise TypeError("activation_conditions must be ActivationConditions")

        for gate in self.quality_gates:
            if not isinstance(gate, str) or not gate:
                raise ValueError("quality_gates must be non-empty strings")

        for step in self.workflow:
            if not isinstance(step, str) or not step:
                raise ValueError("workflow steps must be non-empty strings")

    @classmethod
    def from_dict(cls, data: dict) -> 'ExecutionPack':
        return cls(
            id=make_id(data["id"]),
            name=data["name"],
            description=data["description"],
            schema_version=data.get("schema_version", "1.0.0"),
            mode=data.get("mode", "continuous"),
            duration=data.get("duration", ""),
            summary=data.get("summary", ""),
            core_roles=[make_id(r) for r in data.get("core_roles", [])],
            optional_roles=[OptionalRole.from_dict(r) for r in data.get("optional_roles", [])],
            activation_conditions=ActivationConditions.from_dict(data.get("activation_conditions", {})),
            quality_gates=data.get("quality_gates", []),
            workflow=data.get("workflow", [])
        )

    def to_dict(self) -> dict:
        result = {
            "schema_version": self.schema_version,
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "mode": self.mode,
            "duration": self.duration,
            "summary": self.summary,
            "core_roles": [str(r) for r in self.core_roles],
            "optional_roles": [r.to_dict() for r in self.optional_roles],
            "activation_conditions": self.activation_conditions.to_dict(),
            "quality_gates": self.quality_gates,
            "workflow": self.workflow
        }
        return result

    def validate(self, known_resources: List[CanonicalId],
                 known_capabilities: List[CanonicalId],
                 known_bundles: List[CanonicalId],
                 known_project_types: List[CanonicalId]) -> ValidationResult:
        """Validate this ExecutionPack against known catalog entities."""
        result = ValidationResult.success()

        known_res = set(known_resources)
        known_cap = set(known_capabilities)
        known_bundles = set(known_bundles)
        known_pts = set(known_project_types)

        # Check core roles
        for role in self.core_roles:
            if role not in known_res:
                result = result.add_error(UnknownReferenceError(
                    reference=str(role), reference_type="resource",
                    available=[str(r) for r in known_resources]
                ))

        # Check optional roles
        for opt_role in self.optional_roles:
            if opt_role.resource_id not in known_res:
                result = result.add_error(UnknownReferenceError(
                    reference=str(opt_role.resource_id), reference_type="resource",
                    available=[str(r) for r in known_resources]
                ))

            for cap in opt_role.trigger_capabilities:
                if cap not in known_cap:
                    result = result.add_error(UnknownReferenceError(
                        reference=str(cap), reference_type="capability",
                        available=[str(c) for c in known_capabilities]
                    ))

            for bundle in opt_role.trigger_stack_bundles:
                if bundle not in known_bundles:
                    result = result.add_error(UnknownReferenceError(
                        reference=str(bundle), reference_type="stack_bundle",
                        available=[str(b) for b in known_bundles]
                    ))

        # Check activation conditions
        for pt in self.activation_conditions.project_types:
            if pt not in known_pts:
                result = result.add_error(UnknownReferenceError(
                    reference=str(pt), reference_type="project_type",
                    available=[str(p) for p in known_project_types]
                ))

        for cap in self.activation_conditions.capabilities:
            if cap not in known_cap:
                result = result.add_error(UnknownReferenceError(
                    reference=str(cap), reference_type="capability",
                    available=[str(c) for c in known_capabilities]
                ))

        for bundle in self.activation_conditions.stack_bundles:
            if bundle not in known_bundles:
                result = result.add_error(UnknownReferenceError(
                    reference=str(bundle), reference_type="stack_bundle",
                    available=[str(b) for b in known_bundles]
                ))

        return result

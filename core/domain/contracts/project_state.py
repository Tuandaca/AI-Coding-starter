"""
Domain model for Portable Project State (project.yaml).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from core.domain.contracts.id_policy import CanonicalId, make_id
from core.domain.contracts.errors import ValidationResult, UnknownReferenceError


@dataclass(frozen=True)
class RuntimePreferences:
    """Runtime adapter preferences."""
    primary: Optional[CanonicalId] = None
    fallbacks: List[CanonicalId] = field(default_factory=list)
    project_local_only: bool = True

    def __post_init__(self):
        if self.primary is not None and not isinstance(self.primary, CanonicalId):
            raise TypeError("primary must be CanonicalId or None")
        for fb in self.fallbacks:
            if not isinstance(fb, CanonicalId):
                raise TypeError("fallbacks must be CanonicalId")

    @classmethod
    def from_dict(cls, data: dict) -> 'RuntimePreferences':
        return cls(
            primary=make_id(data["primary"]) if data.get("primary") else None,
            fallbacks=[make_id(f) for f in data.get("fallbacks", [])],
            project_local_only=data.get("project_local_only", True)
        )

    def to_dict(self) -> dict:
        result = {"project_local_only": self.project_local_only}
        if self.primary:
            result["primary"] = str(self.primary)
        if self.fallbacks:
            result["fallbacks"] = [str(f) for f in self.fallbacks]
        return result


@dataclass(frozen=True)
class ProjectSpec:
    """
    Portable project specification — MACHINE AUTHORITATIVE.

    This is the canonical project.yaml content.
    """
    id: CanonicalId
    name: str
    created_at: str  # ISO 8601
    updated_at: str  # ISO 8601
    schema_version: str = "1.0.0"
    description: str = ""
    project_type: Optional[CanonicalId] = None
    capabilities: List[CanonicalId] = field(default_factory=list)
    stack_bundle: Optional[CanonicalId] = None
    technology_overrides: Dict[str, CanonicalId] = field(default_factory=dict)
    runtime_preferences: RuntimePreferences = field(default_factory=RuntimePreferences)
    provider_preferences: Dict[str, CanonicalId] = field(default_factory=dict)

    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("Project name cannot be empty")
        if self.schema_version != "1.0.0":
            raise ValueError(f"Unsupported schema_version: {self.schema_version}")

        # Validate timestamps are ISO format
        for ts_field, ts_value in [("created_at", self.created_at), ("updated_at", self.updated_at)]:
            try:
                datetime.fromisoformat(ts_value.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError(f"{ts_field} must be valid ISO 8601 datetime")

        # Validate IDs
        if self.project_type and not isinstance(self.project_type, CanonicalId):
            raise TypeError("project_type must be CanonicalId or None")
        if self.stack_bundle and not isinstance(self.stack_bundle, CanonicalId):
            raise TypeError("stack_bundle must be CanonicalId or None")

        for cap in self.capabilities:
            if not isinstance(cap, CanonicalId):
                raise TypeError("capabilities must be CanonicalId")

        for role, tech in self.technology_overrides.items():
            if not isinstance(tech, CanonicalId):
                raise TypeError(f"technology_overrides['{role}'] must be CanonicalId")

        if not isinstance(self.runtime_preferences, RuntimePreferences):
            raise TypeError("runtime_preferences must be RuntimePreferences")

        for cap, provider in self.provider_preferences.items():
            if not isinstance(provider, CanonicalId):
                raise TypeError(f"provider_preferences['{cap}'] must be CanonicalId")

    @classmethod
    def from_dict(cls, data: dict) -> 'ProjectSpec':
        project_data = data.get("project", data)  # Support both wrapped and direct

        return cls(
            id=make_id(project_data["id"]),
            name=project_data["name"],
            created_at=project_data["created_at"],
            updated_at=project_data["updated_at"],
            schema_version=project_data.get("schema_version", "1.0.0"),
            description=project_data.get("description", ""),
            project_type=make_id(project_data["project_type"]) if project_data.get("project_type") else None,
            capabilities=[make_id(c) for c in project_data.get("capabilities", [])],
            stack_bundle=make_id(project_data["stack_bundle"]) if project_data.get("stack_bundle") else None,
            technology_overrides={
                k: make_id(v) for k, v in project_data.get("technology_overrides", {}).items()
            },
            runtime_preferences=RuntimePreferences.from_dict(project_data.get("runtime_preferences", {})),
            provider_preferences={
                k: make_id(v) for k, v in project_data.get("provider_preferences", {}).items()
            }
        )

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "project": {
                "id": str(self.id),
                "name": self.name,
                "description": self.description,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
                "project_type": str(self.project_type) if self.project_type else None,
                "capabilities": [str(c) for c in self.capabilities],
                "stack_bundle": str(self.stack_bundle) if self.stack_bundle else None,
                "technology_overrides": {k: str(v) for k, v in self.technology_overrides.items()},
                "runtime_preferences": self.runtime_preferences.to_dict(),
                "provider_preferences": {k: str(v) for k, v in self.provider_preferences.items()}
            }
        }

    def validate(self, known_project_types: List[CanonicalId],
                 known_capabilities: List[CanonicalId],
                 known_bundles: List[CanonicalId],
                 known_technologies: List[CanonicalId],
                 known_runtimes: List[CanonicalId],
                 known_providers: List[CanonicalId]) -> ValidationResult:
        """Validate this ProjectSpec against known catalog entities."""
        result = ValidationResult.success()

        known_pts = set(known_project_types)
        known_caps = set(known_capabilities)
        known_bundles = set(known_bundles)
        known_tech = set(known_technologies)
        known_runtimes = set(known_runtimes)
        known_providers = set(known_providers)

        if self.project_type and self.project_type not in known_pts:
            result = result.add_error(UnknownReferenceError(
                reference=str(self.project_type), reference_type="project_type",
                available=[str(p) for p in known_project_types]
            ))

        for cap in self.capabilities:
            if cap not in known_caps:
                result = result.add_error(UnknownReferenceError(
                    reference=str(cap), reference_type="capability",
                    available=[str(c) for c in known_capabilities]
                ))

        if self.stack_bundle and self.stack_bundle not in known_bundles:
            result = result.add_error(UnknownReferenceError(
                reference=str(self.stack_bundle), reference_type="stack_bundle",
                available=[str(b) for b in known_bundles]
            ))

        for role, tech in self.technology_overrides.items():
            if tech not in known_tech:
                result = result.add_error(UnknownReferenceError(
                    reference=str(tech), reference_type="technology",
                    available=[str(t) for t in known_technologies]
                ))

        if self.runtime_preferences.primary and self.runtime_preferences.primary not in known_runtimes:
            result = result.add_error(UnknownReferenceError(
                reference=str(self.runtime_preferences.primary), reference_type="runtime_adapter",
                available=[str(r) for r in known_runtimes]
            ))

        for fb in self.runtime_preferences.fallbacks:
            if fb not in known_runtimes:
                result = result.add_error(UnknownReferenceError(
                    reference=str(fb), reference_type="runtime_adapter",
                    available=[str(r) for r in known_runtimes]
                ))

        for cap, provider in self.provider_preferences.items():
            if provider not in known_providers:
                result = result.add_error(UnknownReferenceError(
                    reference=str(provider), reference_type="capability_provider",
                    available=[str(p) for p in known_providers]
                ))

        return result

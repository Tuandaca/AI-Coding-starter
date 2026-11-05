"""
Domain model for StackBundle entity.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from core.domain.contracts.id_policy import validate_id, CanonicalId, make_id
from core.domain.contracts.errors import ValidationResult, UnknownReferenceError


@dataclass(frozen=True)
class StackBundle:
    """
    Canonical StackBundle entity.

    One coherent, validated technology combination — NOT an arbitrary list of unrelated presets.
    """
    id: CanonicalId
    name: str
    description: str
    technologies: Dict[str, CanonicalId]  # role -> technology ID
    schema_version: str = "1.0.0"
    project_types: List[CanonicalId] = field(default_factory=list)
    capabilities: List[CanonicalId] = field(default_factory=list)
    profile: str = "balanced"
    constraints: List[str] = field(default_factory=list)
    tradeoffs: List[str] = field(default_factory=list)
    incompatible_with: List[CanonicalId] = field(default_factory=list)

    # Required technology roles
    REQUIRED_ROLES = frozenset(["frontend", "backend", "database"])

    # Optional technology roles
    OPTIONAL_ROLES = frozenset([
        "orm", "cache", "queue", "search", "auth", "payments",
        "ai", "vector_database", "hosting", "styling", "testing"
    ])

    ALL_ROLES = REQUIRED_ROLES | OPTIONAL_ROLES

    VALID_PROFILES = frozenset(["fastest-mvp", "balanced", "scalable", "minimal", "custom"])

    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("StackBundle name cannot be empty")
        if not self.description or not self.description.strip():
            raise ValueError("StackBundle description cannot be empty")
        if self.schema_version != "1.0.0":
            raise ValueError(f"Unsupported schema_version: {self.schema_version}")
        if self.profile not in self.VALID_PROFILES:
            raise ValueError(f"Invalid profile '{self.profile}'. Valid: {self.VALID_PROFILES}")

        # Validate required roles present
        for role in self.REQUIRED_ROLES:
            if role not in self.technologies:
                raise ValueError(f"Missing required technology role: {role}")

        # Validate all roles are known
        for role in self.technologies:
            if role not in self.ALL_ROLES:
                raise ValueError(f"Unknown technology role: {role}. Valid: {self.ALL_ROLES}")

        # Validate all technology IDs are CanonicalId
        for role, tech_id in self.technologies.items():
            if not isinstance(tech_id, CanonicalId):
                raise TypeError(f"technology '{role}' must be CanonicalId, got {type(tech_id)}")

        # Validate list fields
        for lst, field_name in [
            (self.project_types, "project_types"),
            (self.capabilities, "capabilities"),
            (self.incompatible_with, "incompatible_with")
        ]:
            for item in lst:
                if not isinstance(item, CanonicalId):
                    raise TypeError(f"{field_name} must be CanonicalId, got {type(item)}")

        for constraint in self.constraints:
            if not isinstance(constraint, str) or not constraint:
                raise ValueError("Constraints must be non-empty strings")

        for tradeoff in self.tradeoffs:
            if not isinstance(tradeoff, str) or not tradeoff:
                raise ValueError("Tradeoffs must be non-empty strings")

    @classmethod
    def from_dict(cls, data: dict) -> 'StackBundle':
        technologies = {}
        for role, tech_id in data.get("technologies", {}).items():
            technologies[role] = make_id(tech_id)

        return cls(
            id=make_id(data["id"]),
            name=data["name"],
            description=data["description"],
            technologies=technologies,
            schema_version=data.get("schema_version", "1.0.0"),
            project_types=[make_id(p) for p in data.get("project_types", [])],
            capabilities=[make_id(c) for c in data.get("capabilities", [])],
            profile=data.get("profile", "balanced"),
            constraints=data.get("constraints", []),
            tradeoffs=data.get("tradeoffs", []),
            incompatible_with=[make_id(b) for b in data.get("incompatible_with", [])]
        )

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "technologies": {role: str(tid) for role, tid in self.technologies.items()},
            "project_types": [str(p) for p in self.project_types],
            "capabilities": [str(c) for c in self.capabilities],
            "profile": self.profile,
            "constraints": self.constraints,
            "tradeoffs": self.tradeoffs,
            "incompatible_with": [str(b) for b in self.incompatible_with]
        }

    def validate(self, known_technologies: List[CanonicalId],
                 known_project_types: List[CanonicalId],
                 known_capabilities: List[CanonicalId],
                 known_bundles: List[CanonicalId]) -> ValidationResult:
        """Validate this StackBundle against known catalog entities."""
        result = ValidationResult.success()

        known_tech_set = set(known_technologies)
        known_pt_set = set(known_project_types)
        known_cap_set = set(known_capabilities)
        known_bundle_set = set(known_bundles)

        # Validate all technology references
        for role, tech_id in self.technologies.items():
            if tech_id not in known_tech_set:
                result = result.add_error(UnknownReferenceError(
                    reference=str(tech_id),
                    reference_type="technology",
                    available=[str(t) for t in known_technologies]
                ))

        # Validate project types
        for pt in self.project_types:
            if pt not in known_pt_set:
                result = result.add_error(UnknownReferenceError(
                    reference=str(pt),
                    reference_type="project_type",
                    available=[str(p) for p in known_project_types]
                ))

        # Validate capabilities
        for cap in self.capabilities:
            if cap not in known_cap_set:
                result = result.add_error(UnknownReferenceError(
                    reference=str(cap),
                    reference_type="capability",
                    available=[str(c) for c in known_capabilities]
                ))

        # Validate incompatible bundles
        for bundle in self.incompatible_with:
            if bundle not in known_bundle_set:
                result = result.add_error(UnknownReferenceError(
                    reference=str(bundle),
                    reference_type="stack_bundle",
                    available=[str(b) for b in known_bundles]
                ))

        return result

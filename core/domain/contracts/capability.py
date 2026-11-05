"""
Domain model for Capability entity.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from core.domain.contracts.id_policy import validate_id, CanonicalId, make_id
from core.domain.contracts.errors import ValidationResult, UnknownReferenceError


@dataclass(frozen=True)
class Capability:
    """
    Canonical Capability entity.

    Describes what the project needs to do, not which vendor implements it.
    """
    id: CanonicalId
    name: str
    description: str
    schema_version: str = "1.0.0"
    category: str = "core"
    example_implementations: List[CanonicalId] = field(default_factory=list)
    requires: List[CanonicalId] = field(default_factory=list)
    conflicts: List[CanonicalId] = field(default_factory=list)
    implies: List[CanonicalId] = field(default_factory=list)
    recommended_for: List[CanonicalId] = field(default_factory=list)

    VALID_CATEGORIES = frozenset([
        "core", "data", "ai", "integration",
        "infrastructure", "ux", "security", "operations"
    ])

    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("Capability name cannot be empty")
        if not self.description or not self.description.strip():
            raise ValueError("Capability description cannot be empty")
        if self.schema_version != "1.0.0":
            raise ValueError(f"Unsupported schema_version: {self.schema_version}")
        if self.category not in self.VALID_CATEGORIES:
            raise ValueError(f"Invalid category '{self.category}'. Valid: {self.VALID_CATEGORIES}")

        # Validate all ID lists
        for lst, field_name in [
            (self.example_implementations, "example_implementations"),
            (self.requires, "requires"),
            (self.conflicts, "conflicts"),
            (self.implies, "implies"),
            (self.recommended_for, "recommended_for")
        ]:
            for item in lst:
                if not isinstance(item, CanonicalId):
                    raise TypeError(f"{field_name} must be CanonicalId, got {type(item)}")

    @classmethod
    def from_dict(cls, data: dict) -> 'Capability':
        """Create Capability from dictionary."""
        return cls(
            id=make_id(data["id"]),
            name=data["name"],
            description=data["description"],
            schema_version=data.get("schema_version", "1.0.0"),
            category=data.get("category", "core"),
            example_implementations=[make_id(c) for c in data.get("example_implementations", [])],
            requires=[make_id(c) for c in data.get("requires", [])],
            conflicts=[make_id(c) for c in data.get("conflicts", [])],
            implies=[make_id(c) for c in data.get("implies", [])],
            recommended_for=[make_id(c) for c in data.get("recommended_for", [])]
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "schema_version": self.schema_version,
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "example_implementations": [str(c) for c in self.example_implementations],
            "requires": [str(c) for c in self.requires],
            "conflicts": [str(c) for c in self.conflicts],
            "implies": [str(c) for c in self.implies],
            "recommended_for": [str(c) for c in self.recommended_for]
        }

    def validate(self, known_technologies: List[CanonicalId],
                 known_capabilities: List[CanonicalId],
                 known_project_types: List[CanonicalId]) -> ValidationResult:
        """Validate this Capability against known catalog entities."""
        result = ValidationResult.success()

        # Check example implementations (technologies)
        known_tech_set = set(known_technologies)
        for tech in self.example_implementations:
            if tech not in known_tech_set:
                result = result.add_error(UnknownReferenceError(
                    reference=str(tech),
                    reference_type="technology",
                    available=[str(t) for t in known_technologies]
                ))

        # Check requires capabilities
        known_cap_set = set(known_capabilities)
        for cap in self.requires:
            if cap not in known_cap_set:
                result = result.add_error(UnknownReferenceError(
                    reference=str(cap),
                    reference_type="capability",
                    available=[str(c) for c in known_capabilities]
                ))

        # Check conflicts
        for cap in self.conflicts:
            if cap not in known_cap_set:
                result = result.add_error(UnknownReferenceError(
                    reference=str(cap),
                    reference_type="capability",
                    available=[str(c) for c in known_capabilities]
                ))

        # Check implies
        for cap in self.implies:
            if cap not in known_cap_set:
                result = result.add_error(UnknownReferenceError(
                    reference=str(cap),
                    reference_type="capability",
                    available=[str(c) for c in known_capabilities]
                ))

        # Check recommended_for project types
        known_pt_set = set(known_project_types)
        for pt in self.recommended_for:
            if pt not in known_pt_set:
                result = result.add_error(UnknownReferenceError(
                    reference=str(pt),
                    reference_type="project_type",
                    available=[str(p) for p in known_project_types]
                ))

        return result

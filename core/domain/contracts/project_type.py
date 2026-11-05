"""
Domain model for ProjectType entity.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from core.domain.contracts.id_policy import validate_id, CanonicalId, make_id
from core.domain.contracts.errors import ValidationResult


@dataclass(frozen=True)
class ProjectType:
    """
    Canonical ProjectType entity.

    Describes what kind of product is being built.
    Stable IDs separate from version labels.
    """
    id: CanonicalId
    name: str
    description: str
    schema_version: str = "1.0.0"
    default_capabilities: List[CanonicalId] = field(default_factory=list)
    recommended_capabilities: List[CanonicalId] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    example_bundles: List[CanonicalId] = field(default_factory=list)

    def __post_init__(self):
        # Validate string fields
        if not self.name or not self.name.strip():
            raise ValueError("ProjectType name cannot be empty")
        if not self.description or not self.description.strip():
            raise ValueError("ProjectType description cannot be empty")

        # Validate schema_version
        if self.schema_version != "1.0.0":
            raise ValueError(f"Unsupported schema_version: {self.schema_version}")

        # Validate all capability IDs
        for cap in self.default_capabilities:
            if not isinstance(cap, CanonicalId):
                raise TypeError(f"default_capabilities must be CanonicalId, got {type(cap)}")
        for cap in self.recommended_capabilities:
            if not isinstance(cap, CanonicalId):
                raise TypeError(f"recommended_capabilities must be CanonicalId, got {type(cap)}")

        # Validate tags
        for tag in self.tags:
            if not isinstance(tag, str) or not tag:
                raise ValueError("Tags must be non-empty strings")

        # Validate example_bundles
        for bundle in self.example_bundles:
            if not isinstance(bundle, CanonicalId):
                raise TypeError(f"example_bundles must be CanonicalId, got {type(bundle)}")

    @classmethod
    def from_dict(cls, data: dict) -> 'ProjectType':
        """Create ProjectType from dictionary (e.g., parsed YAML/JSON)."""
        # Validate and convert ID
        project_type_id = make_id(data["id"])

        # Convert capability lists
        default_caps = [make_id(c) for c in data.get("default_capabilities", [])]
        recommended_caps = [make_id(c) for c in data.get("recommended_capabilities", [])]
        example_bundles = [make_id(b) for b in data.get("example_bundles", [])]

        return cls(
            id=project_type_id,
            name=data["name"],
            description=data["description"],
            schema_version=data.get("schema_version", "1.0.0"),
            default_capabilities=default_caps,
            recommended_capabilities=recommended_caps,
            tags=data.get("tags", []),
            example_bundles=example_bundles
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "schema_version": self.schema_version,
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "default_capabilities": [str(c) for c in self.default_capabilities],
            "recommended_capabilities": [str(c) for c in self.recommended_capabilities],
            "tags": self.tags,
            "example_bundles": [str(b) for b in self.example_bundles]
        }

    def validate(self, known_capabilities: List[CanonicalId],
                 known_bundles: List[CanonicalId]) -> ValidationResult:
        """Validate this ProjectType against known catalog entities."""
        from core.domain.contracts.errors import UnknownReferenceError
        result = ValidationResult.success()

        # Check default capabilities exist
        known_cap_set = set(known_capabilities)
        for cap in self.default_capabilities:
            if cap not in known_cap_set:
                result = result.add_error(UnknownReferenceError(
                    reference=str(cap),
                    reference_type="capability",
                    available=[str(c) for c in known_capabilities]
                ))

        # Check recommended capabilities exist
        for cap in self.recommended_capabilities:
            if cap not in known_cap_set:
                result = result.add_error(UnknownReferenceError(
                    reference=str(cap),
                    reference_type="capability",
                    available=[str(c) for c in known_capabilities]
                ))

        # Check example bundles exist
        known_bundle_set = set(known_bundles)
        for bundle in self.example_bundles:
            if bundle not in known_bundle_set:
                result = result.add_error(UnknownReferenceError(
                    reference=str(bundle),
                    reference_type="stack_bundle",
                    available=[str(b) for b in known_bundles]
                ))

        return result

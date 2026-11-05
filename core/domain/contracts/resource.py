"""
Domain model for Resource entity.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from core.domain.contracts.id_policy import CanonicalId, make_id
from core.domain.contracts.errors import ValidationResult, UnknownReferenceError


@dataclass(frozen=True)
class RuntimeAdapterMetadata:
    """Metadata for how a resource maps to a specific runtime."""
    format: str
    path_template: str
    transform_hints: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> 'RuntimeAdapterMetadata':
        return cls(
            format=data["format"],
            path_template=data["path_template"],
            transform_hints=data.get("transform_hints", {})
        )

    def to_dict(self) -> dict:
        result = {
            "format": self.format,
            "path_template": self.path_template
        }
        if self.transform_hints:
            result["transform_hints"] = self.transform_hints
        return result


@dataclass(frozen=True)
class ResourceProvenance:
    """Source provenance metadata for traceability."""
    source: str  # bundled, agency-agents, custom, community
    upstream_repo: Optional[str] = None
    upstream_commit: Optional[str] = None
    license: Optional[str] = None
    imported_date: Optional[str] = None  # ISO date
    reviewed_date: Optional[str] = None  # ISO date
    transformation: Optional[str] = None

    VALID_SOURCES = frozenset(["bundled", "agency-agents", "custom", "community"])

    def __post_init__(self):
        if self.source not in self.VALID_SOURCES:
            raise ValueError(f"Invalid source: {self.source}. Valid: {self.VALID_SOURCES}")
        if self.upstream_commit and len(self.upstream_commit) != 40:
            raise ValueError("upstream_commit must be 40-character SHA")

    @classmethod
    def from_dict(cls, data: dict) -> 'ResourceProvenance':
        return cls(
            source=data["source"],
            upstream_repo=data.get("upstream_repo"),
            upstream_commit=data.get("upstream_commit"),
            license=data.get("license"),
            imported_date=data.get("imported_date"),
            reviewed_date=data.get("reviewed_date"),
            transformation=data.get("transformation")
        )

    def to_dict(self) -> dict:
        result = {"source": self.source}
        for field in ["upstream_repo", "upstream_commit", "license",
                      "imported_date", "reviewed_date", "transformation"]:
            value = getattr(self, field)
            if value:
                result[field] = value
        return result


@dataclass(frozen=True)
class Resource:
    """
    Canonical Resource entity.

    Portable resource identity — canonical resource identity != runtime-specific representation.
    """
    id: CanonicalId
    name: str
    type: str
    description: str
    schema_version: str = "1.0.0"
    capabilities: List[CanonicalId] = field(default_factory=list)
    project_types: List[CanonicalId] = field(default_factory=list)
    stack_bundles: List[CanonicalId] = field(default_factory=list)
    runtime_adapters: Dict[str, RuntimeAdapterMetadata] = field(default_factory=dict)
    provenance: ResourceProvenance = field(default_factory=ResourceProvenance)
    version: str = "1.0.0"
    dependencies: List[CanonicalId] = field(default_factory=list)

    VALID_TYPES = frozenset([
        "agent", "skill", "rule", "workflow", "script",
        "template", "instruction", "shared-module"
    ])

    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("Resource name cannot be empty")
        if self.type not in self.VALID_TYPES:
            raise ValueError(f"Invalid resource type: {self.type}. Valid: {self.VALID_TYPES}")
        if self.schema_version != "1.0.0":
            raise ValueError(f"Unsupported schema_version: {self.schema_version}")

        # Validate all ID lists
        for lst, field_name in [
            (self.capabilities, "capabilities"),
            (self.project_types, "project_types"),
            (self.stack_bundles, "stack_bundles"),
            (self.dependencies, "dependencies")
        ]:
            for item in lst:
                if not isinstance(item, CanonicalId):
                    raise TypeError(f"{field_name} must be CanonicalId, got {type(item)}")

        # Validate runtime_adapters
        for runtime_id, metadata in self.runtime_adapters.items():
            if not isinstance(metadata, RuntimeAdapterMetadata):
                raise TypeError(f"runtime_adapters['{runtime_id}'] must be RuntimeAdapterMetadata")

        if not isinstance(self.provenance, ResourceProvenance):
            raise TypeError("provenance must be ResourceProvenance")

    @classmethod
    def from_dict(cls, data: dict) -> 'Resource':
        return cls(
            id=make_id(data["id"]),
            name=data["name"],
            type=data["type"],
            description=data["description"],
            schema_version=data.get("schema_version", "1.0.0"),
            capabilities=[make_id(c) for c in data.get("capabilities", [])],
            project_types=[make_id(p) for p in data.get("project_types", [])],
            stack_bundles=[make_id(b) for b in data.get("stack_bundles", [])],
            runtime_adapters={
                k: RuntimeAdapterMetadata.from_dict(v)
                for k, v in data.get("runtime_adapters", {}).items()
            },
            provenance=ResourceProvenance.from_dict(data.get("provenance", {"source": "bundled"})),
            version=data.get("version", "1.0.0"),
            dependencies=[make_id(d) for d in data.get("dependencies", [])]
        )

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "id": str(self.id),
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "capabilities": [str(c) for c in self.capabilities],
            "project_types": [str(p) for p in self.project_types],
            "stack_bundles": [str(b) for b in self.stack_bundles],
            "runtime_adapters": {k: v.to_dict() for k, v in self.runtime_adapters.items()},
            "provenance": self.provenance.to_dict(),
            "version": self.version,
            "dependencies": [str(d) for d in self.dependencies]
        }

    def validate(self, known_capabilities: List[CanonicalId],
                 known_project_types: List[CanonicalId],
                 known_bundles: List[CanonicalId],
                 known_resources: List[CanonicalId]) -> ValidationResult:
        """Validate this Resource against known catalog entities."""
        result = ValidationResult.success()

        known_cap = set(known_capabilities)
        known_pts = set(known_project_types)
        known_bundles = set(known_bundles)
        known_res = set(known_resources)

        for cap in self.capabilities:
            if cap not in known_cap:
                result = result.add_error(UnknownReferenceError(
                    reference=str(cap), reference_type="capability",
                    available=[str(c) for c in known_capabilities]
                ))

        for pt in self.project_types:
            if pt not in known_pts:
                result = result.add_error(UnknownReferenceError(
                    reference=str(pt), reference_type="project_type",
                    available=[str(p) for p in known_project_types]
                ))

        for bundle in self.stack_bundles:
            if bundle not in known_bundles:
                result = result.add_error(UnknownReferenceError(
                    reference=str(bundle), reference_type="stack_bundle",
                    available=[str(b) for b in known_bundles]
                ))

        for dep in self.dependencies:
            if dep not in known_res:
                result = result.add_error(UnknownReferenceError(
                    reference=str(dep), reference_type="resource",
                    available=[str(r) for r in known_resources]
                ))

        return result

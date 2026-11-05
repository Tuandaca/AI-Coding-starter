"""
Domain model for CapabilityProvider entity.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from core.domain.contracts.id_policy import CanonicalId, make_id
from core.domain.contracts.errors import ValidationResult, UnknownReferenceError


@dataclass(frozen=True)
class HealthCheckConfig:
    """Health check configuration for a capability provider."""
    command: str = ""
    timeout_seconds: int = 30
    expected_output: str = ""

    def __post_init__(self):
        if self.timeout_seconds < 1 or self.timeout_seconds > 300:
            raise ValueError("timeout_seconds must be between 1 and 300")

    @classmethod
    def from_dict(cls, data: dict) -> 'HealthCheckConfig':
        return cls(
            command=data.get("command", ""),
            timeout_seconds=data.get("timeout_seconds", 30),
            expected_output=data.get("expected_output", "")
        )

    def to_dict(self) -> dict:
        result = {}
        if self.command:
            result["command"] = self.command
        if self.timeout_seconds != 30:
            result["timeout_seconds"] = self.timeout_seconds
        if self.expected_output:
            result["expected_output"] = self.expected_output
        return result


@dataclass(frozen=True)
class CapabilityProvider:
    """
    Canonical CapabilityProvider entity.

    Optional provider for a capability — preferred provider with fallback chain.
    """
    id: CanonicalId
    capability: CanonicalId
    priority: int
    schema_version: str = "1.0.0"
    name: str = ""
    description: str = ""
    availability: str = "external-install"
    health_check: HealthCheckConfig = field(default_factory=HealthCheckConfig)
    requirements: List[str] = field(default_factory=list)
    fallback: Optional[CanonicalId] = None
    optional: bool = True
    configuration: Dict[str, Any] = field(default_factory=dict)

    VALID_AVAILABILITY = frozenset([
        "bundled", "external-install", "external-service", "runtime-native"
    ])

    def __post_init__(self):
        if self.schema_version != "1.0.0":
            raise ValueError(f"Unsupported schema_version: {self.schema_version}")
        if not isinstance(self.capability, CanonicalId):
            raise TypeError("capability must be CanonicalId")
        if self.priority < 1 or self.priority > 100:
            raise ValueError("priority must be between 1 and 100")
        if self.availability not in self.VALID_AVAILABILITY:
            raise ValueError(f"Invalid availability: {self.availability}. Valid: {self.VALID_AVAILABILITY}")
        if not isinstance(self.health_check, HealthCheckConfig):
            raise TypeError("health_check must be HealthCheckConfig")
        if self.fallback is not None and not isinstance(self.fallback, CanonicalId):
            raise TypeError("fallback must be CanonicalId or None")

        for req in self.requirements:
            if not isinstance(req, str):
                raise TypeError("requirements must be strings")

    @classmethod
    def from_dict(cls, data: dict) -> 'CapabilityProvider':
        fallback = data.get("fallback")
        return cls(
            id=make_id(data["id"]),
            capability=make_id(data["capability"]),
            priority=data["priority"],
            schema_version=data.get("schema_version", "1.0.0"),
            name=data.get("name", ""),
            description=data.get("description", ""),
            availability=data.get("availability", "external-install"),
            health_check=HealthCheckConfig.from_dict(data.get("health_check", {})),
            requirements=data.get("requirements", []),
            fallback=make_id(fallback) if fallback else None,
            optional=data.get("optional", True),
            configuration=data.get("configuration", {})
        )

    def to_dict(self) -> dict:
        result = {
            "schema_version": self.schema_version,
            "id": str(self.id),
            "capability": str(self.capability),
            "priority": self.priority,
            "availability": self.availability,
            "health_check": self.health_check.to_dict(),
            "requirements": self.requirements,
            "optional": self.optional,
            "configuration": self.configuration
        }
        if self.name:
            result["name"] = self.name
        if self.description:
            result["description"] = self.description
        if self.fallback:
            result["fallback"] = str(self.fallback)
        return result

    def validate(self, known_capabilities: List[CanonicalId],
                 known_providers: List[CanonicalId]) -> ValidationResult:
        """Validate this CapabilityProvider against known catalog entities."""
        result = ValidationResult.success()

        known_cap = set(known_capabilities)
        known_prov = set(known_providers)

        # Check capability exists
        if self.capability not in known_cap:
            result = result.add_error(UnknownReferenceError(
                reference=str(self.capability), reference_type="capability",
                available=[str(c) for c in known_capabilities]
            ))

        # Check fallback provider exists
        if self.fallback and self.fallback not in known_prov:
            result = result.add_error(UnknownReferenceError(
                reference=str(self.fallback), reference_type="capability_provider",
                available=[str(p) for p in known_providers]
            ))

        return result

"""
Domain model for Technology entity.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from core.domain.contracts.id_policy import validate_id, CanonicalId, make_id
from core.domain.contracts.errors import ValidationResult


@dataclass(frozen=True)
class VersionPolicy:
    """Version selection policy for a technology."""
    strategy: str  # latest-stable, lts, pinned-major, pinned-exact, rolling
    default_version: Optional[str] = None
    supported_versions: List[str] = field(default_factory=list)
    min_version: Optional[str] = None

    VALID_STRATEGIES = frozenset(["latest-stable", "lts", "pinned-major", "pinned-exact", "rolling"])

    def __post_init__(self):
        if self.strategy not in self.VALID_STRATEGIES:
            raise ValueError(f"Invalid version strategy: {self.strategy}. Valid: {self.VALID_STRATEGIES}")

        # Validate version format if present
        version_pattern = r'^\d+(\.\d+)*(-[a-zA-Z0-9.-]+)?$'
        import re
        if self.default_version and not re.match(version_pattern, self.default_version):
            raise ValueError(f"Invalid default_version format: {self.default_version}")
        for v in self.supported_versions:
            if not re.match(version_pattern, v):
                raise ValueError(f"Invalid supported_version format: {v}")
        if self.min_version and not re.match(version_pattern, self.min_version):
            raise ValueError(f"Invalid min_version format: {self.min_version}")

    @classmethod
    def from_dict(cls, data: dict) -> 'VersionPolicy':
        return cls(
            strategy=data["strategy"],
            default_version=data.get("default_version"),
            supported_versions=data.get("supported_versions", []),
            min_version=data.get("min_version")
        )

    def to_dict(self) -> dict:
        result = {"strategy": self.strategy}
        if self.default_version:
            result["default_version"] = self.default_version
        if self.supported_versions:
            result["supported_versions"] = self.supported_versions
        if self.min_version:
            result["min_version"] = self.min_version
        return result


@dataclass(frozen=True)
class Technology:
    """
    Canonical Technology entity.

    Stable technology identity — version labels tracked separately in version_policy.
    """
    id: CanonicalId
    name: str
    category: str
    ecosystem: str
    version_policy: VersionPolicy
    schema_version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    documentation_url: Optional[str] = None

    VALID_CATEGORIES = frozenset([
        "frontend", "backend", "database", "orm", "cache", "queue",
        "search", "auth", "payments", "ai", "vector-database",
        "hosting", "styling", "testing", "language", "framework", "tooling"
    ])

    VALID_ECOSYSTEMS = frozenset([
        "javascript", "typescript", "python", "dotnet", "go", "rust",
        "java", "php", "ruby", "elixir", "cloud", "platform-agnostic"
    ])

    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("Technology name cannot be empty")
        if self.schema_version != "1.0.0":
            raise ValueError(f"Unsupported schema_version: {self.schema_version}")
        if self.category not in self.VALID_CATEGORIES:
            raise ValueError(f"Invalid category '{self.category}'. Valid: {self.VALID_CATEGORIES}")
        if self.ecosystem not in self.VALID_ECOSYSTEMS:
            raise ValueError(f"Invalid ecosystem '{self.ecosystem}'. Valid: {self.VALID_ECOSYSTEMS}")
        if not isinstance(self.version_policy, VersionPolicy):
            raise TypeError("version_policy must be VersionPolicy")

        for tag in self.tags:
            if not isinstance(tag, str) or not tag:
                raise ValueError("Tags must be non-empty strings")

        if self.documentation_url and not self.documentation_url.startswith(("http://", "https://")):
            raise ValueError("documentation_url must be a valid HTTP/HTTPS URL")

    @classmethod
    def from_dict(cls, data: dict) -> 'Technology':
        return cls(
            id=make_id(data["id"]),
            name=data["name"],
            category=data["category"],
            ecosystem=data["ecosystem"],
            version_policy=VersionPolicy.from_dict(data["version_policy"]),
            schema_version=data.get("schema_version", "1.0.0"),
            tags=data.get("tags", []),
            documentation_url=data.get("documentation_url")
        )

    def to_dict(self) -> dict:
        result = {
            "schema_version": self.schema_version,
            "id": str(self.id),
            "name": self.name,
            "category": self.category,
            "ecosystem": self.ecosystem,
            "version_policy": self.version_policy.to_dict()
        }
        if self.tags:
            result["tags"] = self.tags
        if self.documentation_url:
            result["documentation_url"] = self.documentation_url
        return result

    def validate(self) -> ValidationResult:
        """Basic self-validation (no cross-references needed for Technology)."""
        return ValidationResult.success()

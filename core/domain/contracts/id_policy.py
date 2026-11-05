"""
Canonical ID policy and validation utilities for AI-Coding-starter V2.

ID Rules (from M1 specification):
- lowercase kebab-case
- stable
- human-readable
- vendor-neutral where possible
- No version numbers embedded in stable identity
"""

import re
from typing import Optional
from dataclasses import dataclass


# Canonical ID pattern: lowercase kebab-case, starts and ends with alphanumeric
# Must not contain version-like patterns (e.g., nextjs-14, postgres-16)
ID_PATTERN = re.compile(r'^[a-z][a-z0-9-]*[a-z0-9]$')
# Matches version patterns: 14, 16, 3.11, 20, 8, 1.0.0, v1.0.0, version-2
VERSION_PATTERN = re.compile(r'(?:^|-)(\d+\.\d+(\.\d+)?|\d{1,2})(?:-|$)|(?:^|-)v\d+\.\d+\.\d+(?:-|$)')
ID_MIN_LENGTH = 2
ID_MAX_LENGTH = 64


class InvalidIdError(ValueError):
    """Raised when an ID violates canonical ID policy."""
    pass


def validate_id(id_value: str, field_name: str = "id") -> None:
    """
    Validate that a string conforms to canonical ID policy.

    Args:
        id_value: The ID string to validate
        field_name: Name of the field (for error messages)

    Raises:
        InvalidIdError: If the ID is invalid
    """
    if not isinstance(id_value, str):
        raise InvalidIdError(f"{field_name} must be a string, got {type(id_value).__name__}")

    if not id_value:
        raise InvalidIdError(f"{field_name} cannot be empty")

    if len(id_value) < ID_MIN_LENGTH:
        raise InvalidIdError(f"{field_name} must be at least {ID_MIN_LENGTH} characters")

    if len(id_value) > ID_MAX_LENGTH:
        raise InvalidIdError(f"{field_name} must be at most {ID_MAX_LENGTH} characters")

    if not ID_PATTERN.match(id_value):
        raise InvalidIdError(
            f"{field_name} '{id_value}' must be lowercase kebab-case "
            f"(e.g., 'nextjs', 'authentication', 'my-project')"
        )

    # Check for version-like patterns that should not be in stable IDs
    # Matches patterns like: nextjs-14, postgres-16, node-20, python-3.11, v1.0.0, version-2
    if VERSION_PATTERN.search(id_value):
        raise InvalidIdError(
            f"{field_name} '{id_value}' appears to contain a version number. "
            f"Stable IDs must not embed versions (use 'nextjs' not 'nextjs-14')"
        )


def is_valid_id(id_value: str) -> bool:
    """Check if a string is a valid canonical ID without raising."""
    try:
        validate_id(id_value)
        return True
    except InvalidIdError:
        return False


def normalize_id_candidate(candidate: str) -> str:
    """
    Normalize a human-readable string to canonical ID format.

    This is a helper for generating IDs from names, not a validation function.
    The result must still be validated with validate_id().

    Args:
        candidate: Human-readable string (e.g., "Next.js 14", "API Documentation")

    Returns:
        Normalized kebab-case string
    """
    # Lowercase
    normalized = candidate.lower()

    # Replace common version patterns
    normalized = re.sub(r'\bv?\d+(\.\d+)*\b', '', normalized)

    # Replace . and other special chars with hyphens
    normalized = re.sub(r'[.]+', '-', normalized)

    # Replace non-alphanumeric with hyphens
    normalized = re.sub(r'[^a-z0-9]+', '-', normalized)

    # Collapse multiple hyphens
    normalized = re.sub(r'-+', '-', normalized)

    # Trim hyphens from ends
    normalized = normalized.strip('-')

    # Ensure starts with letter
    if normalized and not normalized[0].isalpha():
        normalized = 'x-' + normalized

    return normalized


@dataclass(frozen=True)
class CanonicalId:
    """
    Wrapper for a validated canonical ID.

    Use this in domain models to guarantee ID validity at construction time.
    """
    value: str

    def __post_init__(self):
        validate_id(self.value, "CanonicalId")

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other) -> bool:
        if isinstance(other, CanonicalId):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other
        return False

    def __hash__(self) -> int:
        return hash(self.value)


def make_id(value: str) -> CanonicalId:
    """Factory function to create a validated CanonicalId."""
    return CanonicalId(value)


# Predefined valid ID patterns for common categories
PROJECT_TYPE_IDS = frozenset([
    "portfolio", "landing-page", "business-website", "blog",
    "ecommerce", "saas", "fullstack-app", "dashboard",
    "backend-api", "mobile-app", "ai-rag", "ai-agent",
    "realtime-app", "desktop-app", "other", "undecided"
])

CAPABILITY_IDS = frozenset([
    "authentication", "authorization", "payments", "subscriptions",
    "email", "file-upload", "search", "realtime", "notifications",
    "multi-tenancy", "cache", "background-jobs", "queue",
    "analytics", "i18n", "accessibility", "ai", "rag", "vector-search"
])

TECHNOLOGY_CATEGORIES = frozenset([
    "frontend", "backend", "database", "orm", "cache", "queue",
    "search", "auth", "payments", "ai", "vector-database",
    "hosting", "styling", "testing", "language", "framework", "tooling"
])

STACK_BUNDLE_PROFILES = frozenset([
    "fastest-mvp", "balanced", "scalable", "minimal", "custom"
])

RUNTIME_ADAPTER_IDS = frozenset([
    "codex", "opencode", "antigravity", "claude-code", "cursor", "gemini"
])

RESOURCE_TYPES = frozenset([
    "agent", "skill", "rule", "workflow", "script",
    "template", "instruction", "shared-module"
])

EXECUTION_PACK_MODES = frozenset([
    "continuous", "time-boxed", "event-driven", "on-demand"
])

CAPABILITY_PROVIDER_AVAILABILITY = frozenset([
    "bundled", "external-install", "external-service", "runtime-native"
])

COMPATIBILITY_SEVERITIES = frozenset(["error", "warning", "info"])

COMPATIBILITY_RULE_TYPES = frozenset([
    "technology-technology", "technology-capability", "capability-capability",
    "bundle-bundle", "bundle-capability", "bundle-technology", "technology-project-type"
])

"""
Core domain contracts package for AI-Coding-starter V2.

This package contains the canonical domain entities and validation logic
for the portable project specification system.
"""

from core.domain.contracts.id_policy import (
    validate_id,
    is_valid_id,
    normalize_id_candidate,
    CanonicalId,
    make_id,
    InvalidIdError,
    PROJECT_TYPE_IDS,
    CAPABILITY_IDS,
    TECHNOLOGY_CATEGORIES,
    STACK_BUNDLE_PROFILES,
    RUNTIME_ADAPTER_IDS,
    RESOURCE_TYPES,
    EXECUTION_PACK_MODES,
    CAPABILITY_PROVIDER_AVAILABILITY,
    COMPATIBILITY_SEVERITIES,
    COMPATIBILITY_RULE_TYPES,
)

from core.domain.contracts.errors import (
    DomainError,
    SchemaValidationError,
    UnknownReferenceError,
    DuplicateIdError,
    CompatibilityDefinitionError,
    UnsupportedSchemaVersionError,
    ValidationResult,
    validate_required_fields,
    validate_enum_field,
    validate_unique_items,
    validate_references,
)

from core.domain.contracts.project_type import ProjectType
from core.domain.contracts.capability import Capability
from core.domain.contracts.technology import Technology, VersionPolicy
from core.domain.contracts.stack_bundle import StackBundle
from core.domain.contracts.compatibility import Compatibility, CompatibilityRule, CompatibilityCondition
from core.domain.contracts.resource import Resource, RuntimeAdapterMetadata, ResourceProvenance
from core.domain.contracts.execution_pack import ExecutionPack, OptionalRole, ActivationConditions
from core.domain.contracts.runtime_adapter import RuntimeAdapter, DetectionConfig, PermissionPolicy
from core.domain.contracts.capability_provider import CapabilityProvider, HealthCheckConfig
from core.domain.contracts.project_state import ProjectSpec, RuntimePreferences

__all__ = [
    # ID Policy
    "validate_id",
    "is_valid_id",
    "normalize_id_candidate",
    "CanonicalId",
    "make_id",
    "InvalidIdError",
    "PROJECT_TYPE_IDS",
    "CAPABILITY_IDS",
    "TECHNOLOGY_CATEGORIES",
    "STACK_BUNDLE_PROFILES",
    "RUNTIME_ADAPTER_IDS",
    "RESOURCE_TYPES",
    "EXECUTION_PACK_MODES",
    "CAPABILITY_PROVIDER_AVAILABILITY",
    "COMPATIBILITY_SEVERITIES",
    "COMPATIBILITY_RULE_TYPES",

    # Errors
    "DomainError",
    "SchemaValidationError",
    "UnknownReferenceError",
    "DuplicateIdError",
    "CompatibilityDefinitionError",
    "UnsupportedSchemaVersionError",
    "ValidationResult",
    "validate_required_fields",
    "validate_enum_field",
    "validate_unique_items",
    "validate_references",

    # Domain Entities
    "ProjectType",
    "Capability",
    "Technology",
    "VersionPolicy",
    "StackBundle",
    "Compatibility",
    "CompatibilityRule",
    "CompatibilityCondition",
    "Resource",
    "RuntimeAdapterMetadata",
    "ResourceProvenance",
    "ExecutionPack",
    "OptionalRole",
    "ActivationConditions",
    "RuntimeAdapter",
    "DetectionConfig",
    "PermissionPolicy",
    "CapabilityProvider",
    "HealthCheckConfig",
    "ProjectSpec",
    "RuntimePreferences",
]

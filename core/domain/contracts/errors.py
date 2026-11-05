"""
Domain validation errors for AI-Coding-starter V2.

Minimal error hierarchy following M1 specification:
- SchemaValidationError
- UnknownReferenceError
- DuplicateIdError
- CompatibilityDefinitionError
- UnsupportedSchemaVersionError
"""

from typing import Optional, List, Any
from dataclasses import dataclass


class DomainError(Exception):
    """Base class for all domain validation errors."""

    def __init__(self, message: str, code: str, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class SchemaValidationError(DomainError):
    """Raised when a contract/schema validation fails."""

    def __init__(self, message: str, field_path: str = "", schema_id: str = "",
                 details: Optional[dict] = None):
        super().__init__(message, "SCHEMA_VALIDATION_ERROR", details)
        self.field_path = field_path
        self.schema_id = schema_id


class UnknownReferenceError(DomainError):
    """Raised when a reference to an entity cannot be resolved."""

    def __init__(self, reference: str, reference_type: str,
                 available: Optional[List[str]] = None, details: Optional[dict] = None):
        message = f"Unknown {reference_type}: '{reference}'"
        if available:
            message += f". Available: {', '.join(sorted(available))}"
        super().__init__(message, "UNKNOWN_REFERENCE_ERROR", details)
        self.reference = reference
        self.reference_type = reference_type
        self.available = available or []


class DuplicateIdError(DomainError):
    """Raised when duplicate IDs are detected in a collection."""

    def __init__(self, duplicate_id: str, entity_type: str,
                 locations: Optional[List[str]] = None, details: Optional[dict] = None):
        message = f"Duplicate {entity_type} ID: '{duplicate_id}'"
        if locations:
            message += f" at {', '.join(locations)}"
        super().__init__(message, "DUPLICATE_ID_ERROR", details)
        self.duplicate_id = duplicate_id
        self.entity_type = entity_type
        self.locations = locations or []


class CompatibilityDefinitionError(DomainError):
    """Raised when compatibility rules are invalid or contradictory."""

    def __init__(self, message: str, rule_type: str = "",
                 subject: str = "", target: str = "", details: Optional[dict] = None):
        super().__init__(message, "COMPATIBILITY_DEFINITION_ERROR", details)
        self.rule_type = rule_type
        self.subject = subject
        self.target = target


class UnsupportedSchemaVersionError(DomainError):
    """Raised when an unknown or unsupported schema version is encountered."""

    def __init__(self, schema_id: str, found_version: str,
                 supported_versions: List[str], details: Optional[dict] = None):
        message = (f"Unsupported schema version '{found_version}' for {schema_id}. "
                   f"Supported: {', '.join(supported_versions)}")
        super().__init__(message, "UNSUPPORTED_SCHEMA_VERSION_ERROR", details)
        self.schema_id = schema_id
        self.found_version = found_version
        self.supported_versions = supported_versions


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    errors: List[DomainError]
    warnings: List[str]

    @classmethod
    def success(cls, warnings: Optional[List[str]] = None) -> 'ValidationResult':
        return cls(is_valid=True, errors=[], warnings=warnings or [])

    @classmethod
    def failure(cls, errors: List[DomainError], warnings: Optional[List[str]] = None) -> 'ValidationResult':
        return cls(is_valid=False, errors=errors, warnings=warnings or [])

    def add_error(self, error: DomainError) -> 'ValidationResult':
        return ValidationResult(
            is_valid=False,
            errors=self.errors + [error],
            warnings=self.warnings
        )

    def add_warning(self, warning: str) -> 'ValidationResult':
        return ValidationResult(
            is_valid=self.is_valid,
            errors=self.errors,
            warnings=self.warnings + [warning]
        )

    def merge(self, other: 'ValidationResult') -> 'ValidationResult':
        return ValidationResult(
            is_valid=self.is_valid and other.is_valid,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings
        )


def validate_required_fields(data: dict, required_fields: List[str],
                             schema_id: str = "") -> ValidationResult:
    """Validate that all required fields are present in a dictionary."""
    result = ValidationResult.success()
    for field in required_fields:
        if field not in data:
            result = result.add_error(SchemaValidationError(
                f"Missing required field: '{field}'",
                field_path=field,
                schema_id=schema_id
            ))
    return result


def validate_enum_field(data: dict, field: str, valid_values: List[str],
                        schema_id: str = "") -> ValidationResult:
    """Validate that a field's value is in the allowed enum values."""
    result = ValidationResult.success()
    if field in data and data[field] not in valid_values:
        result = result.add_error(SchemaValidationError(
            f"Field '{field}' has invalid value '{data[field]}'. "
            f"Valid values: {', '.join(valid_values)}",
            field_path=field,
            schema_id=schema_id
        ))
    return result


def validate_unique_items(items: List[Any], key_func=lambda x: x,
                          entity_type: str = "item") -> ValidationResult:
    """Validate that all items in a list have unique keys."""
    result = ValidationResult.success()
    seen = {}
    for i, item in enumerate(items):
        key = key_func(item)
        if key in seen:
            result = result.add_error(DuplicateIdError(
                duplicate_id=str(key),
                entity_type=entity_type,
                locations=[str(seen[key]), str(i)]
            ))
        else:
            seen[key] = i
    return result


def validate_references(references: List[str], valid_references: List[str],
                        reference_type: str) -> ValidationResult:
    """Validate that all references point to known entities."""
    result = ValidationResult.success()
    valid_set = set(valid_references)
    for ref in references:
        if ref not in valid_set:
            result = result.add_error(UnknownReferenceError(
                reference=ref,
                reference_type=reference_type,
                available=valid_references
            ))
    return result

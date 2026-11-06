"""
Deterministic catalog loader for AI-Coding-starter V2 M3.

Loads the machine-readable catalog files and produces canonical
domain-compatible data.

Format policy: catalog files use the ``.yaml`` extension and intentionally
contain JSON-compatible YAML 1.2 syntax (YAML is a JSON superset), so the
starter remains stdlib-only and parses them deterministically with ``json``.
Do not add PyYAML or a custom YAML parser.

Responsibilities:
  * Load the four M3 catalog files.
  * Convert raw data into M1 domain entities (ProjectType, Capability,
    StackBundle, Compatibility).
  * Validate structural basics: duplicate IDs, schema versions, valid ID
    format, valid cross-references.
  * Fail clearly (CatalogValidationError) on any malformed catalog.

This module performs file I/O in one boundary so the wizard and resolver do
not scatter catalog reads throughout the codebase.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from core.domain.contracts import (
    ProjectType,
    Capability,
    StackBundle,
    Compatibility,
    make_id,
    CanonicalId,
    InvalidIdError,
    DuplicateIdError,
    UnknownReferenceError,
    SchemaValidationError,
    ValidationResult,
    DomainError,
)

# Canonical location of the M3 catalog directory relative to this module.
DEFAULT_CATALOG_DIR = Path(__file__).resolve().parent.parent / "catalog"

CATALOG_FILES = {
    "project_types": "project-types.yaml",
    "capabilities": "capabilities.yaml",
    "stack_bundles": "stack-bundles.yaml",
    "compatibility": "compatibility.yaml",
}

REQUIRED_TOP_LEVEL = {
    "project_types": "project_types",
    "capabilities": "capabilities",
    "stack_bundles": "stack_bundles",
    "compatibility": "rules",
}


class CatalogValidationError(DomainError):
    """Raised when a catalog file is malformed or fails validation."""

    def __init__(self, message: str, file: str = "", details=None):
        super().__init__(message, "CATALOG_VALIDATION_ERROR", details or {})
        self.file = file


@dataclass(frozen=True)
class Catalog:
    """In-memory representation of the loaded M3 catalogs."""

    project_types: Dict[str, ProjectType] = field(default_factory=dict)
    capabilities: Dict[str, Capability] = field(default_factory=dict)
    stack_bundles: Dict[str, StackBundle] = field(default_factory=dict)
    compatibility: Compatibility = field(default_factory=Compatibility)

    # --- convenience lookups ---------------------------------------------

    def project_type(self, reference: str) -> Optional[ProjectType]:
        return self.project_types.get(reference)

    def capability(self, reference: str) -> Optional[Capability]:
        return self.capabilities.get(reference)

    def stack_bundle(self, reference: str) -> Optional[StackBundle]:
        return self.stack_bundles.get(reference)

    def technology_ids(self) -> Set[str]:
        """All stable technology IDs referenced by the loaded catalog.

        Includes technology role values from stack bundles plus the
        informational ``example_implementations`` listed by capabilities.
        """
        ids: Set[str] = set()
        for bundle in self.stack_bundles.values():
            for role, tech_id in bundle.technologies.items():
                ids.add(str(tech_id))
        for capability in self.capabilities.values():
            for tech_id in capability.example_implementations:
                ids.add(str(tech_id))
        return ids


def _load_json(path: Path, file_label: str) -> dict:
    """Load and parse a catalog file as JSON-compatible YAML.

    YAML 1.2 is a superset of JSON, so any valid JSON document is valid YAML.
    Parsing with stdlib ``json`` keeps the loader offline and deterministic
    without PyYAML or any third-party dependency.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        raise CatalogValidationError(
            f"Catalog file not found: {path}", file=file_label
        )
    except json.JSONDecodeError as exc:
        raise CatalogValidationError(
            f"Malformed JSON/YAML in {file_label}: {exc}",
            file=file_label,
        )
    if not isinstance(data, dict):
        raise CatalogValidationError(
            f"Top-level catalog content in {file_label} must be a mapping, "
            f"got {type(data).__name__}",
            file=file_label,
        )
    return data


def _check_schema_version(data: dict, file_label: str) -> List[str]:
    errors: List[str] = []
    version = data.get("schema_version")
    if version != "1.0.0":
        errors.append(
            f"{file_label}: unsupported or missing schema_version "
            f"({version!r}; expected '1.0.0')"
        )
    return errors


def _check_duplicate_ids(items: List[dict], entity_type: str, file_label: str) -> List[str]:
    errors: List[str] = []
    seen: Dict[str, int] = {}
    for index, item in enumerate(items):
        item_id = item.get("id")
        if not isinstance(item_id, str):
            errors.append(
                f"{file_label}: {entity_type} at index {index} has no string id"
            )
            continue
        if item_id in seen:
            errors.append(
                f"{file_label}: duplicate {entity_type} id '{item_id}' "
                f"(first at index {seen[item_id]}, again at index {index})"
            )
        else:
            seen[item_id] = index
    return errors


def load_catalog(catalog_dir=None) -> Catalog:
    """Load and validate all M3 catalog files.

    Args:
        catalog_dir: Directory containing the catalog files. Defaults to the
            ``catalog/`` directory at the repository root.

    Returns:
        A populated, validated :class:`Catalog`.

    Raises:
        CatalogValidationError: If any catalog file is missing, malformed,
            or fails structural/cross-reference validation.
    """
    if catalog_dir is None:
        catalog_dir = DEFAULT_CATALOG_DIR
    catalog_dir = Path(catalog_dir)

    errors: List[str] = []

    raw: Dict[str, dict] = {}
    for key, filename in CATALOG_FILES.items():
        path = catalog_dir / filename
        raw[key] = _load_json(path, filename)
        errors.extend(_check_schema_version(raw[key], filename))

    # --- Project types -------------------------------------------------------
    pt_raw = raw["project_types"].get("project_types", [])
    if not isinstance(pt_raw, list):
        errors.append("catalog/project-types.yaml: 'project_types' must be a list")
        pt_raw = []
    errors.extend(_check_duplicate_ids(pt_raw, "project type", "catalog/project-types.yaml"))

    project_types: Dict[str, ProjectType] = {}
    for item in pt_raw:
        try:
            pt = ProjectType.from_dict(item)
        except (InvalidIdError, KeyError, TypeError, ValueError) as exc:
            errors.append(
                f"catalog/project-types.yaml: invalid project type "
                f"{item.get('id', '<unknown>')!r}: {exc}"
            )
            continue
        project_types[str(pt.id)] = pt

    # --- Capabilities (need technology IDs for example_implementations) -----
    # Technology IDs are collected from stack bundles, so load bundles first
    # for cross-validation, but parse capabilities now so we can report parse
    # errors even if bundles fail.
    cap_raw = raw["capabilities"].get("capabilities", [])
    if not isinstance(cap_raw, list):
        errors.append("catalog/capabilities.yaml: 'capabilities' must be a list")
        cap_raw = []
    errors.extend(_check_duplicate_ids(cap_raw, "capability", "catalog/capabilities.yaml"))

    capabilities: Dict[str, Capability] = {}
    for item in cap_raw:
        try:
            cap = Capability.from_dict(item)
        except (InvalidIdError, KeyError, TypeError, ValueError) as exc:
            errors.append(
                f"catalog/capabilities.yaml: invalid capability "
                f"{item.get('id', '<unknown>')!r}: {exc}"
            )
            continue
        capabilities[str(cap.id)] = cap

    # --- Stack bundles -------------------------------------------------------
    sb_raw = raw["stack_bundles"].get("stack_bundles", [])
    if not isinstance(sb_raw, list):
        errors.append("catalog/stack-bundles.yaml: 'stack_bundles' must be a list")
        sb_raw = []
    errors.extend(_check_duplicate_ids(sb_raw, "stack bundle", "catalog/stack-bundles.yaml"))

    stack_bundles: Dict[str, StackBundle] = {}
    for item in sb_raw:
        try:
            bundle = StackBundle.from_dict(item)
        except (InvalidIdError, KeyError, TypeError, ValueError) as exc:
            errors.append(
                f"catalog/stack-bundles.yaml: invalid stack bundle "
                f"{item.get('id', '<unknown>')!r}: {exc}"
            )
            continue
        stack_bundles[str(bundle.id)] = bundle

    # --- Compatibility -------------------------------------------------------
    comp_raw = raw["compatibility"].get("rules", [])
    if not isinstance(comp_raw, list):
        errors.append("catalog/compatibility.yaml: 'rules' must be a list")
        comp_raw = []
    try:
        compatibility = Compatibility.from_dict({"schema_version": "1.0.0", "rules": comp_raw})
    except (InvalidIdError, KeyError, TypeError, ValueError) as exc:
        errors.append(f"catalog/compatibility.yaml: invalid compatibility rules: {exc}")
        compatibility = Compatibility()

    # --- Collect known entity IDs for cross-reference validation -------------
    known_capability_ids = {str(c.id) for c in capabilities.values()}
    known_bundle_ids = {str(b.id) for b in stack_bundles.values()}
    known_project_type_ids = {str(p.id) for p in project_types.values()}
    # Technology IDs come from bundle technology role values, plus the
    # informational example implementations referenced by capabilities.
    known_technology_ids: Set[str] = set()
    for bundle in stack_bundles.values():
        for tech_id in bundle.technologies.values():
            known_technology_ids.add(str(tech_id))
    for cap in capabilities.values():
        for tech_id in cap.example_implementations:
            known_technology_ids.add(str(tech_id))

    # --- Cross-reference validation using M1 contracts ----------------------
    for pt in project_types.values():
        result = pt.validate(
            known_capabilities=[make_id(c) for c in known_capability_ids],
            known_bundles=[make_id(b) for b in known_bundle_ids],
        )
        for err in result.errors:
            errors.append(
                f"catalog/project-types.yaml: project type '{pt.id}': {err.message}"
            )

    for cap in capabilities.values():
        result = cap.validate(
            known_technologies=[make_id(t) for t in known_technology_ids],
            known_capabilities=[make_id(c) for c in known_capability_ids],
            known_project_types=[make_id(p) for p in known_project_type_ids],
        )
        for err in result.errors:
            errors.append(
                f"catalog/capabilities.yaml: capability '{cap.id}': {err.message}"
            )

    for bundle in stack_bundles.values():
        result = bundle.validate(
            known_technologies=[make_id(t) for t in known_technology_ids],
            known_project_types=[make_id(p) for p in known_project_type_ids],
            known_capabilities=[make_id(c) for c in known_capability_ids],
            known_bundles=[make_id(b) for b in known_bundle_ids],
        )
        for err in result.errors:
            errors.append(
                f"catalog/stack-bundles.yaml: stack bundle '{bundle.id}': {err.message}"
            )

    result = compatibility.validate(
        known_technologies=[make_id(t) for t in known_technology_ids],
        known_capabilities=[make_id(c) for c in known_capability_ids],
        known_bundles=[make_id(b) for b in known_bundle_ids],
        known_project_types=[make_id(p) for p in known_project_type_ids],
    )
    for err in result.errors:
        errors.append(
            f"catalog/compatibility.yaml: rule '{err.reference}': {err.message}"
        )

    if errors:
        raise CatalogValidationError(
            "Catalog validation failed:\n" + "\n".join(sorted(errors)),
            file="catalog/",
        )

    return Catalog(
        project_types=project_types,
        capabilities=capabilities,
        stack_bundles=stack_bundles,
        compatibility=compatibility,
    )


__all__ = [
    "Catalog",
    "CatalogValidationError",
    "load_catalog",
    "DEFAULT_CATALOG_DIR",
]

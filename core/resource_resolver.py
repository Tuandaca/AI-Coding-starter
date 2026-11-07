"""
Resource resolver for AI-Coding-starter V2 Milestone M12.

Resolves project type + capabilities + stack bundle to a set of resource
selections (id, type, version, provenance, selection_reason).

These resources are then used by core/generic-renderer.py to render
runtime-specific instruction files, and by new_project.py to copy resources
into the generated project.

Architecture:
    project type ID + capabilities + stack bundle ID
            ↓
    Resource selection (this module)
            ↓
    copy_selective()  +  build_resources_lock()

Design principles:
  * Runtime-agnostic. No vendor branches.
  * Offline. No network, no LLM.
  * Stdlib-only.
  * Honest inference: never guesses resource IDs; validates against
    filesystem.
  * (type, id) collision-safe: same ID across different resource types
    is treated as distinct.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from core.domain.contracts.id_policy import make_id


@dataclass(frozen=True)
class ResourceSelection:
    """A single resource selection for M5/M7 rendering.

    Identity is (type, id) — never id alone — so same-named resources
    across different types (e.g. agent:security-auditor vs
    skill:security-auditor) are treated as distinct.
    """
    id: str
    type: str  # agent | skill | shared-module | workflow | script | template | rule
    version: str = "1.0.0"
    provenance_source: str = "bundled"
    provenance_commit_sha: str = "8b61d297dc07772a000b85fc93138c8aefd21c45"
    provenance_license: str = "MIT"
    selection_reason: str = ""


@dataclass(frozen=True)
class ResourceSelectionResult:
    """Result of resolving project type + capabilities + stack bundle to resources."""

    resources: list[ResourceSelection] = field(default_factory=list)
    project_type_id: str = ""
    selected_capability_ids: list[str] = field(default_factory=list)
    stack_bundle_id: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def resource_map(self) -> dict[tuple[str, str], ResourceSelection]:
        """Map keyed by (type, id) for collision-safe lookup."""
        return {(r.type, r.id): r for r in self.resources}


# Canonical location of the resource requirements catalog relative to this module.
DEFAULT_CATALOG_DIR = Path(__file__).resolve().parent.parent / "catalog"

# Mapping from resource type ID to directory name under resources/.
RESOURCE_TYPE_TO_DIR = {
    "agent": "agents",
    "skill": "skills",
    "shared-module": "shared",
    "workflow": "workflows",
    "script": "scripts",
    "template": "core",
    "rule": "rules",
}


def _load_resource_requirements(catalog_dir: Path) -> list[dict]:
    """Load catalog/resource-requirements.yaml as JSON-compatible text.

    Returns the list of ``resource_requirements`` entries, each mapping a
    project type id to the resources selected for that type (plus
    capability-driven selections).
    """
    path = catalog_dir / "resource-requirements.yaml"
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        return []
    requirements = data.get("resource_requirements", [])
    return requirements if isinstance(requirements, list) else []


def _resource_exists(resources_root: Path, rtype: str, rid: str) -> bool:
    """Check if a resource exists under resources/<type>/<rid>.<ext> or
    resources/<type>/<rid>/<anything>.

    Uses RESOURCE_TYPE_TO_DIR to map canonical resource type IDs to actual
    directory names (e.g. "shared-module" -> "shared").
    """
    type_dir_name = RESOURCE_TYPE_TO_DIR.get(rtype, rtype)
    type_dir = resources_root / type_dir_name
    if not type_dir.is_dir():
        return False
    # Try direct file match: <type>/<rid>.<ext>
    for ext in (".md", ".py", ".yaml", ".json"):
        if (type_dir / f"{rid}{ext}").is_file():
            return True
    # Try subdirectory match: <type>/<rid>/<anything>
    rid_dir = type_dir / rid
    if rid_dir.is_dir():
        return any(rid_dir.rglob("*"))
    return False


def resolve_resources(
    project_type_id: str,
    selected_capability_ids: list[str],
    stack_bundle_id: str,
    catalog_dir: Path | None = None,
    resources_root: Path | None = None,
) -> ResourceSelectionResult:
    """Resolve project type + capabilities + stack bundle to resource selections.

    Args:
        project_type_id: Canonical project type ID (e.g. "saas").
        selected_capability_ids: Canonical capability IDs chosen by the user.
        stack_bundle_id: Canonical stack bundle ID.
        catalog_dir: Directory containing catalog files. Defaults to
            <repo_root>/catalog.
        resources_root: Directory containing bundled resources. Defaults to
            <repo_root>/resources.

    Returns:
        A ResourceSelectionResult. Each entry has id, type, version,
        provenance, and selection_reason. Errors are collected rather
        than raised.
    """
    if catalog_dir is None:
        catalog_dir = DEFAULT_CATALOG_DIR
    catalog_dir = Path(catalog_dir)
    if resources_root is None:
        resources_root = Path(__file__).resolve().parent.parent / "resources"

    errors: list[str] = []
    resources: list[ResourceSelection] = []

    # Load resource requirements catalog
    raw = _load_resource_requirements(catalog_dir)

    # Build lookup: project_type_id -> list of resource dicts
    req_by_type: dict[str, list[dict]] = {}
    for entry in raw:
        pt_id = entry.get("project_type")
        if pt_id:
            req_by_type.setdefault(pt_id, []).extend(entry.get("resources", []))

    # Resolve project type resources
    pt_resources = req_by_type.get(project_type_id, [])
    seen: set[tuple[str, str]] = set()

    for res_def in pt_resources:
        rid = res_def.get("id", "")
        rtype = res_def.get("type", "")
        reason = res_def.get("reason", f"project-type:{project_type_id}")

        if not rid or not rtype:
            errors.append(f"Invalid resource entry: missing id or type: {res_def}")
            continue

        key = (rtype, rid)
        if key in seen:
            errors.append(f"Duplicate resource in catalog: {rtype}:{rid}")
            continue
        seen.add(key)

        if not _resource_exists(resources_root, rtype, rid):
            errors.append(
                f"Resource not found: {rtype}:{rid} "
                f"(expected at resources/{type_dir_name(rtype)}/{rid}.*"
            )
            continue

        resources.append(
            ResourceSelection(
                id=rid,
                type=rtype,
                version="1.0.0",
                provenance_source="bundled",
                provenance_commit_sha="8b61d297dc07772a000b85fc93138c8aefd21c45",
                provenance_license="MIT",
                selection_reason=reason,
            )
        )

    # Resolve capability-based resources. A resource whose reason is
    # ``capability:<cap-id>`` is selected when that capability is chosen.
    # Matching is exact on the capability id declared in the reason (never
    # on the resource id, which would mismatch e.g. security-auditor for
    # authentication).
    cap_to_resources: dict[str, list[dict]] = {}
    for entry in raw:
        for res_def in entry.get("resources", []):
            rid = res_def.get("id", "")
            rtype = res_def.get("type", "")
            reason = res_def.get("reason", "")
            if reason.startswith("capability:"):
                derived_cap_id = reason[len("capability:"):]
                cap_to_resources.setdefault(derived_cap_id, []).append(
                    {"id": rid, "type": rtype, "reason": reason}
                )

    for cap_id in selected_capability_ids:
        for defn in cap_to_resources.get(cap_id, []):
            rid = defn["id"]
            rtype = defn["type"]
            key = (rtype, rid)
            if key in seen:
                continue
            if not _resource_exists(resources_root, rtype, rid):
                errors.append(
                    f"Resource not found: {rtype}:{rid} "
                    f"(capability: {cap_id})"
                )
                continue
            seen.add(key)
            resources.append(
                ResourceSelection(
                    id=rid,
                    type=rtype,
                    version="1.0.0",
                    provenance_source="bundled",
                    provenance_commit_sha="8b61d297dc07772a000b85fc93138c8aefd21c45",
                    provenance_license="MIT",
                    selection_reason=defn["reason"],
                )
            )

    return ResourceSelectionResult(
        resources=resources,
        project_type_id=project_type_id,
        selected_capability_ids=selected_capability_ids,
        stack_bundle_id=stack_bundle_id,
        errors=errors,
    )


def type_dir_name(rtype: str) -> str:
    """Map canonical resource type ID to directory name under resources/."""
    return RESOURCE_TYPE_TO_DIR.get(rtype, rtype)

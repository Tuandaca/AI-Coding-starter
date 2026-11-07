"""
Resource registry / catalog layer (M6.3).

Loads canonical resources from two sources:

  * Bundled filesystem resources (``resources/``) — locally authored, MIT.
  * Agency Agents canonical catalog (``catalog/agency-agents.yaml``) — imported
    from upstream ``msitarzewski/agency-agents`` at a pinned commit.

The resolver (M6.4) depends only on this registry; it never reads Agency file
layout, GitHub structure, or upstream paths directly.

Standard library only. No network. Deterministic.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from core.domain.contracts.id_policy import is_valid_id


@dataclass(frozen=True)
class CanonicalResourceRef:
    """Lightweight reference to a registered canonical resource."""

    id: str
    type: str  # agent | skill | rule | workflow | script | template | shared-module | instruction
    source: str  # "bundled" | "agency-agents"
    division: Optional[str] = None  # agency division (None for bundled)
    name: str = ""
    description: str = ""
    capabilities: list[str] = field(default_factory=list)
    project_types: list[str] = field(default_factory=list)
    provenance: dict = field(default_factory=dict)

    def matches_project_type(self, project_type_id: str) -> bool:
        if not project_type_id or project_type_id in ("not-decided", "other", ""):
            return False
        return project_type_id in self.project_types

    def matches_capability(self, capability_id: str) -> bool:
        if not capability_id:
            return False
        return capability_id in self.capabilities


class ResourceRegistry:
    """In-memory registry of canonical resources keyed by (type, id).

    Collision-safe: ``agent:security-auditor`` and
    ``skill:security-auditor`` are distinct entries.
    """

    def __init__(self) -> None:
        self._resources: dict[tuple[str, str], CanonicalResourceRef] = {}

    # -- registration -------------------------------------------------------
    def add(self, ref: CanonicalResourceRef) -> None:
        key = (ref.type, ref.id)
        self._resources[key] = ref

    # -- lookup -------------------------------------------------------------
    def get(self, rtype: str, rid: str) -> Optional[CanonicalResourceRef]:
        return self._resources.get((rtype, rid))

    def list_by_type(self, rtype: str) -> list[CanonicalResourceRef]:
        return sorted(
            (r for (t, _), r in self._resources.items() if t == rtype),
            key=lambda r: r.id,
        )

    def list_agents(self) -> list[CanonicalResourceRef]:
        return self.list_by_type("agent")

    def all(self) -> list[CanonicalResourceRef]:
        return sorted(self._resources.values(), key=lambda r: (r.type, r.id))

    def __len__(self) -> int:
        return len(self._resources)


class ResourceCatalogLoader:
    """Loads canonical resources into a :class:`ResourceRegistry`.

    Sources:
      * ``resources/`` bundled tree — one entry per file/dir with known type.
      * ``catalog/agency-agents.yaml`` — imported Agency Agents catalog.
    """

    # Directory name → canonical resource type (mirrors resource_resolver).
    RESOURCE_TYPE_TO_DIR = {
        "agent": "agents",
        "skill": "skills",
        "shared-module": "shared",
        "workflow": "workflows",
        "script": "scripts",
        "template": "core",
        "rule": "rules",
    }

    # Reverse mapping: directory → type.
    _DIR_TO_TYPE = {v: k for k, v in RESOURCE_TYPE_TO_DIR.items()}

    # Bundled resource provenance (locally authored, M2 snapshot).
    BUNDLED_PROVENANCE = {
        "source": "bundled",
        "commit_sha": "8b61d297dc07772a000b85fc93138c8aefd21c45",
        "license": "MIT",
        "reviewed_date": "2026-11-06",
        "transformation": "none",
    }

    def __init__(
        self,
        resources_root: Path,
        agency_catalog_path: Optional[Path] = None,
    ) -> None:
        self.resources_root = Path(resources_root)
        self.agency_catalog_path = (
            Path(agency_catalog_path) if agency_catalog_path else None
        )

    def load(self) -> ResourceRegistry:
        """Load all canonical resources into a registry (deterministic order)."""
        registry = ResourceRegistry()
        self._load_bundled(registry)
        self._load_agency(registry)
        return registry

    # -- bundled ------------------------------------------------------------
    def _load_bundled(self, registry: ResourceRegistry) -> None:
        if not self.resources_root.is_dir():
            return
        for type_dir_name, rtype in sorted(self._DIR_TO_TYPE.items()):
            type_dir = self.resources_root / type_dir_name
            if not type_dir.is_dir():
                continue
            for entry in sorted(type_dir.iterdir()):
                ref = self._make_bundled_ref(type_dir, entry, rtype)
                if ref is not None:
                    registry.add(ref)

    def _make_bundled_ref(
        self, type_dir: Path, entry: Path, rtype: str
    ) -> Optional[CanonicalResourceRef]:
        rid = entry.stem
        if not rid:
            return None
        name = rid.replace("-", " ").replace("_", " ").title()
        description = f"Bundled {rtype} resource: {rid}"
        return CanonicalResourceRef(
            id=rid,
            type=rtype,
            source="bundled",
            division=None,
            name=name,
            description=description,
            capabilities=[],
            project_types=[],
            provenance=dict(self.BUNDLED_PROVENANCE),
        )

    # -- agency -------------------------------------------------------------
    def _load_agency(self, registry: ResourceRegistry) -> None:
        if self.agency_catalog_path is None or not self.agency_catalog_path.is_file():
            return
        with open(self.agency_catalog_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        agents = data.get("agents", [])
        if not isinstance(agents, list):
            return
        for item in agents:
            if not isinstance(item, dict):
                continue
            rid = item.get("id")
            if not rid or not is_valid_id(rid):
                continue
            ref = CanonicalResourceRef(
                id=str(rid),
                type="agent",
                source="agency-agents",
                division=item.get("division") or "",
                name=str(item.get("name", "")),
                description=str(item.get("description", "")),
                capabilities=list(item.get("capabilities", []) or []),
                project_types=list(item.get("project_types", []) or []),
                provenance=dict(item.get("provenance", {})),
            )
            registry.add(ref)


def build_default_registry(
    resources_root: Optional[Path] = None,
    agency_catalog_path: Optional[Path] = None,
) -> ResourceRegistry:
    """Build the default registry (bundled + agency catalog)."""
    if resources_root is None:
        resources_root = Path(__file__).resolve().parent.parent.parent / "resources"
    if agency_catalog_path is None:
        agency_catalog_path = (
            Path(__file__).resolve().parent.parent.parent / "catalog" / "agency-agents.yaml"
        )
    loader = ResourceCatalogLoader(resources_root, agency_catalog_path)
    return loader.load()

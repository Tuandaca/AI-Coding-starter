"""
Portable project specification (project.yaml) for M4.

project.yaml is the machine-authoritative project identity and configuration.
It is owned by the generated project, not by any coding runtime.

Format policy: the file uses the ``.yaml`` extension and intentionally
contains JSON-compatible YAML 1.2 syntax, so the starter remains stdlib-only
and reads/writes it deterministically with ``json``. No PyYAML or custom YAML
parser is used.

Public entry points:
  * :func:`generate_project_id` - canonical project ID from a project name
  * :func:`build_project_spec` - build a :class:`ProjectSpec` from M3 state
  * :func:`write_project_spec` / :func:`read_project_spec` - atomic-ish round trip
  * :func:`round_trip_spec` - write then read back for equivalence checks
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core.domain.contracts.id_policy import (
    CanonicalId,
    InvalidIdError,
    is_valid_id,
    make_id,
    normalize_id_candidate,
)
from core.domain.contracts.project_state import ProjectSpec

CANONICAL_STATE_DIR = ".ai-coding-starter"
PROJECT_YAML = "project.yaml"
SCHEMA_VERSION = "1.0.0"
GENERATED_BY = "ai-coding-starter-generator"


def _utc_now() -> str:
    """Current time as ISO 8601 UTC (deterministic format, no locale)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_project_id(name: str) -> str:
    """
    Generate a deterministic, safe canonical project ID from a project name.

    The ID follows the M1 ID policy (lowercase kebab-case, no version labels,
    stable, human-readable). Invalid characters are collapsed/sanitized; names
    that cannot yield a valid ID fall back to ``project``. No random UUID and no
    filesystem path is used as the visible identity.
    """
    candidate = normalize_id_candidate(name or "") or "project"
    if not is_valid_id(candidate):
        candidate = "project"
    return candidate


def build_project_spec(
    project_name: str,
    project_type_id: Optional[str] = None,
    capabilities: Optional[list[str]] = None,
    stack_bundle_id: Optional[str] = None,
    description: str = "",
) -> ProjectSpec:
    """Build a machine-authoritative :class:`ProjectSpec` from M3 selection state.

    All IDs are stored as canonical IDs (never display names, never versions).
    """
    now = _utc_now()
    project_id = generate_project_id(project_name)
    return ProjectSpec(
        id=make_id(project_id),
        name=project_name,
        created_at=now,
        updated_at=now,
        description=description,
        project_type=make_id(project_type_id) if project_type_id else None,
        capabilities=[make_id(c) for c in (capabilities or [])],
        stack_bundle=make_id(stack_bundle_id) if stack_bundle_id else None,
    )


def spec_to_json_text(spec: ProjectSpec) -> str:
    """Serialize a spec to deterministic, UTF-8, JSON-compatible YAML text."""
    return json.dumps(spec.to_dict(), indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def write_project_spec(dest_dir: Path | str, spec: ProjectSpec) -> Path:
    """Write ``project.yaml`` under ``<dest>/.ai-coding-starter/``.

    Returns the written path. Creates the state directory if missing.
    """
    state_dir = Path(dest_dir) / CANONICAL_STATE_DIR
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / PROJECT_YAML
    path.write_text(spec_to_json_text(spec), encoding="utf-8")
    return path


def read_project_spec(path: Path | str) -> ProjectSpec:
    """Read and validate ``project.yaml``.

    Rejects malformed/unsupported structure clearly; never falls back to
    Markdown as authority.
    """
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot read project.yaml at {path}: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported or missing schema_version in {path}")
    if "project" not in data or not isinstance(data["project"], dict):
        raise ValueError(f"Missing 'project' object in {path}")
    return ProjectSpec.from_dict(data)


def round_trip_spec(spec: ProjectSpec, dest_dir: Path | str) -> ProjectSpec:
    """Write a spec then read it back, returning the re-parsed spec."""
    path = write_project_spec(dest_dir, spec)
    return read_project_spec(path)

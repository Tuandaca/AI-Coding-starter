#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Maintainer-side Agency Agents importer (M6.1).

Synchronises the Agency Agents specialist catalog (upstream
``msitarzewski/agency-agents``) into the AI-Coding-starter canonical catalog
at ``catalog/agency-agents.yaml``.

This script is a **maintainer operation only**. It is never invoked by
``new_project.py`` or by end-user project generation. No network access is
performed here — the maintainer must first provide a local, already-checked-out
copy of the Agency Agents source (e.g. via ``git clone`` + ``git checkout <sha>``).

Design principles (per project rules):
  * Stdlib only. No PyYAML, no network, no LLM.
  * Deterministic: same source tree -> byte-equivalent catalog output.
  * Non-mutating: the upstream source is read-only.
  * Full provenance: every agent records upstream repo, commit SHA, license,
    import date, and content hash.
  * Bounded activation is NOT done here: the importer only normalizes the full
    catalog. Project/task resolution + bounded team selection happens in the
    resolver (M6.3/M6.4).
  * Upstream slug (filename stem) is preserved as the canonical ``id``.

Usage (maintainer):
    python scripts/sync_agency_agents.py \
        --source /path/to/agency-agents \
        [--upstream-commit <sha>] \
        [--output catalog/agency-agents.yaml] \
        [--check-license]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Canonical ID policy: lowercase kebab-case, no path separators, no traversal.
# Mirrors core/domain/contracts/id_policy.py so the catalog stays consistent
# with the resolver's validation.
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$")


def is_valid_id(candidate: str) -> bool:
    """Return True if ``candidate`` satisfies the canonical ID policy.

    Rules:
      * lowercase letters, digits, hyphens only;
      * must start and end with alphanumeric;
      * no consecutive hyphens;
      * no path separators or traversal (``/``, ``\\``, ``..``).
    """
    if not isinstance(candidate, str) or not candidate:
        return False
    if "/" in candidate or "\\" in candidate:
        return False
    if ".." in candidate.split("/") or ".." in candidate.split("\\"):
        return False
    if "--" in candidate:
        return False
    return bool(_ID_RE.match(candidate))


def sha256_file(path: Path) -> str:
    """Return ``sha256:<hexdigest>`` for the raw bytes of ``path``."""
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


# ---------------------------------------------------------------------------
# Frontmatter parsing (stdlib-only, minimal YAML subset)
# ---------------------------------------------------------------------------

_FRONTMATTER_FENCE = "---"


def _strip_yaml_scalar(raw: str) -> str:
    """Strip one matching outer quote pair from a YAML scalar value."""
    v = raw.strip()
    if len(v) >= 2:
        if v[0] == '"' and v[-1] == '"':
            v = v[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        elif v[0] == "'" and v[-1] == "'":
            v = v[1:-1].replace("''", "'")
    return v


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse YAML frontmatter delimited by ``---`` fences.

    Supports the subset actually used by Agency Agents agent files:
    ``key: value`` pairs with optional single/double-quoted scalars and simple
    indented continuation lines. Unknown or unparseable lines are skipped
    rather than raising, so a malformed agent is reported as invalid instead of
    crashing the whole import.

    Returns a dict of field -> string value (may be empty).
    """
    fields: dict[str, str] = {}
    lines = text.splitlines()
    if not lines or lines[0].strip() != _FRONTMATTER_FENCE:
        return fields

    fence_count = 1  # opening fence seen on lines[0]
    current_key: str | None = None
    current_val: list[str] = []

    def flush() -> None:
        nonlocal current_key, current_val
        if current_key is not None:
            fields[current_key] = _strip_yaml_scalar(" ".join(current_val).strip())
        current_key = None
        current_val = []

    for line in lines[1:]:
        stripped = line.strip()
        if stripped == _FRONTMATTER_FENCE:
            fence_count += 1
            flush()
            if fence_count >= 2:
                break  # end of frontmatter
            continue
        if fence_count == 0:
            continue  # before opening fence
        # Inside frontmatter (fence_count == 1)
        if current_key is not None and re.match(r"^[ \t]+[^ \t]", line):
            # Indented continuation of a plain scalar value.
            current_val.append(stripped)
            continue
        flush()
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", line)
        if not m:
            continue
        current_key = m.group(1)
        current_val = [m.group(2)]
    flush()
    return fields


# ---------------------------------------------------------------------------
# Import logic
# ---------------------------------------------------------------------------

# Directories that are NOT divisions (no installable agent frontmatter).
NON_DIVISION_DIRS = frozenset({
    ".github", "examples", "integrations", "scripts", "strategy",
})

# Frontmatter fields we preserve from upstream.
FRONTMATTER_FIELDS = ("name", "description", "color", "emoji", "vibe", "tools")


class ImportError(Exception):
    """Raised when the Agency source cannot be imported."""


@dataclass
class AgentEntry:
    """A single normalized agent record from the Agency catalog."""

    id: str
    name: str
    type: str
    division: str
    description: str
    capabilities: list[str]
    project_types: list[str]
    tags: list[str]
    source_path: str
    version: str
    provenance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "division": self.division,
            "description": self.description,
            "capabilities": self.capabilities,
            "project_types": self.project_types,
            "tags": self.tags,
            "source_path": self.source_path,
            "version": self.version,
            "provenance": dict(self.provenance),
        }


def _iter_agent_files(source: Path) -> list[tuple[str, Path]]:
    """Discover all agent .md files under division directories.

    Returns a list of ``(relative_path, absolute_path)`` sorted deterministically
    by relative path. Only files whose first line is ``---`` (YAML frontmatter)
    are treated as agents.
    """
    found: list[tuple[str, Path]] = []
    for entry in sorted(source.iterdir()):
        if not entry.is_dir():
            continue
        rel = entry.name
        if rel in NON_DIVISION_DIRS:
            continue
        if rel.startswith("."):
            continue
        # A division directory must contain at least one agent file; we still
        # scan it and will report if it yields none.
        for md_file in sorted(entry.glob("*.md")):
            try:
                first_line = md_file.read_text(encoding="utf-8").splitlines()[0]
            except (OSError, UnicodeError):
                continue
            if first_line.strip() == _FRONTMATTER_FENCE:
                found.append((str(md_file.relative_to(source).as_posix()), md_file))
    found.sort(key=lambda item: item[0])
    return found


def import_catalog(
    source: Path,
    upstream_commit: str,
    upstream_repo: str,
    license_: str,
    imported_date: str,
    catalog_version: str,
) -> dict[str, Any]:
    """Import and normalize the full Agency Agents catalog from ``source``.

    Returns a dict suitable for JSON serialization (the canonical catalog).
    Raises :class:`ImportError` on fatal problems (missing divisions.json,
    no agents found, duplicate slugs).
    """
    if not source.is_dir():
        raise ImportError(f"Agency source directory not found: {source}")

    divisions_path = source / "divisions.json"
    if not divisions_path.is_file():
        raise ImportError(f"divisions.json not found in {source}")
    with open(divisions_path, "r", encoding="utf-8") as handle:
        divisions_data = json.load(handle)
    divisions_meta: dict[str, dict[str, Any]] = divisions_data.get("divisions", {})

    agent_files = _iter_agent_files(source)
    if not agent_files:
        raise ImportError(f"No agent .md files found in {source}")

    seen_ids: set[str] = set()
    agents: list[AgentEntry] = []
    errors: list[str] = []
    warnings: list[str] = []

    for rel_path, abs_path in agent_files:
        # Canonical id = upstream filename stem (slug), preserved as-is.
        agent_id = abs_path.stem

        # --- Validate id policy -------------------------------------------
        if not is_valid_id(agent_id):
            errors.append(
                f"Invalid agent id '{agent_id}' in {rel_path}: "
                f"does not satisfy canonical ID policy (kebab-case, no traversal)"
            )
            continue

        # --- Duplicate detection ------------------------------------------
        if agent_id in seen_ids:
            errors.append(f"Duplicate agent slug '{agent_id}' (seen at {rel_path})")
            continue
        seen_ids.add(agent_id)

        # --- Read + parse frontmatter -------------------------------------
        try:
            raw_text = abs_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"Cannot read agent {rel_path}: {exc}")
            continue
        fm = parse_frontmatter(raw_text)
        name = fm.get("name", "")
        description = fm.get("description", "")
        if not name:
            errors.append(f"Agent {rel_path}: missing frontmatter 'name'")
            continue
        if not description:
            warnings.append(f"Agent {rel_path}: empty frontmatter 'description'")

        # --- Division metadata --------------------------------------------
        division = os.path.dirname(rel_path) or "root"
        if division not in divisions_meta:
            warnings.append(
                f"Agent {rel_path}: division '{division}' not in divisions.json"
            )

        # --- Provenance ----------------------------------------------------
        provenance: dict[str, Any] = {
            "source": "agency-agents",
            "upstream_repo": upstream_repo,
            "upstream_commit": upstream_commit,
            "license": license_,
            "imported_date": imported_date,
            "content_hash": sha256_file(abs_path),
        }

        agents.append(
            AgentEntry(
                id=agent_id,
                name=name,
                type="agent",
                division=division,
                description=description,
                capabilities=[],  # populated by resolver based on project type
                project_types=[],  # populated by resolver based on project type
                tags=[],  # populated by resolver
                source_path=rel_path,
                version="1.0.0",
                provenance=provenance,
            )
        )

    if errors:
        raise ImportError("Import validation failed:\n" + "\n".join(sorted(errors)))

    # Deterministic ordering by id.
    agents.sort(key=lambda a: a.id)

    catalog: dict[str, Any] = {
        "schema_version": "1.0.0",
        "catalog_version": catalog_version,
        "imported_date": imported_date,
        "upstream_repo": upstream_repo,
        "upstream_commit": upstream_commit,
        "license": license_,
        "division_count": len(divisions_meta),
        "agent_count": len(agents),
        "agents": [a.to_dict() for a in agents],
    }
    if warnings:
        catalog["_warnings"] = sorted(warnings)
    return catalog


def write_catalog(catalog: dict[str, Any], output: Path) -> None:
    """Write the catalog as deterministic JSON-compatible YAML text."""
    output.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(catalog, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    output.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import Agency Agents catalog into AI-Coding-starter canonical catalog.",
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Local path to a checked-out Agency Agents repository (read-only).",
    )
    parser.add_argument(
        "--upstream-commit",
        default=None,
        help="Upstream commit SHA to record in provenance. Defaults to the "
             "pinned SHA recorded in catalog/upstream-sources.yaml.",
    )
    parser.add_argument(
        "--output",
        default="catalog/agency-agents.yaml",
        help="Output catalog path (default: catalog/agency-agents.yaml).",
    )
    parser.add_argument(
        "--upstream-repo",
        default="https://github.com/msitarzewski/agency-agents",
        help="Upstream repository URL (for provenance).",
    )
    parser.add_argument(
        "--license",
        default="MIT",
        help="Upstream license (for provenance).",
    )
    parser.add_argument(
        "--imported-date",
        default=None,
        help="Import date (ISO 8601). Defaults to current UTC date.",
    )
    parser.add_argument(
        "--catalog-version",
        default=None,
        help="Catalog version string. Defaults to <imported-date>-1.",
    )
    parser.add_argument(
        "--check-license",
        action="store_true",
        help="Exit non-zero if upstream license is not MIT.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    source = Path(args.source).resolve()
    if not source.is_dir():
        print(f"ERROR: source directory not found: {source}", file=sys.stderr)
        return 1

    # Resolve pinned commit from upstream-sources.yaml if not given explicitly.
    upstream_commit = args.upstream_commit
    if upstream_commit is None:
        us_path = Path(__file__).resolve().parent.parent / "catalog" / "upstream-sources.yaml"
        try:
            with open(us_path, "r", encoding="utf-8") as handle:
                us = json.load(handle)
            for src in us.get("sources", []):
                if src.get("id") == "agency-agents":
                    upstream_commit = src.get("commit_sha")
                    break
        except (OSError, ValueError):
            pass
    if not upstream_commit:
        print("ERROR: no upstream commit resolved (pass --upstream-commit)", file=sys.stderr)
        return 1

    # Optional license check.
    if args.check_license:
        license_file = source / "LICENSE"
        if license_file.is_file():
            head = license_file.read_text(encoding="utf-8", errors="replace").splitlines()[0]
            if "MIT License" not in head and "MIT" not in head[:80]:
                print("ERROR: upstream license is not MIT", file=sys.stderr)
                return 1
        else:
            print("WARNING: no LICENSE file in source", file=sys.stderr)

    from datetime import datetime, timezone

    imported_date = args.imported_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    catalog_version = args.catalog_version or f"{imported_date}-1"

    try:
        catalog = import_catalog(
            source=source,
            upstream_commit=upstream_commit,
            upstream_repo=args.upstream_repo,
            license_=args.license,
            imported_date=imported_date,
            catalog_version=catalog_version,
        )
    except ImportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    output = Path(args.output).resolve()
    write_catalog(catalog, output)

    agent_count = catalog["agent_count"]
    division_count = catalog["division_count"]
    print(
        f"Imported {agent_count} agents from {division_count} divisions "
        f"(upstream {upstream_commit[:12]}) -> {output}"
    )
    if catalog.get("_warnings"):
        print(f"  ({len(catalog['_warnings'])} warnings; see catalog _warnings)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

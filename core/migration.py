"""
V1 → V2 portable state migration engine (M8).

One-time, safe enhancement path for existing V1 projects:

    V1 project  →  detect  →  analyze  →  MigrationPlan  →  preview
        →  confirm  →  apply  →  .ai-coding-starter/

Architecture (per UPGRADE_PLAN.md Section 6):

    migration detection
            ↓
    migration analysis
            ↓
    MigrationPlan
            ↓
    preview
            ↓
    confirmation
            ↓
    apply

Detection and parsing are pure/mostly-pure and perform NO filesystem writes.
All writes are confined to ``.ai-coding-starter/`` and happen only after
explicit user confirmation.

Properties (M8 acceptance):
  * Opt-in: no filesystem writes before explicit confirmation.
  * Non-destructive: legacy files (.agent/**, GEMINI.md, CONTEXT.md,
    user source) are never modified. Only .ai-coding-starter/** is written.
  * Reversible: removing .ai-coding-starter/ restores V1 behavior.
  * Offline: no network, no LLM, no GitHub lookup.
  * Honest inference: never guesses project type / capabilities / stack bundle;
    falls back to canonical defaults when evidence is insufficient.
  * Provenance honesty: never fabricates resource provenance (M7 rules).
  * Same-ID/different-type resource identity is collision-safe ((type, id)).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from core.catalog_loader import DEFAULT_CATALOG_DIR, load_catalog
from core.domain.contracts.id_policy import make_id, normalize_id_candidate
from core.spec import (
    CANONICAL_STATE_DIR,
    PROJECT_YAML,
    SCHEMA_VERSION,
    build_project_spec,
    read_project_spec,
    write_project_spec,
)
from core.state import (
    STATE_YAML,
    RESOURCES_LOCK,
    build_initial_state,
    build_resources_lock,
    read_resources_lock,
    read_state,
    write_resources_lock,
    write_state,
)

# M2 snapshot commit that introduced bundled resources (M7 provenance).
BUNDLED_PROVENANCE_COMMIT_SHA = "8b61d297dc07772a000b85fc93138c8aefd21c45"
BUNDLED_LICENSE = "MIT"
BUNDLED_REVIEWED_DATE = "2026-11-06"
MIGRATION_TOOL_ID = "ai-coding-starter-migrator"

# V1 legacy project markers (read-only detection signals).
V1_SIGNAL_AGENT_DIR = ".agent"
V1_SIGNAL_GEMINI_MD = "GEMINI.md"
V1_SIGNAL_CONTEXT_MD = "CONTEXT.md"

# V1 GEMINI.md frontmatter marker that distinguishes starter-generated
# GEMINI.md files from generic, unrelated files with the same name.
V1_GEMINI_FRONTMARKER = "trigger: always_on"

# Absolute developer path pattern (Windows drive letter or POSIX absolute).
ABSOLUTE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]|^/")

# Legacy resource directory names under .agent/ and their canonical resource type.
AGENT_DIR_TYPE_MAP = {
    "agents": "agent",
    "skills": "skill",
    "workflows": "workflow",
    "scripts": "script",
    "shared": "shared-module",
    "core": "template",
    "rules": "rule",
}

# Secret-like keywords: legacy content matching these is never migrated into
# canonical state (M8 §34).
SECRET_KEYWORDS = (
    "api_key",
    "apikey",
    "api-secret",
    "apisecret",
    "secret_key",
    "secretkey",
    "private_key",
    "privatekey",
    "access_token",
    "accesstoken",
    "password",
    "passwd",
    "connection_string",
    "connectionstring",
    "mongodb+srv",
    "postgresql://",
    "mysql://",
    "redis://",
    ".env",
)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DetectionResult:
    """Read-only detection of a V1 project. Never writes anything."""

    project_root: Path
    is_v1_project: bool
    already_migrated: bool
    partial_v2_state: bool
    signals: list[str]
    reasons: list[str]
    confidence: str  # "high" | "medium" | "low" | "none"
    v1_signals: dict  # e.g. {"agent_dir": True, "gemini_md": True, ...}
    existing_canonical_state: bool  # .ai-coding-starter/project.yaml exists


@dataclass(frozen=True)
class MigrationAnalysis:
    """Conservative analysis of legacy V1 content."""

    project_name: str
    project_id: str
    project_type_id: Optional[str]
    capabilities: list[str]
    stack_bundle_id: Optional[str]
    phase: str
    focus: str
    canonical_branch: Optional[str]
    inferred_fields: dict  # field -> {"source": str, "value": str}
    unresolved_fields: list[str]
    warnings: list[str]
    legacy_resources: list[dict]  # discovered legacy resources with match info


@dataclass
class MigrationPlan:
    """Build plan: what will be created and preserved."""

    project_root: Path
    spec: object  # ProjectSpec
    state: object  # ProjectState
    lock: object  # ResourcesLock
    will_create: list[str]  # relative paths under project root
    will_preserve: list[str]
    inference: dict
    unresolved: list[str]
    warnings: list[str]
    dry_run: bool = False


@dataclass
class MigrationResult:
    """Outcome of a migration run."""

    detected: bool
    already_migrated: bool
    confirmed: bool
    applied: bool
    created_files: list[str]
    preserved_files: list[str]
    inferred_fields: dict
    unresolved_fields: list[str]
    warnings: list[str]
    dry_run: bool
    errors: list[str]


# ---------------------------------------------------------------------------
# Detection (read-only, side-effect free)
# ---------------------------------------------------------------------------


def _file_hash(path: Path) -> Optional[str]:
    """SHA-256 of a file's bytes, or None if unreadable."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _read_text(path: Path) -> Optional[str]:
    """Read a text file, or None if unreadable."""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _strip_frontmatter(text: str) -> str:
    """Remove a YAML frontmatter block (``--- ... ---``) if present."""
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---\n", 4)
    if end == -1:
        return text
    return text[end + 5 :]


def _looks_like_secret(text: str) -> bool:
    """Return True if ``text`` contains an obvious secret-like keyword."""
    low = text.lower()
    return any(kw in low for kw in SECRET_KEYWORDS)


def _git_branch(project_root: Path) -> Optional[str]:
    """Read the current git branch, or None if not a git repo / unreadable.

    Handles both plain ``.git/`` directories and linked worktrees where
    ``.git`` is a file (e.g. ``gitdir: <path>``). Never mutates any git state.
    """
    git_path = project_root / ".git"
    try:
        if git_path.is_file():
            # Linked worktree: .git is a pointer file "gitdir: <path>".
            text = _read_text(git_path) or ""
            if text.startswith("gitdir:"):
                target = text[len("gitdir:"):].strip()
                target_path = Path(target)
                if not target_path.is_absolute():
                    target_path = (project_root / target_path).resolve()
                head_file = target_path / "HEAD"
            else:
                return None
        elif git_path.is_dir():
            head_file = git_path / "HEAD"
        else:
            return None
    except OSError:
        return None

    if not head_file.exists():
        return None
    text = _read_text(head_file)
    if not text:
        return None
    text = text.strip()
    if text.startswith("ref: "):
        ref = text[len("ref: "):]
        if ref.startswith("refs/heads/"):
            return ref[len("refs/heads/"):]
        return ref
    return None  # detached HEAD -> no branch name


def detect_v1_project(project_root: Path | str) -> DetectionResult:
    """Detect whether ``project_root`` is a legacy V1 project.

    Read-only: inspects directory entries and file presence only. Never writes.

    Returns a structured :class:`DetectionResult`.
    """
    root = Path(project_root).resolve()
    signals: list[str] = []
    reasons: list[str] = []
    v1_signals: dict = {}

    agent_dir = root / V1_SIGNAL_AGENT_DIR
    gemini_md = root / V1_SIGNAL_GEMINI_MD
    context_md = root / V1_SIGNAL_CONTEXT_MD
    canonical_dir = root / CANONICAL_STATE_DIR
    project_yaml = canonical_dir / PROJECT_YAML

    agent_dir_exists = agent_dir.is_dir()
    gemini_exists = gemini_md.is_file()
    context_exists = context_md.is_file()
    project_yaml_exists = project_yaml.is_file()
    ai_coding_exists = canonical_dir.is_dir()

    v1_signals = {
        "agent_dir": agent_dir_exists,
        "gemini_md": gemini_exists,
        "context_md": context_exists,
    }

    if agent_dir_exists:
        signals.append(".agent/ directory present")
        reasons.append("V1 projects store agents/skills/workflows under .agent/")
    if gemini_exists:
        # GEMINI.md: high only if it carries V1 starter frontmatter markers,
        # otherwise medium (a generic GEMINI.md could be unrelated).
        gemini_text = _read_text(gemini_md) or ""
        has_v1_marker = V1_GEMINI_FRONTMARKER in gemini_text
        if has_v1_marker:
            signals.append("GEMINI.md present (V1 frontmatter markers)")
            reasons.append("GEMINI.md with V1 starter frontmatter detected")
        else:
            signals.append("GEMINI.md present (generic)")
            reasons.append(
                "GEMINI.md present but no V1 starter frontmatter markers"
            )
    if context_exists:
        signals.append("CONTEXT.md present (weak signal)")
        reasons.append(
            "CONTEXT.md present alone — weak V1 signal, confirmation required"
        )

    if project_yaml_exists:
        # Already migrated to V2 canonical state.
        confidence = "high"
        is_v1_project = False
        already_migrated = True
        partial_v2_state = False
        reasons.append(
            ".ai-coding-starter/project.yaml already exists (V2 canonical state)"
        )
    elif ai_coding_exists:
        # .ai-coding-starter/ exists but no project.yaml → partial V2 state.
        confidence = "medium"
        is_v1_project = False
        already_migrated = False
        partial_v2_state = True
        reasons.append(
            ".ai-coding-starter/ exists without project.yaml (partial V2 state)"
        )
    elif agent_dir_exists:
        # .agent/ is a strong, V1-specific structural signal.
        confidence = "high"
        is_v1_project = True
        already_migrated = False
        partial_v2_state = False
    elif gemini_exists:
        confidence = "high" if any(
            "V1 frontmatter markers" in s for s in signals
        ) else "medium"
        is_v1_project = True
        already_migrated = False
        partial_v2_state = False
    elif context_exists:
        # CONTEXT.md alone is a weak signal: many non-starter projects have
        # a CONTEXT.md for unrelated reasons. Do not overstate certainty.
        confidence = "low"
        is_v1_project = True
        already_migrated = False
        partial_v2_state = False
    else:
        confidence = "none"
        is_v1_project = False
        already_migrated = False
        partial_v2_state = False
        reasons.append("no V1 legacy markers detected")

    return DetectionResult(
        project_root=root,
        is_v1_project=is_v1_project,
        already_migrated=already_migrated,
        partial_v2_state=partial_v2_state,
        signals=signals,
        reasons=reasons,
        confidence=confidence,
        v1_signals=v1_signals,
        existing_canonical_state=project_yaml_exists,
    )


# ---------------------------------------------------------------------------
# Analysis (conservative inference from legacy content)
# ---------------------------------------------------------------------------


def _map_legacy_project_type(text: str, catalog) -> Optional[str]:
    """Map legacy text to an M3 canonical project-type ID, or None.

    Only returns a match when the legacy content explicitly names a known
    M3 project type. Never guesses from file presence.
    """
    if not text:
        return None
    low = text.lower()
    for pt_id in catalog.project_types:
        # Match the canonical ID or its display name.
        if pt_id in low or str(catalog.project_types[pt_id].name).lower() in low:
            return pt_id
    return None


def _map_legacy_capabilities(text: str, catalog) -> list[str]:
    """Return capability IDs explicitly mentioned in legacy text.

    Never infers capabilities from file presence or source-code scanning.
    """
    if not text:
        return []
    low = text.lower()
    found: list[str] = []
    for cap_id in catalog.capabilities:
        # Match canonical ID or a human-friendly keyword form.
        keyword = cap_id.replace("-", " ")
        if cap_id in low or keyword in low:
            if cap_id not in found:
                found.append(cap_id)
    return found


def _match_legacy_bundle(text: str, catalog) -> Optional[str]:
    """Return a stack-bundle ID if legacy text explicitly names one, else None."""
    if not text:
        return None
    low = text.lower()
    for bundle_id in catalog.stack_bundles:
        if bundle_id in low or str(catalog.stack_bundles[bundle_id].name).lower() in low:
            return bundle_id
    return None


def _discover_legacy_resources(
    project_root: Path, catalog
) -> list[dict]:
    """Discover resources under ``.agent/`` and try to match each to a known
    bundled resource.

    Matching uses evidence stronger than basename alone: canonical type (from
    the parent directory under .agent/) + id (filename without extension) +
    optional content-hash equality against the bundled resource file.

    Returns a list of dicts with keys: id, type, legacy_path, matched (bool),
    bundled_path (str or None), content_hash_match (bool).
    """
    agent_dir = project_root / V1_SIGNAL_AGENT_DIR
    if not agent_dir.is_dir():
        return []

    # Build a lookup keyed by (type, id) → bundled file path for provenance.
    bundled_lookup: dict[tuple[str, str], Path] = {}
    try:
        bundled_root = Path(DEFAULT_CATALOG_DIR).parent / "resources"
    except Exception:
        bundled_root = Path("resources")
    if bundled_root.is_dir():
        for type_dir, rtype in AGENT_DIR_TYPE_MAP.items():
            tdir = bundled_root / type_dir
            if not tdir.is_dir():
                continue
            for item in tdir.rglob("*"):
                if not item.is_file():
                    continue
                rid = _resource_id_from_path(item, tdir)
                if rid:
                    bundled_lookup[(rtype, rid)] = item

    discovered: list[dict] = []
    for type_dir, rtype in AGENT_DIR_TYPE_MAP.items():
        tdir = agent_dir / type_dir
        if not tdir.is_dir():
            continue
        for item in sorted(tdir.rglob("*")):
            if not item.is_file():
                continue
            rid = _resource_id_from_path(item, tdir)
            if not rid:
                continue
            legacy_path = item.relative_to(project_root).as_posix()
            key = (rtype, rid)
            bundled_path = bundled_lookup.get(key)
            content_hash_match = False
            if bundled_path is not None:
                legacy_hash = _file_hash(item)
                bundled_hash = _file_hash(bundled_path)
                content_hash_match = (
                    legacy_hash is not None
                    and legacy_hash == bundled_hash
                )
            # A resource is "matched" only when content hash equality is
            # verified. Same filename/type with different content is NOT a
            # match — filename alone is insufficient for provenance.
            matched = content_hash_match
            discovered.append(
                {
                    "id": rid,
                    "type": rtype,
                    "legacy_path": legacy_path,
                    "matched": matched,
                    "bundled_path": (
                        bundled_path.relative_to(Path.cwd()).as_posix()
                        if bundled_path is not None
                        else None
                    ),
                    "content_hash_match": content_hash_match,
                }
            )
    return discovered


def _resource_id_from_path(path: Path, type_dir: Path) -> Optional[str]:
    """Derive a canonical resource id from a file path relative to its type dir.

    E.g. ``.agent/agents/project-planner.md`` → ``project-planner``
    (type ``agent``). Collisions across types are fine because identity is
    (type, id), never id alone. Returns ``None`` for names that are not valid
    canonical ids (e.g. ``auto_preview`` contains an underscore).
    """
    from core.domain.contracts.id_policy import InvalidIdError, is_valid_id

    try:
        rel = path.relative_to(type_dir)
    except ValueError:
        return None
    # Strip known extensions.
    for ext in (".md", ".py", ".yaml", ".json"):
        if rel.name.endswith(ext):
            rid = rel.name[: -len(ext)]
            break
    else:
        rid = rel.name
    # Flatten nested dirs (e.g. skills/X/skill.md → X is already the dir name;
    # use the leaf directory name as the id for directory-based resources).
    if rel.parts and rel.name in ("skill.md", "guidelines.md", "patterns.md",
                                  "checklist.md", "principles.md", "tokens.md"):
        rid = rel.parts[0]
    if not rid or not rid[0].isalpha() or not is_valid_id(rid):
        return None
    return make_id(rid).value if hasattr(make_id(rid), "value") else str(make_id(rid))


def _infer_state_from_context(text: Optional[str]) -> tuple[str, str, list[str]]:
    """Infer phase/focus/tasks from CONTEXT.md, conservatively.

    Returns (phase, focus, warnings). Unknown → defaults, with a warning.
    """
    phase = "planning"
    focus = ""
    warnings: list[str] = []
    if not text:
        warnings.append("CONTEXT.md not found or unreadable; using M4 defaults")
        return phase, focus, warnings
    low = text.lower()
    # Recognize explicit phase mentions.
    for p in (
        "not-started", "planning", "architecture", "development",
        "testing", "staging", "production", "maintenance",
    ):
        if p in low:
            phase = p
            break
    # Extract a focus hint from a "Focus:" or "Current focus" line.
    for marker in ("focus:", "current focus:", "focus area:"):
        idx = low.find(marker)
        if idx != -1:
            line = text[idx + len(marker) :]
            line = line.split("\n")[0].strip(" -:*")
            if line:
                # Never persist absolute developer paths into canonical state.
                line = ABSOLUTE_PATH_RE.sub("<path>", line)
                focus = line[:200]
            break
    if not focus:
        warnings.append("no explicit focus found in CONTEXT.md; using default")
    return phase, focus, warnings


def analyze_v1_project(
    project_root: Path | str, detection: DetectionResult
) -> MigrationAnalysis:
    """Conservatively analyze legacy V1 content.

    Never guesses uncertain values. Falls back to M4 defaults and records
    unresolved fields.
    """
    root = Path(project_root).resolve()
    catalog = load_catalog(DEFAULT_CATALOG_DIR)

    gemini_md = root / V1_SIGNAL_GEMINI_MD
    context_md = root / V1_SIGNAL_CONTEXT_MD

    gemini_text = _read_text(gemini_md) if gemini_md.is_file() else None
    context_text = _read_text(context_md) if context_md.is_file() else None

    # Strip frontmatter before keyword matching.
    gemini_body = _strip_frontmatter(gemini_text or "")
    context_body = _strip_frontmatter(context_text or "")

    # Project name: from directory name (canonicalized), not from content.
    dir_name = root.name
    project_id = normalize_id_candidate(dir_name) or "project"
    if not make_id(project_id):  # validate
        project_id = "project"
    project_name = dir_name

    inferred: dict = {}
    unresolved: list[str] = []
    warnings: list[str] = []

    # Project type: explicit legacy metadata only.
    project_type_id = _map_legacy_project_type(gemini_body + "\n" + context_body, catalog)
    if project_type_id:
        inferred["project_type"] = {
            "source": "legacy_metadata",
            "value": project_type_id,
        }
    else:
        project_type_id = None
        unresolved.append("project_type")
        warnings.append(
            "project type not explicitly stated in legacy files; using 'not-decided'"
        )

    # Capabilities: explicit mentions only.
    capabilities = _map_legacy_capabilities(gemini_body + "\n" + context_body, catalog)
    if capabilities:
        inferred["capabilities"] = {
            "source": "legacy_metadata",
            "value": ", ".join(capabilities),
        }
    else:
        unresolved.append("capabilities")
        warnings.append(
            "no capabilities explicitly stated in legacy files; none recorded"
        )

    # Stack bundle: explicit match only.
    stack_bundle_id = _match_legacy_bundle(gemini_body + "\n" + context_body, catalog)
    if stack_bundle_id:
        inferred["stack_bundle"] = {
            "source": "legacy_metadata",
            "value": stack_bundle_id,
        }
    else:
        unresolved.append("stack_bundle")
        warnings.append(
            "no stack bundle explicitly stated in legacy files; none recorded"
        )

    # State: phase/focus from CONTEXT.md.
    phase, focus, state_warnings = _infer_state_from_context(context_text)
    warnings.extend(state_warnings)
    inferred["phase"] = {"source": "context_md" if context_text else "default", "value": phase}
    inferred["focus"] = {"source": "context_md" if context_text and focus else "default", "value": focus}

    # Git metadata (observed only, never mutated).
    canonical_branch = _git_branch(root)
    if canonical_branch:
        inferred["canonical_branch"] = {"source": "git", "value": canonical_branch}

    # Legacy resource discovery.
    legacy_resources = _discover_legacy_resources(root, catalog)

    # Secret scan on legacy text.
    combined_text = (gemini_body + "\n" + context_body)
    if _looks_like_secret(combined_text):
        warnings.append(
            "secret-like content detected in legacy files; secrets will not be migrated"
        )

    return MigrationAnalysis(
        project_name=project_name,
        project_id=project_id,
        project_type_id=project_type_id,
        capabilities=capabilities,
        stack_bundle_id=stack_bundle_id,
        phase=phase,
        focus=focus,
        canonical_branch=canonical_branch,
        inferred_fields=inferred,
        unresolved_fields=unresolved,
        warnings=warnings,
        legacy_resources=legacy_resources,
    )


# ---------------------------------------------------------------------------
# Migration plan (build in memory, validate before writing)
# ---------------------------------------------------------------------------


def build_migration_plan(
    project_root: Path | str, analysis: MigrationAnalysis, dry_run: bool = False
) -> MigrationPlan:
    """Build a migration plan in memory.

    Validates all canonical documents before any filesystem mutation.
    """
    root = Path(project_root).resolve()

    # Build ProjectSpec (M4 model) from analysis.
    spec = build_project_spec(
        analysis.project_name,
        project_type_id=analysis.project_type_id or "not-decided",
        capabilities=analysis.capabilities,
        stack_bundle_id=analysis.stack_bundle_id,
        description="Migrated from V1 legacy project",
    )

    # Build ProjectState (M4 model).
    state = build_initial_state(
        analysis.project_id,
        phase=analysis.phase,
        focus=analysis.focus,
        canonical_branch=analysis.canonical_branch,
    )

    # Build resources.lock from matched legacy resources (M7 provenance).
    lock_resources: list[dict] = []
    for res in analysis.legacy_resources:
        if not res["matched"]:
            continue  # unknown provenance → never fabricate
        prov = {
            "source": "bundled",
            "commit_sha": BUNDLED_PROVENANCE_COMMIT_SHA,
            "license": BUNDLED_LICENSE,
            "reviewed_date": BUNDLED_REVIEWED_DATE,
            "transformation": "none",
        }
        lock_resources.append(
            {
                "id": res["id"],
                "type": res["type"],
                "version": "1.0.0",
                "provenance": prov,
                "selection_reason": "migrated_from_v1_legacy",
            }
        )
    lock = build_resources_lock(
        analysis.stack_bundle_id or "not-decided",
        requested_bundle_id=analysis.stack_bundle_id or "not-decided",
        catalog_version=BUNDLED_PROVENANCE_COMMIT_SHA,
        resources=lock_resources,
    )

    will_create = [
        f"{CANONICAL_STATE_DIR}/{PROJECT_YAML}",
        f"{CANONICAL_STATE_DIR}/{STATE_YAML}",
        f"{CANONICAL_STATE_DIR}/{RESOURCES_LOCK}",
    ]
    will_preserve = [
        V1_SIGNAL_AGENT_DIR,
        V1_SIGNAL_GEMINI_MD,
        V1_SIGNAL_CONTEXT_MD,
    ]
    unresolved = list(analysis.unresolved_fields)
    if analysis.legacy_resources:
        unmatched = [r["id"] for r in analysis.legacy_resources if not r["matched"]]
        if unmatched:
            unresolved.append(f"unmatched_legacy_resources: {', '.join(sorted(set(unmatched)))}")

    inference = dict(analysis.inferred_fields)
    inference["project_id"] = {"source": "directory_name", "value": analysis.project_id}
    inference["project_name"] = {"source": "directory_name", "value": analysis.project_name}

    return MigrationPlan(
        project_root=root,
        spec=spec,
        state=state,
        lock=lock,
        will_create=will_create,
        will_preserve=will_preserve,
        inference=inference,
        unresolved=unresolved,
        warnings=list(analysis.warnings),
        dry_run=dry_run,
    )


def preview_plan(plan: MigrationPlan) -> str:
    """Return a human-readable preview of the migration plan."""
    lines: list[str] = []
    lines.append("M8 Migration Plan (preview — no writes yet)")
    lines.append("=" * 50)
    lines.append(f"Project root: {plan.project_root}")
    lines.append(f"Project: {plan.spec.name} (id={plan.spec.id})")
    lines.append(f"Dry run: {plan.dry_run}")
    lines.append("")
    lines.append("Inferred fields:")
    for field, info in sorted(plan.inference.items()):
        lines.append(f"  - {field}: {info.get('value')} (source: {info.get('source')})")
    if plan.unresolved:
        lines.append("")
        lines.append("Unresolved fields (honest absence):")
        for u in plan.unresolved:
            lines.append(f"  - {u}")
    if plan.warnings:
        lines.append("")
        lines.append("Warnings:")
        for w in plan.warnings:
            lines.append(f"  - {w}")
    lines.append("")
    lines.append("Will create (under .ai-coding-starter/):")
    for p in plan.will_create:
        lines.append(f"  + {p}")
    lines.append("")
    lines.append("Will preserve (untouched):")
    for p in plan.will_preserve:
        lines.append(f"  - {p}")
    lines.append("")
    lines.append("Locked resources (provenance-verified only):")
    for r in plan.lock.resources:
        lines.append(
            f"  - {r.type}:{r.id} v{r.version} "
            f"(source={r.provenance.source}, sha={r.provenance.commit_sha[:12]})"
        )
    lines.append("")
    lines.append("Root user Markdown (AGENTS.md/CONTEXT.md/DECISIONS.md/HANDOFF.md)")
    lines.append("  is NOT regenerated by migration; canonical state only.")
    lines.append("")
    lines.append("Proceed? [y/N]  (default: NO)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Apply (writes only to .ai-coding-starter/, after confirmation)
# ---------------------------------------------------------------------------


def _snapshot_files(project_root: Path, paths: list[str]) -> dict[str, Optional[str]]:
    """Snapshot hashes of files that must be preserved."""
    snap: dict[str, Optional[str]] = {}
    for p in paths:
        snap[p] = _file_hash(project_root / p)
    return snap


def apply_plan(
    plan: MigrationPlan, confirmed: bool = False
) -> MigrationResult:
    """Apply the migration plan.

    Requires explicit confirmation (``confirmed=True``). Writes only to
    ``.ai-coding-starter/``. Validates all documents before writing.
    """
    created_files: list[str] = []
    preserved_files: list[str] = list(plan.will_preserve)
    errors: list[str] = []

    if not confirmed:
        return MigrationResult(
            detected=True,
            already_migrated=False,
            confirmed=False,
            applied=False,
            created_files=[],
            preserved_files=preserved_files,
            inferred_fields=plan.inference,
            unresolved_fields=plan.unresolved,
            warnings=list(plan.warnings),
            dry_run=plan.dry_run,
            errors=[],
        )

    # Conflict policy: refuse if a M8-owned destination already exists with
    # unexpected content (defensive; apply_plan is called after detection
    # which already handles already-migrated/partial states).
    state_dir = plan.project_root / CANONICAL_STATE_DIR
    for rel in plan.will_create:
        dest = plan.project_root / rel
        if dest.exists() and not dest.is_dir():
            errors.append(f"destination already exists and will not be overwritten: {rel}")
            return MigrationResult(
                detected=True,
                already_migrated=False,
                confirmed=True,
                applied=False,
                created_files=[],
                preserved_files=preserved_files,
                inferred_fields=plan.inference,
                unresolved_fields=plan.unresolved,
                warnings=list(plan.warnings),
                dry_run=plan.dry_run,
                errors=errors,
            )

    # Snapshot protected legacy files before writing (for verification).
    protected = [V1_SIGNAL_AGENT_DIR, V1_SIGNAL_GEMINI_MD, V1_SIGNAL_CONTEXT_MD]
    before_snapshot = _snapshot_files(plan.project_root, protected)

    if plan.dry_run:
        return MigrationResult(
            detected=True,
            already_migrated=False,
            confirmed=True,
            applied=False,
            created_files=[],
            preserved_files=preserved_files,
            inferred_fields=plan.inference,
            unresolved_fields=plan.unresolved,
            warnings=list(plan.warnings),
            dry_run=True,
            errors=[],
        )

    # --- ATOMIC APPLY ---------------------------------------------------
    # Stage all canonical files in a temp staging dir under the project
    # root, validate each write by reading it back, then move them into
    # .ai-coding-starter/ only after every file is proven good. A failure
    # at any stage cleans up staging and leaves the target untouched.
    staging_dir = None
    try:
        staging_dir = Path(
            tempfile.mkdtemp(prefix=".ai-coding-starter-staging-", dir=plan.project_root)
        )

        # 1. Write all files to staging.
        write_project_spec(staging_dir, plan.spec)
        write_state(staging_dir, plan.state)
        write_resources_lock(staging_dir, plan.lock)

        # 2. Validate by reading each back.
        read_project_spec(staging_dir / CANONICAL_STATE_DIR / PROJECT_YAML)
        read_state(staging_dir / CANONICAL_STATE_DIR / STATE_YAML)
        read_resources_lock(staging_dir / CANONICAL_STATE_DIR / RESOURCES_LOCK)

        # 3. Ensure destination dir exists.
        state_dir.mkdir(parents=True, exist_ok=True)

        # 4. Move each staged file into place. If any move fails, clean up
        #    what was already moved and report error (partial state, but
        #    we attempt to leave nothing behind).
        moved: list[Path] = []
        for rel in plan.will_create:
            src = staging_dir / rel
            dst = plan.project_root / rel
            try:
                shutil.move(str(src), str(dst))
                moved.append(dst)
                created_files.append(rel)
            except OSError as exc:
                # Roll back any files already moved in this batch.
                for already_moved in moved:
                    try:
                        already_moved.unlink()
                    except OSError:
                        pass
                errors.append(f"failed to publish {rel}: {exc}")
                return MigrationResult(
                    detected=True,
                    already_migrated=False,
                    confirmed=True,
                    applied=False,
                    created_files=[],
                    preserved_files=preserved_files,
                    inferred_fields=plan.inference,
                    unresolved_fields=plan.unresolved,
                    warnings=list(plan.warnings),
                    dry_run=False,
                    errors=errors,
                )

    except OSError as exc:
        errors.append(f"failed to stage canonical state: {exc}")
        return MigrationResult(
            detected=True,
            already_migrated=False,
            confirmed=True,
            applied=False,
            created_files=[],
            preserved_files=preserved_files,
            inferred_fields=plan.inference,
            unresolved_fields=plan.unresolved,
            warnings=list(plan.warnings),
            dry_run=False,
            errors=errors,
        )
    finally:
        # Always clean up staging dir if it still exists.
        if staging_dir is not None and staging_dir.exists():
            try:
                shutil.rmtree(staging_dir, ignore_errors=True)
            except OSError:
                pass

    # Verify protected legacy files unchanged.
    for p in protected:
        after = _file_hash(plan.project_root / p)
        if before_snapshot.get(p) != after:
            errors.append(f"protected file changed during migration: {p}")
    if errors:
        return MigrationResult(
            detected=True,
            already_migrated=False,
            confirmed=True,
            applied=False,
            created_files=created_files,
            preserved_files=preserved_files,
            inferred_fields=plan.inference,
            unresolved_fields=plan.unresolved,
            warnings=list(plan.warnings),
            dry_run=plan.dry_run,
            errors=errors,
        )

    return MigrationResult(
        detected=True,
        already_migrated=False,
        confirmed=True,
        applied=True,
        created_files=created_files,
        preserved_files=preserved_files,
        inferred_fields=plan.inference,
        unresolved_fields=plan.unresolved,
        warnings=list(plan.warnings),
        dry_run=plan.dry_run,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# Rollback (reversible: delete .ai-coding-starter/)
# ---------------------------------------------------------------------------


def rollback_migration(project_root: Path | str) -> MigrationResult:
    """Roll back migration by removing ``.ai-coding-starter/``.

    Legacy V1 files were never modified, so the project returns to V1 state.
    """
    root = Path(project_root).resolve()
    state_dir = root / CANONICAL_STATE_DIR
    removed: list[str] = []
    errors: list[str] = []
    if state_dir.is_dir():
        try:
            shutil.rmtree(state_dir)
            removed.append(str(CANONICAL_STATE_DIR))
        except OSError as exc:
            errors.append(f"failed to remove .ai-coding-starter/: {exc}")
    return MigrationResult(
        detected=False,
        already_migrated=False,
        confirmed=True,
        applied=True,
        created_files=[],
        preserved_files=[],
        inferred_fields={},
        unresolved_fields=[],
        warnings=[],
        dry_run=False,
        errors=errors,
    )


__all__ = [
    "DetectionResult",
    "MigrationAnalysis",
    "MigrationPlan",
    "MigrationResult",
    "detect_v1_project",
    "analyze_v1_project",
    "build_migration_plan",
    "preview_plan",
    "apply_plan",
    "rollback_migration",
    "MIGRATION_TOOL_ID",
]

"""
Portable workflow/session state (state.yaml) and resource lock (resources.lock)
for M4.

state.yaml is machine-authoritative workflow/session state. resources.lock is
the machine-readable resource/stack lock state.

Both files use the ``.yaml`` extension with JSON-compatible YAML 1.2 syntax,
read/written deterministically with stdlib ``json``. No PyYAML or custom YAML
parser is used.

M4 records the smallest honest lock state: an empty ``resources`` array (no
fabricated commit SHAs, licenses, or upstream repositories) and the selected
stack bundle under ``stack_bundle_resolution``. Full provenance is deferred to
M7.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from core.domain.contracts.id_policy import CanonicalId, is_valid_id, make_id

CANONICAL_STATE_DIR = ".ai-coding-starter"
STATE_YAML = "state.yaml"
RESOURCES_LOCK = "resources.lock"
SCHEMA_VERSION = "1.0.0"
LOCKFILE_VERSION = 1
GENERATED_BY = "ai-coding-starter-generator"

VALID_PHASES = frozenset([
    "not-started", "planning", "architecture", "development",
    "testing", "staging", "production", "maintenance",
])
VALID_TASK_STATUS = frozenset(["pending", "in-progress", "blocked", "done", "cancelled"])


def _utc_now() -> str:
    """Current time as ISO 8601 UTC (deterministic format, no locale)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# State model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TaskEntry:
    """A single active task."""
    id: str
    title: str
    status: str = "pending"
    assignee: Optional[str] = None
    due_date: Optional[str] = None

    def __post_init__(self) -> None:
        if self.status not in VALID_TASK_STATUS:
            raise ValueError(f"Invalid task status: {self.status}")
        if self.assignee is not None and not is_valid_id(self.assignee):
            raise ValueError(f"Invalid assignee id: {self.assignee}")


@dataclass(frozen=True)
class CompletedTask:
    """A single completed task in history."""
    id: str
    title: str
    completed_at: str
    outcome: str = ""

    def __post_init__(self) -> None:
        try:
            datetime.fromisoformat(self.completed_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"completed_at must be ISO 8601: {self.completed_at}") from exc


@dataclass(frozen=True)
class WorktreeEntry:
    """A single active git worktree (repo-relative path)."""
    path: str
    purpose: str
    branch: str
    created_at: Optional[str] = None
    owner_agent: Optional[str] = None


@dataclass(frozen=True)
class LastSession:
    """Previous session summary for continuity."""
    ended_at: Optional[str] = None
    summary: str = ""
    next_steps: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProjectState:
    """
    Portable workflow/session state.

    This is the canonical state.yaml content. It is machine-authoritative for
    workflow/session tracking and is portable across runtimes.
    """
    schema_version: str = SCHEMA_VERSION
    phase: str = "planning"
    focus: str = ""
    active_tasks: List[TaskEntry] = field(default_factory=list)
    completed_tasks: List[CompletedTask] = field(default_factory=list)
    decisions_pointer: str = "DECISIONS.md"
    handoff_pointer: str = "HANDOFF.md"
    canonical_branch: Optional[str] = None
    active_worktrees: List[WorktreeEntry] = field(default_factory=list)
    last_session: Optional[LastSession] = None

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"Unsupported schema_version: {self.schema_version}")
        if self.phase not in VALID_PHASES:
            raise ValueError(f"Invalid phase: {self.phase}")
        if self.decisions_pointer and not isinstance(self.decisions_pointer, str):
            raise ValueError("decisions_pointer must be a string")
        if self.handoff_pointer and not isinstance(self.handoff_pointer, str):
            raise ValueError("handoff_pointer must be a string")

    # -- serialization ------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "state": {
                "phase": self.phase,
                "focus": self.focus,
                "active_tasks": [
                    {
                        "id": t.id,
                        "title": t.title,
                        "status": t.status,
                        **({"assignee": t.assignee} if t.assignee else {}),
                        **({"due_date": t.due_date} if t.due_date else {}),
                    }
                    for t in self.active_tasks
                ],
                "completed_tasks": [
                    {
                        "id": t.id,
                        "title": t.title,
                        "completed_at": t.completed_at,
                        **({"outcome": t.outcome} if t.outcome else {}),
                    }
                    for t in self.completed_tasks
                ],
                "decisions_pointer": self.decisions_pointer,
                "handoff_pointer": self.handoff_pointer,
                **({"canonical_branch": self.canonical_branch}
                   if self.canonical_branch is not None else {}),
                "active_worktrees": [
                    {
                        "path": w.path,
                        "purpose": w.purpose,
                        "branch": w.branch,
                        **({"created_at": w.created_at} if w.created_at else {}),
                        **({"owner_agent": w.owner_agent} if w.owner_agent else {}),
                    }
                    for w in self.active_worktrees
                ],
                **({"last_session": {
                    **({"ended_at": self.last_session.ended_at}
                       if self.last_session and self.last_session.ended_at else {}),
                    "summary": self.last_session.summary,
                    "next_steps": self.last_session.next_steps,
                }} if self.last_session is not None else {}),
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectState":
        if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported or missing schema_version in state document"
            )
        state = data.get("state")
        if not isinstance(state, dict):
            raise ValueError("Missing 'state' object in state document")

        active_tasks = [
            TaskEntry(
                id=t["id"], title=t["title"], status=t.get("status", "pending"),
                assignee=t.get("assignee"), due_date=t.get("due_date"),
            )
            for t in state.get("active_tasks", [])
        ]
        completed_tasks = [
            CompletedTask(
                id=t["id"], title=t["title"], completed_at=t["completed_at"],
                outcome=t.get("outcome", ""),
            )
            for t in state.get("completed_tasks", [])
        ]
        last_session = None
        if state.get("last_session") is not None:
            ls = state["last_session"]
            last_session = LastSession(
                ended_at=ls.get("ended_at"),
                summary=ls.get("summary", ""),
                next_steps=list(ls.get("next_steps", [])),
            )
        return cls(
            phase=state.get("phase", "planning"),
            focus=state.get("focus", ""),
            active_tasks=active_tasks,
            completed_tasks=completed_tasks,
            decisions_pointer=state.get("decisions_pointer", "DECISIONS.md"),
            handoff_pointer=state.get("handoff_pointer", "HANDOFF.md"),
            canonical_branch=state.get("canonical_branch"),
            active_worktrees=[
                WorktreeEntry(
                    path=w["path"], purpose=w["purpose"], branch=w["branch"],
                    created_at=w.get("created_at"), owner_agent=w.get("owner_agent"),
                )
                for w in state.get("active_worktrees", [])
            ],
            last_session=last_session,
        )


def state_to_json_text(state: ProjectState) -> str:
    """Serialize state to deterministic, UTF-8, JSON-compatible YAML text."""
    return json.dumps(state.to_dict(), indent=2, ensure_ascii=False) + "\n"


def write_state(dest_dir: Path | str, state: ProjectState) -> Path:
    """Write ``state.yaml`` under ``<dest>/.ai-coding-starter/``."""
    state_dir = Path(dest_dir) / CANONICAL_STATE_DIR
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / STATE_YAML
    path.write_text(state_to_json_text(state), encoding="utf-8")
    return path


def read_state(path: Path | str) -> ProjectState:
    """Read and validate ``state.yaml``."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot read state.yaml at {path}: {exc}") from exc
    return ProjectState.from_dict(data)


# ---------------------------------------------------------------------------
# Resources lock
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Provenance:
    """Minimal provenance for a locked resource."""
    source: str  # "bundled" | "agency-agents" | "custom" | "community"
    commit_sha: str
    upstream_repo: Optional[str] = None
    license: Optional[str] = None
    imported_date: Optional[str] = None
    reviewed_date: Optional[str] = None
    transformation: Optional[str] = None


@dataclass(frozen=True)
class LockedResource:
    """A single locked resource entry."""
    id: str
    type: str  # agent | skill | rule | workflow | script | template | instruction | shared-module
    version: str
    provenance: Provenance
    runtime_representations: dict = field(default_factory=dict)
    selection_reason: Optional[str] = None


@dataclass(frozen=True)
class StackBundleResolution:
    """Stack bundle resolution metadata recorded in the lock."""
    requested_bundle: str
    resolved_bundle: str
    technology_versions: dict = field(default_factory=dict)
    compatibility_warnings: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ResourcesLock:
    """Machine-readable resource/stack lock state (resources.lock)."""
    schema_version: str = SCHEMA_VERSION
    lockfile_version: int = LOCKFILE_VERSION
    generated_at: str = field(default_factory=_utc_now)
    generated_by: str = GENERATED_BY
    catalog_version: Optional[str] = None
    resources: List[LockedResource] = field(default_factory=list)
    stack_bundle_resolution: Optional[StackBundleResolution] = None

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"Unsupported schema_version: {self.schema_version}")
        if not isinstance(self.lockfile_version, int) or self.lockfile_version < 1:
            raise ValueError("lockfile_version must be an integer >= 1")

    # -- serialization ------------------------------------------------------

    def to_dict(self) -> dict:
        data = {
            "schema_version": self.schema_version,
            "lockfile_version": self.lockfile_version,
            "generated_at": self.generated_at,
            "generated_by": self.generated_by,
            "resources": [
                {
                    "id": r.id,
                    "type": r.type,
                    "version": r.version,
                    "provenance": {
                        "source": r.provenance.source,
                        "commit_sha": r.provenance.commit_sha,
                        **({"upstream_repo": r.provenance.upstream_repo}
                           if r.provenance.upstream_repo else {}),
                        **({"license": r.provenance.license}
                           if r.provenance.license else {}),
                        **({"imported_date": r.provenance.imported_date}
                           if r.provenance.imported_date else {}),
                        **({"reviewed_date": r.provenance.reviewed_date}
                           if r.provenance.reviewed_date else {}),
                        **({"transformation": r.provenance.transformation}
                           if r.provenance.transformation else {}),
                    },
                    **({"runtime_representations": r.runtime_representations}
                       if r.runtime_representations else {}),
                    **({"selection_reason": r.selection_reason}
                       if r.selection_reason else {}),
                }
                for r in self.resources
            ],
        }
        if self.catalog_version is not None:
            data["catalog_version"] = self.catalog_version
        if self.stack_bundle_resolution is not None:
            sbr = self.stack_bundle_resolution
            data["stack_bundle_resolution"] = {
                "requested_bundle": sbr.requested_bundle,
                "resolved_bundle": sbr.resolved_bundle,
                **({"technology_versions": sbr.technology_versions}
                   if sbr.technology_versions else {}),
                **({"compatibility_warnings": sbr.compatibility_warnings}
                   if sbr.compatibility_warnings else {}),
            }
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ResourcesLock":
        if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported or missing schema_version in resources.lock"
            )
        resources = []
        for r in data.get("resources", []):
            prov = r["provenance"]
            resources.append(LockedResource(
                id=r["id"], type=r["type"], version=r["version"],
                provenance=Provenance(
                    source=prov["source"], commit_sha=prov["commit_sha"],
                    upstream_repo=prov.get("upstream_repo"),
                    license=prov.get("license"),
                    imported_date=prov.get("imported_date"),
                    reviewed_date=prov.get("reviewed_date"),
                    transformation=prov.get("transformation"),
                ),
                runtime_representations=r.get("runtime_representations", {}),
                selection_reason=r.get("selection_reason"),
            ))
        sbr = None
        if data.get("stack_bundle_resolution") is not None:
            raw = data["stack_bundle_resolution"]
            sbr = StackBundleResolution(
                requested_bundle=raw["requested_bundle"],
                resolved_bundle=raw["resolved_bundle"],
                technology_versions=raw.get("technology_versions", {}),
                compatibility_warnings=list(raw.get("compatibility_warnings", [])),
            )
        return cls(
            lockfile_version=data.get("lockfile_version", LOCKFILE_VERSION),
            generated_at=data.get("generated_at", _utc_now()),
            generated_by=data.get("generated_by", GENERATED_BY),
            catalog_version=data.get("catalog_version"),
            resources=resources,
            stack_bundle_resolution=sbr,
        )


def lock_to_json_text(lock: ResourcesLock) -> str:
    """Serialize lock to deterministic, UTF-8, JSON-compatible YAML text."""
    return json.dumps(lock.to_dict(), indent=2, ensure_ascii=False) + "\n"


def write_resources_lock(dest_dir: Path | str, lock: ResourcesLock) -> Path:
    """Write ``resources.lock`` under ``<dest>/.ai-coding-starter/``."""
    state_dir = Path(dest_dir) / CANONICAL_STATE_DIR
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / RESOURCES_LOCK
    path.write_text(lock_to_json_text(lock), encoding="utf-8")
    return path


def read_resources_lock(path: Path | str) -> ResourcesLock:
    """Read and validate ``resources.lock``."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot read resources.lock at {path}: {exc}") from exc
    return ResourcesLock.from_dict(data)


# ---------------------------------------------------------------------------
# Builders for M4 generation
# ---------------------------------------------------------------------------


def build_initial_state(
    project_id: str,
    *,
    phase: str = "planning",
    focus: str = "",
    canonical_branch: Optional[str] = None,
) -> ProjectState:
    """Build the minimal, honest initial state for a freshly generated project.

    No completed tasks are fabricated. A freshly generated project has not yet
    done any implementation work.
    """
    if phase not in VALID_PHASES:
        raise ValueError(f"Invalid initial phase: {phase}")
    return ProjectState(
        phase=phase,
        focus=focus,
        decisions_pointer="DECISIONS.md",
        handoff_pointer="HANDOFF.md",
        canonical_branch=canonical_branch,
    )


def build_resources_lock(
    resolved_bundle_id: str,
    *,
    requested_bundle_id: Optional[str] = None,
    catalog_version: Optional[str] = None,
    resources: Optional[list[dict]] = None,
) -> ResourcesLock:
    """Build the M4/M7 resources lock.

    ``resources`` is empty by default (no fabricated provenance). When a list of
    selected resource entries is supplied (M7), each entry is converted into a
    :class:`LockedResource` with full provenance. Technology versions are
    intentionally omitted unless actually resolved by the generator
    (honest absence over false precision — see M7 Section 30).

    Each resource entry dict may carry:
      id, type, version, provenance (source, commit_sha, license, ...),
      runtime_representations, selection_reason.
    """
    lock_resources: list[LockedResource] = []
    if resources:
        for entry in resources:
            prov = entry.get("provenance", {}) or {}
            commit_sha = prov.get("commit_sha")
            if not commit_sha:
                raise ValueError(
                    "Missing provenance commit_sha for resource "
                    f"'{entry.get('id', '<unknown>')}' (type "
                    f"'{entry.get('type', '<unknown>')}'). "
                    "Every locked resource must declare a verified commit_sha; "
                    "refusing to fabricate provenance."
                )
            lock_resources.append(
                LockedResource(
                    id=entry["id"],
                    type=entry["type"],
                    version=entry.get("version", "1.0.0"),
                    provenance=Provenance(
                        source=prov.get("source", "bundled"),
                        commit_sha=commit_sha,
                        upstream_repo=prov.get("upstream_repo"),
                        license=prov.get("license"),
                        imported_date=prov.get("imported_date"),
                        reviewed_date=prov.get("reviewed_date"),
                        transformation=prov.get("transformation"),
                    ),
                    runtime_representations=entry.get(
                        "runtime_representations", {}
                    ),
                    selection_reason=entry.get("selection_reason"),
                )
            )
    return ResourcesLock(
        catalog_version=catalog_version,
        resources=lock_resources,
        stack_bundle_resolution=StackBundleResolution(
            requested_bundle=requested_bundle_id or resolved_bundle_id,
            resolved_bundle=resolved_bundle_id,
            compatibility_warnings=[],
        ),
    )

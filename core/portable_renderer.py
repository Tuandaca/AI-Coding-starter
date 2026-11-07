"""
Derived Markdown renderer + portable AI workspace materialization for M4.

The portable AI workspace (``.ai-workspace/``) holds the human-readable
resources actually activated for the project. It is the portable,
runtime-neutral source of truth from which runtime adapters derive their
vendor-specific representations.

Direction is strictly one-way:

    canonical state + resource selection  ->  .ai-workspace/ + derived Markdown

Markdown and the portable workspace are never parsed back into canonical
state, and canonical state always wins on conflict.

No runtime-specific instructions (Codex/OpenCode/Antigravity/Claude/Cursor)
are emitted here; runtime adaptation belongs to the adapter layer.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from core.domain.contracts.project_state import ProjectSpec
from core.resource_resolver import ResourceSelection, ResourceSelectionResult
from core.state import ProjectState, ResourcesLock


# Canonical resource type -> directory name under .ai-workspace/.
WORKSPACE_SUBDIR = {
    "agent": "agents",
    "skill": "skills",
    "shared-module": "shared",
    "workflow": "workflows",
    "script": "scripts",
    "rule": "rules",
}

# Source file/suffix used to materialize each resource type from resources/.
RESOURCE_SOURCE_SUFFIX = {
    "agent": ".md",
    "skill": "/SKILL.md",
    "shared-module": "",      # copied as a directory tree
    "workflow": ".md",
    "script": ".py",
    "rule": ".md",
}


def _bullet_list(items, prefix="- ") -> str:
    if not items:
        return "None"
    return "\n".join(f"{prefix}{item}" for item in items)


def render_agents_md(
    spec: ProjectSpec,
    active_agents: Optional[list[ResourceSelection]] = None,
    active_skills: Optional[list[ResourceSelection]] = None,
) -> str:
    """Portable AGENTS.md derived from project.yaml (+ active resources)."""
    lines = [
        "# AGENTS.md",
        "",
        "> Portable, runtime-neutral project instructions derived from canonical state.",
        "> Canonical state: ``.ai-coding-starter/project.yaml``.",
        "> Markdown is derived; it never overrides canonical state.",
        "",
        f"## Project: {spec.name}",
        "",
        f"- **Project ID**: {spec.id}",
        f"- **Name**: {spec.name}",
        f"- **Description**: {spec.description or '(not set)'}",
        f"- **Created**: {spec.created_at}",
        f"- **Updated**: {spec.updated_at}",
    ]
    if spec.project_type:
        lines.append(f"- **Project Type**: {spec.project_type}")
    if spec.capabilities:
        lines.append(f"- **Capabilities**: {', '.join(str(c) for c in spec.capabilities)}")
    else:
        lines.append("- **Capabilities**: None")
    if spec.stack_bundle:
        lines.append(f"- **Stack Bundle**: {spec.stack_bundle}")
    else:
        lines.append("- **Stack Bundle**: None")
    lines += [
        "",
        "## Portable AI Workspace",
        "",
        "- Activated portable resources live under ``.ai-workspace/``:",
        "  - ``.ai-workspace/agents/``   active agents",
        "  - ``.ai-workspace/skills/``   active skills",
        "  - ``.ai-workspace/workflows/`` active workflows",
        "  - ``.ai-workspace/rules/``    active rules",
        "  - ``.ai-workspace/shared/``   shared modules",
        "  - ``.ai-workspace/scripts/``  active scripts",
        "- Runtime adapters derive vendor-specific files from this workspace.",
        "",
    ]
    if active_agents:
        lines += [
            "## Active Agents",
            "",
            _bullet_list(
                [
                    f"**{r.id}** — {r.description or r.name}"
                    f" (score {r.score})" if r.score else f"**{r.id}** — {r.description or r.name}"
                    for r in active_agents
                ]
            ),
            "",
        ]
    if active_skills:
        lines += [
            "## Active Skills",
            "",
            _bullet_list([f"**{r.id}**" for r in active_skills]),
            "",
        ]
    lines += [
        "## Authority",
        "",
        "- ``.ai-coding-starter/project.yaml`` is the machine-authoritative project config.",
        "- ``.ai-coding-starter/state.yaml`` is the machine-authoritative workflow/session state.",
        "- ``.ai-coding-starter/resources.lock`` is the machine-readable resource/stack lock.",
        "- This file (AGENTS.md) is a derived, readable projection; it cannot override canonical state.",
        "",
    ]
    return "\n".join(lines) + "\n"


def render_context_md(spec: ProjectSpec, state: ProjectState) -> str:
    """Portable CONTEXT.md derived from project.yaml + state.yaml."""
    lines = [
        "# 📋 PROJECT CONTEXT",
        "",
        f"> Project: {spec.name} ({spec.id})",
        "> Derived from canonical state (project.yaml + state.yaml).",
        "> Not an independent machine-authoritative state store.",
        "",
        "## Project Identity",
        "",
        f"- **ID**: {spec.id}",
        f"- **Name**: {spec.name}",
        f"- **Description**: {spec.description or '(not set)'}",
        f"- **Project Type**: {spec.project_type or '(not set)'}",
        f"- **Capabilities**: {', '.join(str(c) for c in spec.capabilities) if spec.capabilities else 'None'}",
        f"- **Stack Bundle**: {spec.stack_bundle or '(not set)'}",
        f"- **Created**: {spec.created_at}",
        f"- **Updated**: {spec.updated_at}",
        "",
        "## Workflow State",
        "",
        f"- **Phase**: {state.phase}",
        f"- **Focus**: {state.focus or '(not set)'}",
        f"- **Decisions Pointer**: {state.decisions_pointer}",
        f"- **Handoff Pointer**: {state.handoff_pointer}",
        f"- **Canonical Branch**: {state.canonical_branch or 'not initialized / unavailable'}",
        f"- **Active Worktrees**: {len(state.active_worktrees)}",
        "",
        "## Active Tasks",
        "",
        _bullet_list(
            [f"**{t.id}** — {t.title} [{t.status}]" for t in state.active_tasks],
        ),
        "",
        "## Completed Tasks",
        "",
        _bullet_list(
            [f"**{t.id}** — {t.title} ({t.completed_at})" for t in state.completed_tasks],
        ),
        "",
    ]
    return "\n".join(lines) + "\n"


def render_decisions_md() -> str:
    """Append-only architecture decision history (initial content)."""
    return (
        "# Architecture Decisions\n"
        "\n"
        "No decisions recorded yet.\n"
        "\n"
        "This file is append-only. It must not duplicate project configuration "
        "as independent state; canonical configuration lives in "
        "``.ai-coding-starter/project.yaml``.\n"
    )


def render_handoff_md(
    spec: ProjectSpec,
    state: ProjectState,
    *,
    last_session_summary: Optional[str] = None,
    last_session_next_steps: Optional[list[str]] = None,
) -> str:
    """Portable HANDOFF.md: concise continuation interface."""
    next_steps = list(last_session_next_steps or [])
    if not next_steps:
        next_steps = ["Open this project in your coding runtime", "Read .ai-coding-starter/project.yaml", "Continue from state.yaml phase"]
    lines = [
        "# Handoff",
        "",
        f"> Continuation interface for {spec.name} ({spec.id}).",
        "> Regeneratable from canonical state plus append-only human context.",
        "",
        "## Project",
        f"- **Name**: {spec.name}",
        f"- **ID**: {spec.id}",
        f"- **Project Type**: {spec.project_type or 'not set'}",
        f"- **Selected Stack**: {spec.stack_bundle or 'not set'}",
        f"- **Capabilities**: {', '.join(str(c) for c in spec.capabilities) if spec.capabilities else 'None'}",
        "",
        "## Current Phase",
        f"- **Phase**: {state.phase}",
        f"- **Focus**: {state.focus or 'not set'}",
        "",
        "## Canonical Branch",
        f"- {state.canonical_branch or 'not initialized / unavailable'}",
        "",
        "## Active Worktrees",
        f"- {len(state.active_worktrees)} worktree(s)",
        "",
        "## Last Session",
        f"- **Summary**: {last_session_summary or 'None / Not recorded'}",
        "",
        "## Next Steps",
        "",
        _bullet_list(next_steps),
        "",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Portable AI workspace materialization
# ---------------------------------------------------------------------------

def _copy_file(src: Path, dst: Path) -> int:
    """Copy a single file, creating parent dirs. Returns bytes copied."""
    if not src.is_file():
        return 0
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return src.stat().st_size


def _copy_tree(src: Path, dst: Path) -> int:
    """Copy a directory tree. Returns bytes copied."""
    if not src.is_dir():
        return 0
    total = 0
    for f in sorted(src.rglob("*")):
        if f.is_file():
            rel = f.relative_to(src)
            out = dst / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, out)
            total += f.stat().st_size
    return total


def render_portable_workspace(
    dest_dir: Path | str,
    resource_selection: ResourceSelectionResult,
    resources_root: Path | str,
) -> list[Path]:
    """Materialize every active portable resource into ``.ai-workspace/``.

    Invariant (§10): every locked active resource that has a filesystem
    representation gets a corresponding file under ``.ai-workspace/``.
    Resource types with no filesystem representation are skipped.

    Returns the list of written paths.
    """
    dest = Path(dest_dir)
    workspace = dest / ".ai-workspace"
    resources_root = Path(resources_root)
    written: list[Path] = []

    type_to_source_dir = {
        "agent": "agents",
        "skill": "skills",
        "shared-module": "shared",
        "workflow": "workflows",
        "script": "scripts",
        "rule": "rules",
    }

    for res in resource_selection.resources:
        rtype = res.type
        rid = res.id
        source_dir_name = type_to_source_dir.get(rtype)
        if source_dir_name is None:
            # No filesystem representation for this type; skip.
            continue

        suffix = RESOURCE_SOURCE_SUFFIX.get(rtype, "")
        src_dir = resources_root / source_dir_name

        if rtype == "shared-module":
            # Copy the whole shared module directory tree.
            src = src_dir / rid
            dst = workspace / WORKSPACE_SUBDIR[rtype] / rid
            bytes_copied = _copy_tree(src, dst)
            if bytes_copied > 0:
                written.append(dst)
            continue

        if rtype == "skill":
            src = src_dir / rid / "SKILL.md"
            dst = workspace / WORKSPACE_SUBDIR[rtype] / rid / "SKILL.md"
        else:
            src = src_dir / f"{rid}{suffix}"
            dst = workspace / WORKSPACE_SUBDIR[rtype] / f"{rid}{suffix}"

        bytes_copied = _copy_file(src, dst)
        if bytes_copied > 0:
            written.append(dst)
        elif rtype == "agent":
            # Agency agents have no bundled source file; materialize them from
            # their registry metadata so the portable workspace always contains
            # the actual active agent content (no phantom resources, §10).
            generated = _generate_agent_md(res)
            if generated:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(generated, encoding="utf-8")
                written.append(dst)

    return written


def _generate_agent_md(res: ResourceSelection) -> Optional[str]:
    """Generate a portable agent markdown from a selection's metadata."""
    lines = [
        "---",
        f"name: {res.id}",
        f"description: {res.description or res.id}",
    ]
    if res.division:
        lines.append(f"division: {res.division}")
    if res.score:
        lines.append(f"score: {res.score}")
    lines += [
        "---",
        "",
        f"# {res.name or res.id}",
        "",
        f"> Portable agent activated for the project.",
        f"> Type: agent | ID: {res.id}",
    ]
    if res.selection_reason:
        lines += ["", f"Selection reason: {res.selection_reason}", ""]
    if res.description:
        lines += ["", res.description, ""]
    return "\n".join(lines) + "\n"


def render_all(
    dest_dir: Path | str,
    spec: ProjectSpec,
    state: ProjectState,
    *,
    last_session_summary: Optional[str] = None,
    last_session_next_steps: Optional[list[str]] = None,
    resources: Optional[ResourceSelectionResult] = None,
) -> list[Path]:
    """Render all derived Markdown files into ``dest_dir`` (project root).

    Derived files live at the project root, while canonical state lives in
    ``.ai-coding-starter/``. When ``resources`` is provided, AGENTS.md lists
    the active agents and skills.
    """
    dest = Path(dest_dir)
    active_agents = resources.agents if resources else None
    active_skills = [r for r in resources.resources if r.type == "skill"] if resources else None
    files = {
        "AGENTS.md": render_agents_md(spec, active_agents=active_agents, active_skills=active_skills),
        "CONTEXT.md": render_context_md(spec, state),
        "DECISIONS.md": render_decisions_md(),
        "HANDOFF.md": render_handoff_md(
            spec, state,
            last_session_summary=last_session_summary,
            last_session_next_steps=last_session_next_steps,
        ),
    }
    written: list[Path] = []
    for name, content in files.items():
        path = dest / name
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written

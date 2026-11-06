"""
Derived Markdown renderer for M4 portable state.

These renderers produce human-readable project interfaces (AGENTS.md,
CONTEXT.md, DECISIONS.md, HANDOFF.md) from canonical state only. The direction
is strictly:

    canonical YAML/lock  ->  derived Markdown

Markdown is never parsed back into canonical state, and canonical state always
wins on conflict.

No runtime-specific instructions (Codex/OpenCode/Antigravity/Claude/Cursor)
are emitted here; runtime adaptation belongs to M5.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from core.domain.contracts.project_state import ProjectSpec
from core.state import ProjectState, ResourcesLock


def _bullet_list(items, prefix="- ") -> str:
    if not items:
        return "None"
    return "\n".join(f"{prefix}{item}" for item in items)


def render_agents_md(spec: ProjectSpec) -> str:
    """Portable AGENTS.md derived from project.yaml."""
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


def render_all(
    dest_dir: Path | str,
    spec: ProjectSpec,
    state: ProjectState,
    *,
    last_session_summary: Optional[str] = None,
    last_session_next_steps: Optional[list[str]] = None,
) -> list[Path]:
    """Render all derived Markdown files into ``dest_dir`` (project root).

    Returns the list of written paths. Derived files live at the project root,
    while canonical state lives in ``.ai-coding-starter/``.
    """
    dest = Path(dest_dir)
    files = {
        "AGENTS.md": render_agents_md(spec),
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

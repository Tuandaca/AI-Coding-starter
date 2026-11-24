"""
Agent Manager Bridge — spawn specialist agents from project spec.

Integrates with Codex Agent Manager (origin.cursor.com) to launch
bounded specialist sessions based on team_pack + project context.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from core.domain.contracts.project_state import ProjectSpec
from core.spec import read_project_spec
from core.agency_specialists import (
    SpecialistAgent as Specialist,
    get_all_specialists,
    get_packs_for_project_type,
    get_specialists_for_pack,
    get_core_team,
)


@dataclass
class AgentSession:
    """Represents a launched Agent Manager session."""
    specialist_id: str
    session_id: str
    task: str
    status: str = "running"
    worktree: Optional[str] = None
    result: Optional[str] = None


@dataclass
class TeamDeployment:
    """Result of deploying a team pack."""
    project_id: str
    project_type: str
    team_pack: str
    core_agents: list[AgentSession] = field(default_factory=list)
    specialist_agents: list[AgentSession] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class AgentManagerBridge:
    """Bridge to Codex Agent Manager for spawning specialist agents."""

    def __init__(self, project_root: Path | str):
        self.project_root = Path(project_root)
        self.ai_coding_dir = self.project_root / ".ai-coding-starter"
        self.spec = read_project_spec(self.ai_coding_dir / "project.yaml")
        self.specialists = get_all_specialists()

    def get_core_team(self) -> list[Specialist]:
        """Get always-active core team agents."""
        return get_core_team(self.specialists)

    def get_specialists_for_current_pack(self) -> list[Specialist]:
        """Get as-needed specialists for the project's team pack."""
        if not self.spec.team_pack:
            return []
        return get_specialists_for_pack(self.spec.team_pack, self.specialists)

    def get_available_packs(self) -> list[str]:
        """Get team packs available for this project type."""
        if not self.spec.project_type:
            return []
        return get_packs_for_project_type(self.spec.project_type)

    def build_agent_prompt(self, specialist: Specialist, task: str, context: dict) -> str:
        """Build prompt for a specialist agent."""
        lines = [
            f"# Specialist: {specialist.name} ({specialist.id})",
            f"# Division: {specialist.division}",
            f"# Activation: {specialist.activation}",
            "",
            f"## Project Context",
            f"- Project: {self.spec.name} ({self.spec.id})",
            f"- Type: {self.spec.project_type}",
            f"- Stack: {self.spec.stack_bundle}",
            f"- Team Pack: {self.spec.team_pack}",
            f"- Capabilities: {', '.join(self.spec.capabilities) if self.spec.capabilities else 'None'}",
            "",
            f"## Your Role",
            specialist.description or specialist.system_prompt or "Specialist agent for this project.",
            "",
            f"## Task",
            task,
            "",
            f"## Additional Context",
            json.dumps(context, indent=2, ensure_ascii=False),
            "",
            "## Instructions",
            "- Work within the project directory",
            "- Read .ai-coding-starter/project.yaml for canonical state",
            "- Read .ai-workspace/ for activated resources",
            "- Write outputs to appropriate locations",
            "- Report completion with summary",
        ]
        return "\n".join(lines)

    def launch_specialist(
        self,
        specialist: Specialist,
        task: str,
        context: Optional[dict] = None,
        worktree: bool = True,
    ) -> AgentSession:
        """Launch a single specialist agent via Agent Manager."""
        prompt = self.build_agent_prompt(specialist, task, context or {})

        # Write prompt to temp file for Agent Manager
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(prompt)
            prompt_file = f.name

        try:
            # Build Agent Manager command
            cmd = [
                "origin", "agent", "create",
                "--prompt-file", prompt_file,
                "--model", "gpt-4o",  # Default; could be configurable
            ]

            if worktree:
                cmd.extend(["--worktree", f"{self.spec.id}-{specialist.id}"])

            # Add project context as environment
            env = {
                **subprocess.os.environ,
                "AI_CODING_PROJECT_ID": self.spec.id,
                "AI_CODING_PROJECT_ROOT": str(self.project_root),
                "AI_CODING_SPECIALIST": specialist.id,
                "AI_CODING_TEAM_PACK": self.spec.team_pack or "",
            }

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                cwd=self.project_root,
                timeout=30,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Agent Manager failed: {result.stderr}")

            # Parse session ID from output
            session_id = result.stdout.strip().split()[-1] if result.stdout else "unknown"

            return AgentSession(
                specialist_id=specialist.id,
                session_id=session_id,
                task=task,
                status="running",
            )

        finally:
            Path(prompt_file).unlink(missing_ok=True)

    def deploy_core_team(self, task: str = "Initialize project context") -> list[AgentSession]:
        """Launch core team agents (always active)."""
        sessions = []
        core_team = self.get_core_team()

        for specialist in core_team:
            try:
                session = self.launch_specialist(specialist, task, {"phase": "initialization"})
                sessions.append(session)
            except Exception as e:
                print(f"Failed to launch core agent {specialist.id}: {e}")

        return sessions

    def deploy_specialists(
        self,
        task: str,
        specialist_ids: Optional[list[str]] = None,
        context: Optional[dict] = None,
    ) -> list[AgentSession]:
        """Launch specialist agents (as-needed)."""
        sessions = []
        available = self.get_specialists_for_current_pack()

        if specialist_ids:
            available = [s for s in available if s.id in specialist_ids]

        for specialist in available:
            if specialist.activation == "always":
                continue  # Already in core team

            try:
                session = self.launch_specialist(specialist, task, context or {})
                sessions.append(session)
            except Exception as e:
                print(f"Failed to launch specialist {specialist.id}: {e}")

        return sessions

    def deploy_team_pack(self, task: str = "Execute team pack mission") -> TeamDeployment:
        """Deploy full team pack: core team + specialists."""
        deployment = TeamDeployment(
            project_id=self.spec.id,
            project_type=self.spec.project_type or "unknown",
            team_pack=self.spec.team_pack or "none",
        )

        # Deploy core team
        core_sessions = self.deploy_core_team("Initialize and maintain project context")
        deployment.core_agents = core_sessions

        # Deploy specialists
        specialist_sessions = self.deploy_specialists(task)
        deployment.specialist_agents = specialist_sessions

        return deployment

    def list_specialists(self) -> dict[str, list[dict]]:
        """List all specialists organized by activation type."""
        core = self.get_core_team()
        specialists = self.get_specialists_for_current_pack()

        return {
            "core_team": [
                {
                    "id": s.id,
                    "name": s.name,
                    "division": s.division,
                    "activation": s.activation,
                    "description": s.description,
                }
                for s in core
            ],
            "specialists": [
                {
                    "id": s.id,
                    "name": s.name,
                    "division": s.division,
                    "activation": s.activation,
                    "description": s.description,
                }
                for s in specialists if s.activation == "as-needed"
            ],
            "available_packs": self.get_available_packs(),
        }

    def check_agent_manager_available(self) -> bool:
        """Check if Agent Manager CLI is available."""
        try:
            result = subprocess.run(
                ["origin", "--version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False


def create_bridge(project_root: Path | str) -> AgentManagerBridge:
    """Factory function to create bridge instance."""
    return AgentManagerBridge(project_root)
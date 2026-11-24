"""
Runtime Adapters — derive vendor-specific config from portable workspace.

Direction: canonical state (.ai-coding-starter/project.yaml) + portable workspace (.ai-workspace/)
         → vendor-specific files (.codex/, .opencode/, .claude/, .cursor/)

Each adapter is stateless and idempotent; re-running produces same output.
"""

from __future__ import annotations

import json
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from core.domain.contracts.project_state import ProjectSpec
from core.domain.contracts.id_policy import CanonicalId
from core.state import ProjectState, ResourcesLock
from core.spec import read_project_spec
from core.state import read_state, read_resources_lock
from core.resource_resolver import ResourceSelectionResult


def _to_serializable(obj: Any) -> Any:
    """Convert CanonicalId and other non-JSON-serializable types to JSON-compatible."""
    if isinstance(obj, CanonicalId):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_serializable(v) for v in obj]
    if hasattr(obj, 'to_dict'):
        return _to_serializable(obj.to_dict())
    return obj


class RuntimeAdapter(ABC):
    """Base class for runtime adapters."""

    def __init__(self, project_root: Path | str):
        self.project_root = Path(project_root)
        self.ai_coding_dir = self.project_root / ".ai-coding-starter"
        self.workspace_dir = self.project_root / ".ai-workspace"

    @property
    @abstractmethod
    def runtime_name(self) -> str:
        """Unique identifier for this runtime (e.g., 'codex', 'opencode')."""

    @property
    @abstractmethod
    def config_dir_name(self) -> str:
        """Directory name under project root (e.g., '.codex', '.opencode')."""

    def read_canonical_state(self) -> tuple[ProjectSpec, ProjectState, ResourcesLock]:
        """Load canonical state files."""
        spec = read_project_spec(self.ai_coding_dir / "project.yaml")
        state = read_state(self.ai_coding_dir / "state.yaml")
        resources_lock = read_resources_lock(self.ai_coding_dir / "resources.lock")
        return spec, state, resources_lock

    def read_portable_workspace(self) -> dict[str, list[Path]]:
        """Scan .ai-workspace/ for activated resources by type."""
        result = {}
        if not self.workspace_dir.exists():
            return result
        for type_dir in self.workspace_dir.iterdir():
            if type_dir.is_dir():
                files = list(type_dir.rglob("*"))
                result[type_dir.name] = [f for f in files if f.is_file()]
        return result

    @abstractmethod
    def generate_config(
        self,
        spec: ProjectSpec,
        state: ProjectState,
        resources_lock: ResourcesLock,
        workspace_resources: dict[str, list[Path]],
    ) -> dict[Path, str]:
        """Generate vendor-specific config files. Returns {path: content}."""

    def apply(self, force: bool = False) -> list[Path]:
        """Generate and write all config files. Returns list of written paths."""
        spec, state, resources_lock = self.read_canonical_state()
        workspace_resources = self.read_portable_workspace()
        config_files = self.generate_config(spec, state, resources_lock, workspace_resources)

        config_dir = self.project_root / self.config_dir_name
        config_dir.mkdir(parents=True, exist_ok=True)

        written = []
        for rel_path, content in config_files.items():
            abs_path = config_dir / rel_path
            if abs_path.exists() and not force:
                continue
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text(content, encoding="utf-8")
            written.append(abs_path)
        return written

    def clean(self) -> None:
        """Remove generated config directory."""
        config_dir = self.project_root / self.config_dir_name
        if config_dir.exists():
            shutil.rmtree(config_dir)


class CodexAdapter(RuntimeAdapter):
    """Codex CLI adapter — generates .codex/ configuration."""

    @property
    def runtime_name(self) -> str:
        return "codex"

    @property
    def config_dir_name(self) -> str:
        return ".codex"

    def generate_config(
        self,
        spec: ProjectSpec,
        state: ProjectState,
        resources_lock: ResourcesLock,
        workspace_resources: dict[str, list[Path]],
    ) -> dict[Path, str]:
        files = {}

        # .codex/config.toml — main configuration
        files[Path("config.toml")] = self._generate_config_toml(spec, state, resources_lock)

        # .codex/agents/ — agent definitions from workspace
        agents = workspace_resources.get("agents", [])
        for agent_file in agents:
            rel = agent_file.relative_to(self.workspace_dir / "agents")
            content = agent_file.read_text(encoding="utf-8")
            files[Path("agents") / rel] = content

        # .codex/skills/ — skill definitions
        skills = workspace_resources.get("skills", [])
        for skill_file in skills:
            rel = skill_file.relative_to(self.workspace_dir / "skills")
            content = skill_file.read_text(encoding="utf-8")
            files[Path("skills") / rel] = content

        # .codex/workflows/ — workflow definitions
        workflows = workspace_resources.get("workflows", [])
        for wf_file in workflows:
            rel = wf_file.relative_to(self.workspace_dir / "workflows")
            content = wf_file.read_text(encoding="utf-8")
            files[Path("workflows") / rel] = content

        # .codex/rules/ — rule files
        rules = workspace_resources.get("rules", [])
        for rule_file in rules:
            rel = rule_file.relative_to(self.workspace_dir / "rules")
            content = rule_file.read_text(encoding="utf-8")
            files[Path("rules") / rel] = content

        # .codex/scripts/ — executable scripts
        scripts = workspace_resources.get("scripts", [])
        for script_file in scripts:
            rel = script_file.relative_to(self.workspace_dir / "scripts")
            content = script_file.read_text(encoding="utf-8")
            files[Path("scripts") / rel] = content

        # .codex/shared/ — shared modules (copied as-is)
        shared = workspace_resources.get("shared", [])
        for shared_file in shared:
            rel = shared_file.relative_to(self.workspace_dir / "shared")
            content = shared_file.read_bytes()
            # For binary files, we'd need different handling; skip for now
            if shared_file.suffix in {".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".sh"}:
                files[Path("shared") / rel] = content.decode("utf-8")

        # .codex/project.json — project metadata for Codex
        files[Path("project.json")] = json.dumps(_to_serializable({
            "name": spec.name,
            "id": spec.id,
            "project_type": spec.project_type,
            "stack_bundle": spec.stack_bundle,
            "team_pack": spec.team_pack,
            "specialists": spec.specialists,
            "capabilities": spec.capabilities,
            "runtime_preferences": spec.runtime_preferences,
        }), indent=2, ensure_ascii=False)

        return files

    def _generate_config_toml(
        self,
        spec: ProjectSpec,
        state: ProjectState,
        resources_lock: ResourcesLock,
    ) -> str:
        lines = [
            "# Codex Configuration",
            f"# Generated from {spec.name} ({spec.id})",
            f"# Project Type: {spec.project_type or 'unset'}",
            f"# Stack Bundle: {spec.stack_bundle or 'unset'}",
            f"# Team Pack: {spec.team_pack or 'unset'}",
            "",
            "[project]",
            f'name = "{spec.name}"',
            f'id = "{spec.id}"',
            f'project_type = "{spec.project_type or ""}"',
            f'stack_bundle = "{spec.stack_bundle or ""}"',
            f'team_pack = "{spec.team_pack or ""}"',
            f'specialists = {json.dumps(_to_serializable(spec.specialists))}',
            f'capabilities = {json.dumps(_to_serializable(spec.capabilities))}',
            "",
            "[runtime]",
            'mode = "local"',
            f'project_local_only = {str(getattr(spec.runtime_preferences, "project_local_only", True)).lower()}',
            "",
            "[agents]",
            "# Agents are loaded from .codex/agents/ (synced from .ai-workspace/agents/)",
            'auto_load = true',
            "",
            "[skills]",
            "# Skills are loaded from .codex/skills/ (synced from .ai-workspace/skills/)",
            'auto_load = true',
            "",
            "[workflows]",
            "# Workflows from .codex/workflows/",
            'auto_load = true',
            "",
        ]
        return "\n".join(lines) + "\n"


class OpenCodeAdapter(RuntimeAdapter):
    """OpenCode adapter — generates .opencode/ configuration."""

    @property
    def runtime_name(self) -> str:
        return "opencode"

    @property
    def config_dir_name(self) -> str:
        return ".opencode"

    def generate_config(
        self,
        spec: ProjectSpec,
        state: ProjectState,
        resources_lock: ResourcesLock,
        workspace_resources: dict[str, list[Path]],
    ) -> dict[Path, str]:
        files = {}

        # .opencode/config.json — main configuration
        files[Path("config.json")] = json.dumps(_to_serializable({
            "name": spec.name,
            "projectType": spec.project_type,
            "stackBundle": spec.stack_bundle,
            "teamPack": spec.team_pack,
            "specialists": spec.specialists,
            "capabilities": spec.capabilities,
            "version": "1.0.0",
        }), indent=2, ensure_ascii=False)

        # .opencode/agents/ — agent definitions
        agents = workspace_resources.get("agents", [])
        for agent_file in agents:
            rel = agent_file.relative_to(self.workspace_dir / "agents")
            content = agent_file.read_text(encoding="utf-8")
            files[Path("agents") / rel] = content

        # .opencode/skills/ — skill definitions
        skills = workspace_resources.get("skills", [])
        for skill_file in skills:
            rel = skill_file.relative_to(self.workspace_dir / "skills")
            content = skill_file.read_text(encoding="utf-8")
            files[Path("skills") / rel] = content

        # .opencode/commands/ — custom commands (from workflows/scripts)
        workflows = workspace_resources.get("workflows", [])
        for wf_file in workflows:
            rel = wf_file.relative_to(self.workspace_dir / "workflows")
            content = wf_file.read_text(encoding="utf-8")
            # Convert workflow to OpenCode command format
            cmd_content = self._workflow_to_command(wf_file.stem, content)
            files[Path("commands") / f"{wf_file.stem}.md"] = cmd_content

        scripts = workspace_resources.get("scripts", [])
        for script_file in scripts:
            rel = script_file.relative_to(self.workspace_dir / "scripts")
            content = script_file.read_text(encoding="utf-8")
            cmd_content = self._script_to_command(script_file.stem, content)
            files[Path("commands") / f"{script_file.stem}.md"] = cmd_content

        # .opencode/rules/ — rule files
        rules = workspace_resources.get("rules", [])
        for rule_file in rules:
            rel = rule_file.relative_to(self.workspace_dir / "rules")
            content = rule_file.read_text(encoding="utf-8")
            files[Path("rules") / rel] = content

        # .opencode/shared/ — shared modules
        shared = workspace_resources.get("shared", [])
        for shared_file in shared:
            rel = shared_file.relative_to(self.workspace_dir / "shared")
            if shared_file.suffix in {".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".sh"}:
                content = shared_file.read_text(encoding="utf-8")
                files[Path("shared") / rel] = content

        return files

    def _workflow_to_command(self, name: str, content: str) -> str:
        return f"""---
name: {name}
description: Workflow converted from .ai-workspace/workflows/{name}.md
---

{content}
"""

    def _script_to_command(self, name: str, content: str) -> str:
        return f"""---
name: {name}
description: Script converted from .ai-workspace/scripts/{name}.py
---

```python
{content}
```
"""


class ClaudeCodeAdapter(RuntimeAdapter):
    """Claude Code adapter — generates .claude/ configuration."""

    @property
    def runtime_name(self) -> str:
        return "claude"

    @property
    def config_dir_name(self) -> str:
        return ".claude"

    def generate_config(
        self,
        spec: ProjectSpec,
        state: ProjectState,
        resources_lock: ResourcesLock,
        workspace_resources: dict[str, list[Path]],
    ) -> dict[Path, str]:
        files = {}

        # .claude/settings.json
        files[Path("settings.json")] = json.dumps(_to_serializable({
            "projectName": spec.name,
            "projectType": spec.project_type,
            "stackBundle": spec.stack_bundle,
            "teamPack": spec.team_pack,
            "specialists": spec.specialists,
            "capabilities": spec.capabilities,
        }), indent=2, ensure_ascii=False)

        # .claude/agents/ — agent definitions
        agents = workspace_resources.get("agents", [])
        for agent_file in agents:
            rel = agent_file.relative_to(self.workspace_dir / "agents")
            content = agent_file.read_text(encoding="utf-8")
            files[Path("agents") / rel] = content

        # .claude/commands/ — slash commands from workflows/scripts
        workflows = workspace_resources.get("workflows", [])
        for wf_file in workflows:
            rel = wf_file.relative_to(self.workspace_dir / "workflows")
            content = wf_file.read_text(encoding="utf-8")
            files[Path("commands") / f"{wf_file.stem}.md"] = content

        scripts = workspace_resources.get("scripts", [])
        for script_file in scripts:
            rel = script_file.relative_to(self.workspace_dir / "scripts")
            content = script_file.read_text(encoding="utf-8")
            files[Path("commands") / f"{script_file.stem}.md"] = f"```bash\n{content}\n```"

        # .claude/rules/ — rule files (converted to CLAUDE.md format)
        rules = workspace_resources.get("rules", [])
        for rule_file in rules:
            rel = rule_file.relative_to(self.workspace_dir / "rules")
            content = rule_file.read_text(encoding="utf-8")
            files[Path("rules") / rel] = content

        return files


class CursorAdapter(RuntimeAdapter):
    """Cursor adapter — generates .cursor/rules/ configuration."""

    @property
    def runtime_name(self) -> str:
        return "cursor"

    @property
    def config_dir_name(self) -> str:
        return ".cursor"

    def generate_config(
        self,
        spec: ProjectSpec,
        state: ProjectState,
        resources_lock: ResourcesLock,
        workspace_resources: dict[str, list[Path]],
    ) -> dict[Path, str]:
        files = {}

        # .cursor/rules/ — rules from workspace rules + agents
        rules = workspace_resources.get("rules", [])
        for rule_file in rules:
            rel = rule_file.relative_to(self.workspace_dir / "rules")
            content = rule_file.read_text(encoding="utf-8")
            # Convert to .mdc format
            mdc_content = self._to_mdc(rule_file.stem, content)
            files[Path("rules") / f"{rule_file.stem}.mdc"] = mdc_content

        agents = workspace_resources.get("agents", [])
        for agent_file in agents:
            rel = agent_file.relative_to(self.workspace_dir / "agents")
            content = agent_file.read_text(encoding="utf-8")
            mdc_content = self._agent_to_mdc(agent_file.stem, content)
            files[Path("rules") / f"agent-{agent_file.stem}.mdc"] = mdc_content

        # .cursor/mcp.json — MCP server config (placeholder)
        files[Path("mcp.json")] = json.dumps({
            "mcpServers": {}
        }, indent=2)

        return files

    def _to_mdc(self, name: str, content: str) -> str:
        return f"""---
description: Rule converted from .ai-workspace/rules/{name}.md
globs: []
alwaysApply: false
---

{content}
"""

    def _agent_to_mdc(self, name: str, content: str) -> str:
        return f"""---
description: Agent {name} from .ai-workspace/agents/
globs: []
alwaysApply: false
---

{content}
"""


# Adapter registry
ADAPTERS = {
    "codex": CodexAdapter,
    "opencode": OpenCodeAdapter,
    "claude": ClaudeCodeAdapter,
    "cursor": CursorAdapter,
}


def get_adapter(runtime: str, project_root: Path | str) -> RuntimeAdapter:
    """Get adapter instance for runtime."""
    if runtime not in ADAPTERS:
        raise ValueError(f"Unknown runtime: {runtime}. Available: {list(ADAPTERS.keys())}")
    return ADAPTERS[runtime](project_root)


def list_adapters() -> list[str]:
    return list(ADAPTERS.keys())


def apply_all_adapters(project_root: Path | str, force: bool = False) -> dict[str, list[Path]]:
    """Apply all registered adapters. Returns {runtime: [written_paths]}."""
    results = {}
    for name, adapter_cls in ADAPTERS.items():
        adapter = adapter_cls(project_root)
        try:
            written = adapter.apply(force=force)
            results[name] = written
        except Exception as e:
            results[name] = []
            print(f"Warning: {name} adapter failed: {e}")
    return results
"""
Domain model for RuntimeAdapter entity.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from core.domain.contracts.id_policy import CanonicalId, make_id
from core.domain.contracts.errors import ValidationResult


@dataclass(frozen=True)
class DetectionConfig:
    """Heuristics for detecting a runtime."""
    executables: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)
    environment_variables: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> 'DetectionConfig':
        return cls(
            executables=data.get("executables", []),
            config_files=data.get("config_files", []),
            environment_variables=data.get("environment_variables", [])
        )

    def to_dict(self) -> dict:
        result = {}
        if self.executables:
            result["executables"] = self.executables
        if self.config_files:
            result["config_files"] = self.config_files
        if self.environment_variables:
            result["environment_variables"] = self.environment_variables
        return result


@dataclass(frozen=True)
class PermissionPolicy:
    """Security/permission policy for a runtime adapter."""
    modifies_global_config: bool = False
    requires_explicit_consent: bool = True
    dangerous_flags_never_enabled: List[str] = field(default_factory=lambda: [
        "--dangerously-skip-permissions",
        "--dangerously-bypass-approvals-and-sandbox",
        "--yolo"
    ])

    @classmethod
    def from_dict(cls, data: dict) -> 'PermissionPolicy':
        return cls(
            modifies_global_config=data.get("modifies_global_config", False),
            requires_explicit_consent=data.get("requires_explicit_consent", True),
            dangerous_flags_never_enabled=data.get("dangerous_flags_never_enabled", [
                "--dangerously-skip-permissions",
                "--dangerously-bypass-approvals-and-sandbox",
                "--yolo"
            ])
        )

    def to_dict(self) -> dict:
        return {
            "modifies_global_config": self.modifies_global_config,
            "requires_explicit_consent": self.requires_explicit_consent,
            "dangerous_flags_never_enabled": self.dangerous_flags_never_enabled
        }


@dataclass(frozen=True)
class RuntimeAdapter:
    """
    Canonical RuntimeAdapter entity.

    Metadata contract for AI coding runtimes — runtime detection != permission to modify global configuration.
    """
    id: CanonicalId
    name: str
    schema_version: str = "1.0.0"
    description: str = ""
    instruction_format: str = "agents-md"
    agent_format: str = "markdown-frontmatter"
    skill_format: str = "markdown"
    project_paths: List[str] = field(default_factory=list)
    global_paths: List[str] = field(default_factory=list)
    supports_mcp: bool = False
    supports_hooks: bool = False
    supports_subagents: bool = False
    supports_commands: bool = False
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    limitations: List[str] = field(default_factory=list)
    permission_policy: PermissionPolicy = field(default_factory=PermissionPolicy)

    VALID_INSTRUCTION_FORMATS = frozenset([
        "agents-md", "claude-md", "codex-md", "gemini-md", "cursor-md", "custom"
    ])

    VALID_AGENT_FORMATS = frozenset(["markdown-frontmatter", "yaml", "json", "custom"])
    VALID_SKILL_FORMATS = frozenset(["markdown", "yaml", "json", "custom"])

    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise ValueError("RuntimeAdapter name cannot be empty")
        if self.schema_version != "1.0.0":
            raise ValueError(f"Unsupported schema_version: {self.schema_version}")
        if self.instruction_format not in self.VALID_INSTRUCTION_FORMATS:
            raise ValueError(f"Invalid instruction_format: {self.instruction_format}")
        if self.agent_format not in self.VALID_AGENT_FORMATS:
            raise ValueError(f"Invalid agent_format: {self.agent_format}")
        if self.skill_format not in self.VALID_SKILL_FORMATS:
            raise ValueError(f"Invalid skill_format: {self.skill_format}")

        if not isinstance(self.detection, DetectionConfig):
            raise TypeError("detection must be DetectionConfig")
        if not isinstance(self.permission_policy, PermissionPolicy):
            raise TypeError("permission_policy must be PermissionPolicy")

        for lim in self.limitations:
            if not isinstance(lim, str) or not lim:
                raise ValueError("limitations must be non-empty strings")

    @classmethod
    def from_dict(cls, data: dict) -> 'RuntimeAdapter':
        return cls(
            id=make_id(data["id"]),
            name=data["name"],
            schema_version=data.get("schema_version", "1.0.0"),
            description=data.get("description", ""),
            instruction_format=data.get("instruction_format", "agents-md"),
            agent_format=data.get("agent_format", "markdown-frontmatter"),
            skill_format=data.get("skill_format", "markdown"),
            project_paths=data.get("project_paths", []),
            global_paths=data.get("global_paths", []),
            supports_mcp=data.get("supports_mcp", False),
            supports_hooks=data.get("supports_hooks", False),
            supports_subagents=data.get("supports_subagents", False),
            supports_commands=data.get("supports_commands", False),
            detection=DetectionConfig.from_dict(data.get("detection", {})),
            limitations=data.get("limitations", []),
            permission_policy=PermissionPolicy.from_dict(data.get("permission_policy", {}))
        )

    def to_dict(self) -> dict:
        result = {
            "schema_version": self.schema_version,
            "id": str(self.id),
            "name": self.name,
            "instruction_format": self.instruction_format,
            "agent_format": self.agent_format,
            "skill_format": self.skill_format,
            "project_paths": self.project_paths,
            "global_paths": self.global_paths,
            "supports_mcp": self.supports_mcp,
            "supports_hooks": self.supports_hooks,
            "supports_subagents": self.supports_subagents,
            "supports_commands": self.supports_commands,
            "detection": self.detection.to_dict(),
            "limitations": self.limitations,
            "permission_policy": self.permission_policy.to_dict()
        }
        if self.description:
            result["description"] = self.description
        return result

    def validate(self) -> ValidationResult:
        """Basic self-validation."""
        result = ValidationResult.success()

        # Ensure permission policy is safe
        if self.permission_policy.modifies_global_config:
            result = result.add_warning(
                f"RuntimeAdapter '{self.id}' modifies global config — requires explicit user consent"
            )

        # Check dangerous flags are listed
        required_flags = [
            "--dangerously-skip-permissions",
            "--dangerously-bypass-approvals-and-sandbox",
            "--yolo"
        ]
        for flag in required_flags:
            if flag not in self.permission_policy.dangerous_flags_never_enabled:
                result = result.add_warning(
                    f"RuntimeAdapter '{self.id}' missing dangerous flag in policy: {flag}"
                )

        return result

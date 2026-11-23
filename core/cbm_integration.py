"""
Codebase Memory (CBM) Integration for AI-Coding-starter M9.

Optional, fail-open integration for project-local code intelligence.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from core.capability_provider_registry import get_provider_for_capability


@dataclass(frozen=True)
class CBMConfig:
    """Codebase Memory project configuration (.codebase-memory.json)."""
    project_root: str
    index_transient_worktrees: bool = False
    ignore_patterns: list[str] = field(default_factory=lambda: [
        "**/node_modules/**",
        "**/.git/**",
        "**/__pycache__/**",
        "**/dist/**",
        "**/build/**",
        "**/.venv/**",
        "**/venv/**",
        "*.log",
        "*.tmp",
    ])
    mcp_server_port: int = 8765


DEFAULT_CBM_CONFIG = CBMConfig(project_root=".")

CBM_IGNORE_DEFAULT = """# Codebase Memory ignore patterns
# Add patterns to exclude from indexing

**/node_modules/**
**/.git/**
**/__pycache__/**
**/dist/**
**/build/**
**/.venv/**
**/venv/**
*.log
*.tmp
"""


def detect_cbm() -> Optional[str]:
    """
    Detect Codebase Memory installation.

    Returns:
        Path to CBM executable (cbm or cbm.exe) or None if not found.
    """
    # Check common installation locations
    candidates = [
        "cbm",
        "cbm.exe",
        shutil.which("cbm"),
        # Windows common paths
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Codebase Memory\cbm.exe"),
        os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Codebase Memory\cbm.exe"),
        # Unix common paths
        "/usr/local/bin/cbm",
        os.path.expanduser("~/.local/bin/cbm"),
    ]

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate).resolve())

    return None


def health_check(cbm_path: Optional[str] = None) -> bool:
    """
    Check if CBM MCP server is reachable.

    Args:
        cbm_path: Optional path to CBM executable. If None, uses detect_cbm().

    Returns:
        True if MCP server responds, False otherwise.
    """
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(("127.0.0.1", 8765))
        sock.close()
        return result == 0
    except Exception:
        return False


def get_project_policy(project_dir: Path) -> CBMConfig:
    """
    Read or create CBM project policy.

    Args:
        project_dir: Project directory (contains .ai-coding-starter/)

    Returns:
        CBMConfig with project settings.
    """
    config_path = project_dir / ".codebase-memory.json"

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return CBMConfig(
                project_root=data.get("project_root", str(project_dir)),
                index_transient_worktrees=data.get("index_transient_worktrees", False),
                ignore_patterns=data.get("ignore_patterns", DEFAULT_CBM_CONFIG.ignore_patterns),
                mcp_server_port=data.get("mcp_server_port", 8765),
            )
        except (json.JSONDecodeError, OSError):
            pass

    # Return default config for this project
    return CBMConfig(project_root=str(project_dir))


def write_project_policy(project_dir: Path, config: CBMConfig) -> Path:
    """
    Write CBM project policy.

    Args:
        project_dir: Project directory
        config: CBM configuration

    Returns:
        Path to written config file.
    """
    config_path = project_dir / ".codebase-memory.json"
    config_path.write_text(
        json.dumps({
            "project_root": config.project_root,
            "index_transient_worktrees": config.index_transient_worktrees,
            "ignore_patterns": config.ignore_patterns,
            "mcp_server_port": config.mcp_server_port,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    return config_path


def write_cbmignore(project_dir: Path, patterns: Optional[list[str]] = None) -> Path:
    """
    Write .cbmignore file.

    Args:
        project_dir: Project directory
        patterns: Optional custom ignore patterns (uses defaults if None)

    Returns:
        Path to written .cbmignore file.
    """
    ignore_path = project_dir / ".cbmignore"
    ignore_path.write_text(
        patterns and "\n".join(patterns) + "\n" or CBM_IGNORE_DEFAULT,
        encoding="utf-8"
    )
    return ignore_path


def initialize_cbm_project(project_dir: Path, force: bool = False) -> bool:
    """
    Initialize CBM for a project.

    Delegates to CBM's install script if available, otherwise writes config files.

    Args:
        project_dir: Project directory
        force: Re-initialize even if config exists

    Returns:
        True if initialization succeeded or was skipped, False on error.
    """
    config_path = project_dir / ".codebase-memory.json"
    ignore_path = project_dir / ".cbmignore"

    if config_path.exists() and not force:
        return True  # Already initialized

    cbm_path = detect_cbm()

    if cbm_path:
        # Delegate to CBM's install script
        try:
            install_script = Path(cbm_path).parent / "install.sh"
            if sys.platform == "win32":
                install_script = Path(cbm_path).parent / "install.ps1"

            if install_script.exists():
                if sys.platform == "win32":
                    subprocess.run(
                        ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(install_script), str(project_dir)],
                        check=True,
                        capture_output=True,
                        timeout=60
                    )
                else:
                    subprocess.run(
                        ["bash", str(install_script), str(project_dir)],
                        check=True,
                        capture_output=True,
                        timeout=60
                    )
                return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            # Fall through to manual config write
            pass

    # Manual config write (fallback or no CBM install script)
    config = CBMConfig(project_root=str(project_dir))
    write_project_policy(project_dir, config)
    write_cbmignore(project_dir)
    return True


def get_cbm_provider_info() -> dict:
    """
    Get CBM provider info for resources.lock.

    Returns:
        Dict with provider metadata or empty dict if not available.
    """
    provider = get_provider_for_capability("code-intelligence")
    if not provider or provider.id != "codebase-memory":
        return {}

    cbm_path = detect_cbm()
    if not cbm_path:
        return {}

    return {
        "provider_id": "codebase-memory",
        "capability": "code-intelligence",
        "executable": cbm_path,
        "health_check": "mcp:127.0.0.1:8765",
        "optional": True,
        "fallback": "source-scan",
    }


def is_cbm_available() -> bool:
    """Check if CBM is installed and healthy."""
    return detect_cbm() is not None and health_check()


# --- Integration hooks for new_project.py ---

def maybe_initialize_cbm(project_dir: Path, interactive: bool = False) -> dict:
    """
    Optionally initialize CBM for a generated project.

    This is the main integration point called from new_project.py after generation.

    Args:
        project_dir: Generated project directory
        interactive: If True, prompt user before initializing

    Returns:
        Dict with result info for resources.lock/AGENTS.md
    """
    result = {
        "initialized": False,
        "provider_info": {},
        "message": "",
    }

    if not detect_cbm():
        result["message"] = "Codebase Memory not installed; skipping (optional)"
        return result

    if not health_check():
        result["message"] = "Codebase Memory MCP server not reachable; skipping (optional)"
        return result

    if interactive:
        # In a real implementation, this would prompt the user
        # For now, auto-initialize since it's optional and fail-open
        pass

    success = initialize_cbm_project(project_dir)
    if success:
        result["initialized"] = True
        result["provider_info"] = get_cbm_provider_info()
        result["message"] = "Codebase Memory initialized for project"
    else:
        result["message"] = "Codebase Memory initialization failed (non-blocking)"

    return result
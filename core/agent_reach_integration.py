"""
Agent-Reach Integration for AI-Coding-starter M10.

Optional, fail-open integration for web research capability.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Optional

from core.capability_provider_registry import get_provider_for_capability


def detect_agent_reach() -> Optional[str]:
    """
    Detect Agent-Reach installation.

    Returns:
        Path to Agent-Reach executable (agent-reach or agent-reach.exe) or None if not found.
    """
    # Check common installation locations
    candidates = [
        "agent-reach",
        "agent-reach.exe",
        shutil.which("agent-reach"),
        # Windows common paths
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Agent-Reach\agent-reach.exe"),
        os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Agent-Reach\agent-reach.exe"),
        # Unix common paths
        "/usr/local/bin/agent-reach",
        os.path.expanduser("~/.local/bin/agent-reach"),
    ]

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate).resolve())

    return None


def health_check(agent_reach_path: Optional[str] = None) -> bool:
    """
    Check if Agent-Reach executable is available.

    Args:
        agent_reach_path: Optional path to Agent-Reach executable. If None, uses detect_agent_reach().

    Returns:
        True if executable is found, False otherwise.
    """
    if agent_reach_path:
        return Path(agent_reach_path).exists()

    return detect_agent_reach() is not None


def get_agent_reach_provider_info() -> dict:
    """
    Get Agent-Reach provider info for resources.lock.

    Returns:
        Dict with provider metadata or empty dict if not available.
    """
    provider = get_provider_for_capability("research-web")
    if not provider or provider.id != "agent-reach":
        return {}

    agent_reach_path = detect_agent_reach()
    if not agent_reach_path:
        return {}

    return {
        "provider_id": "agent-reach",
        "capability": "research-web",
        "executable": agent_reach_path,
        "health_check": "exec:agent-reach",
        "optional": True,
        "fallback": "runtime-native",
    }


def is_agent_reach_available() -> bool:
    """Check if Agent-Reach is installed and healthy."""
    return detect_agent_reach() is not None and health_check()


# --- Integration hooks for new_project.py ---

def maybe_initialize_agent_reach(project_dir: Path, interactive: bool = False) -> dict:
    """
    Optionally initialize Agent-Reach for a generated project.

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

    if not detect_agent_reach():
        result["message"] = "Agent-Reach not installed; skipping (optional)"
        return result

    if not health_check():
        result["message"] = "Agent-Reach executable not found; skipping (optional)"
        return result

    if interactive:
        # In a real implementation, this would prompt the user
        # For now, auto-initialize since it's optional and fail-open
        pass

    result["initialized"] = True
    result["provider_info"] = get_agent_reach_provider_info()
    result["message"] = "Agent-Reach available for project"

    return result
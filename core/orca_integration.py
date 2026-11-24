"""
Orca Integration for AI-Coding-starter M11.

Optional, fail-open integration for orchestration/worktree capability.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from core.capability_provider_registry import get_provider_for_capability


def detect_orca() -> Optional[str]:
    """
    Detect Orca installation.

    Returns:
        Path to Orca executable (orca or orca.exe) or None if not found.
    """
    # Check common installation locations
    candidates = [
        "orca",
        "orca.exe",
        shutil.which("orca"),
        # Windows common paths
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Orca\orca.exe"),
        os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Orca\orca.exe"),
        # Unix common paths
        "/usr/local/bin/orca",
        os.path.expanduser("~/.local/bin/orca"),
    ]

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate).resolve())

    return None


def health_check(orca_path: Optional[str] = None) -> bool:
    """
    Check if Orca is available and responsive.

    Runs `orca --version` with a 10s timeout and expects "orca version"
    in the output.

    Args:
        orca_path: Optional path to Orca executable. If None, uses detect_orca().

    Returns:
        True if Orca responds with version output, False otherwise.
    """
    executable = orca_path or (detect_orca() or "orca")
    try:
        result = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = (result.stdout or "") + (result.stderr or "")
        return "orca version" in output.lower()
    except (subprocess.TimeoutExpired, OSError, subprocess.SubprocessError):
        return False


def get_orca_provider_info() -> dict:
    """
    Get Orca provider info for resources.lock.

    Returns:
        Dict with provider metadata or empty dict if not available.
    """
    provider = get_provider_for_capability("orchestration")
    if not provider or provider.id != "orca":
        return {}

    orca_path = detect_orca()
    if not orca_path:
        return {}

    return {
        "provider_id": "orca",
        "capability": "orchestration",
        "executable": orca_path,
        "health_check": "exec:orca --version",
        "optional": True,
        "fallback": "git-worktree",
    }


def is_orca_available() -> bool:
    """Check if Orca is installed and healthy."""
    return detect_orca() is not None and health_check()


# --- Integration hooks for new_project.py ---

def maybe_initialize_orca(project_dir: Path, interactive: bool = False) -> dict:
    """
    Optionally initialize Orca for a generated project.

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

    if not detect_orca():
        result["message"] = "Orca not installed; skipping (optional)"
        return result

    if not health_check():
        result["message"] = "Orca not responsive; skipping (optional)"
        return result

    if interactive:
        # In a real implementation, this would prompt the user
        # For now, auto-initialize since it's optional and fail-open
        pass

    result["initialized"] = True
    result["provider_info"] = get_orca_provider_info()
    result["message"] = "Orca available for project"

    return result

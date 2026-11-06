#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared, stdlib-only setup helper for AI-Coding-starter V2 Milestone M12.

Both setup.bat (Windows) and setup.sh (POSIX) delegate configuration
generation to this module so that:

  * config.json is always emitted through json.dump() -- which correctly
    escapes backslashes, double-quotes, spaces, and Unicode -- instead of
    fragile shell echo/heredoc interpolation that breaks on Windows paths
    such as ``C:\\Users\\alice\\Projects`` or WSL paths such as
    ``C:\\Users\\alice\\Projects``.
  * Windows and POSIX produce semantically identical config for equivalent
    input (same project directory -> same DEFAULT_PROJECT_PATH value).
  * No shell interpolation of user-supplied paths occurs anywhere.

Responsibilities:
  * Detect an available Python interpreter (python3 -> python -> py).
  * Prompt for / validate the projects directory (absolute, no traversal,
    creatable).
  * Validate bundled resources (<starter>/resources/agents exists).
  * Write <starter>/config.json with UTF-8 encoding and proper JSON escaping.
  * Print the chosen projects directory and interpreter to stdout for the
    thin shell wrapper to consume when creating the platform launcher.

Exit codes:
  0  success
  1  Python interpreter not found
  2  bundled resources missing
  3  path validation error
  4  config write error

All file I/O uses UTF-8 encoding.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

CONFIG_FILE_NAME = "config.json"
RESOURCES_MARKER_DIR = Path("resources") / "agents"
DEFAULT_PROJECTS_DIR_NAME = "Projects"

# Strings that must never be silently enabled anywhere in the starter.
DANGEROUS_FLAGS = (
    "--dangerously-skip-permissions",
    "--dangerously-bypass-approvals-and-sandbox",
    "--yolo",
)


def _find_python() -> str | None:
    """Return the first available Python interpreter, or None.

    Preference order:
      python3  -> python3 (typical POSIX default)
      python   -> python  (typical Windows default)
      py       -> py      (Windows launcher)
    """
    for candidate in ("python3", "python", "py"):
        if shutil.which(candidate) is not None:
            return candidate
    return None


def _has_bundled_resources(starter_dir: Path) -> bool:
    """True if the bundled resource set is present under starter_dir."""
    return (starter_dir / RESOURCES_MARKER_DIR).is_dir()


def _is_path_traversal(path_str: str) -> bool:
    """True if the path contains a parent-traversal segment."""
    parts = Path(path_str).parts
    return ".." in parts


def _prompt_projects_dir(default_dir: Path, non_interactive: bool,
                         explicit_dir: str | None) -> Path:
    """Resolve the projects directory.

    Priority:
      1. --projects-dir CLI argument (explicit, non-interactive)
      2. User input when interactive
      3. default_dir (<home>/Projects)

    Returns an absolute Path. Raises ValueError on validation failure.
    """
    if explicit_dir is not None:
        # Reject path traversal on the raw string before Path construction
        # (Path() normalizes '..' away).
        if _is_path_traversal(explicit_dir):
            raise ValueError(
                f"projects directory contains parent traversal ('..'): "
                f"{explicit_dir}"
            )
        candidate = Path(explicit_dir)
    elif non_interactive:
        candidate = default_dir
    else:
        prompt = (
            f"Enter projects folder [Default: {default_dir}]: "
        )
        user_input = input(prompt).strip()
        if not user_input:
            candidate = default_dir
        else:
            candidate = Path(user_input)

    # Reject path traversal on user input too.
    if not explicit_dir and not non_interactive:
        if _is_path_traversal(user_input):
            raise ValueError(
                f"projects directory contains parent traversal ('..'): "
                f"{user_input}"
            )

    # Expand user (~ / ~user) then make absolute.
    candidate = Path(os.path.expanduser(str(candidate))).resolve()

    return candidate


def _ensure_creatable(path: Path) -> None:
    """Ensure path exists as a directory, creating it if needed.

    Raises ValueError if it cannot be created or is not a directory.
    """
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ValueError(
            f"cannot create projects directory {path}: {exc}"
        ) from exc
    if not path.is_dir():
        raise ValueError(f"projects directory is not a directory: {path}")


def _build_config(projects_dir: Path) -> dict:
    """Build the config.json document dict."""
    return {
        "MASTER_TEMPLATE_PATH": None,
        "DEFAULT_PROJECT_PATH": str(projects_dir),
        "bundled_resources_enabled": True,
        "external_template_optional": True,
    }


def _write_config(starter_dir: Path, config: dict) -> None:
    """Write config.json using json.dump (proper JSON escaping)."""
    config_path = starter_dir / CONFIG_FILE_NAME
    try:
        with open(config_path, "w", encoding="utf-8") as handle:
            json.dump(config, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    except OSError as exc:
        raise ValueError(
            f"cannot write config file {config_path}: {exc}"
        ) from exc


def _read_config(starter_dir: Path) -> dict:
    """Read config.json back for validation round-trip."""
    config_path = starter_dir / CONFIG_FILE_NAME
    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError) as exc:
        raise ValueError(
            f"cannot read back config file {config_path}: {exc}"
        ) from exc


def run(starter_dir: Path,
        projects_dir_arg: str | None,
        non_interactive: bool) -> int:
    """Run the setup helper. Returns an exit code."""
    starter_dir = starter_dir.resolve()

    # 1. Python interpreter detection.
    python = _find_python()
    if python is None:
        print("[ERROR] Python is not installed!")
        print("      Please install Python from: https://python.org")
        return 1
    print(f"[OK] Python found: {python}")

    # 2. Bundled resources check.
    if not _has_bundled_resources(starter_dir):
        print("[ERROR] Bundled resources missing! resources/agents not found.")
        print("      Please ensure the resources/ directory is present in this "
              "repository.")
        return 2
    print("[OK] Bundled resources available: resources/")

    # 3. Resolve projects directory.
    default_dir = Path.home() / DEFAULT_PROJECTS_DIR_NAME
    try:
        projects_dir = _prompt_projects_dir(
            default_dir, non_interactive, projects_dir_arg
        )
    except ValueError as exc:
        print(f"[ERROR] {exc}")
        return 3

    _ensure_creatable(projects_dir)
    print(f"[OK] Projects directory: {projects_dir}")

    # 4. Write config.json via json.dump (proper escaping).
    config = _build_config(projects_dir)
    try:
        _write_config(starter_dir, config)
    except ValueError as exc:
        print(f"[ERROR] {exc}")
        return 4

    # 5. Validate round-trip.
    try:
        written = _read_config(starter_dir)
    except ValueError as exc:
        print(f"[ERROR] {exc}")
        return 4

    # Confirm semantic equivalence: the stored path must equal the intended
    # absolute path after JSON round-trip.
    stored = written.get("DEFAULT_PROJECT_PATH")
    if stored != str(projects_dir):
        print(f"[ERROR] config.json round-trip mismatch: "
              f"stored {stored!r} != expected {projects_dir!r}")
        return 4

    print(f"[OK] Configuration written to: config.json")
    print(f"[OK] DEFAULT_PROJECT_PATH = {projects_dir}")
    print(f"[OK] Python interpreter   = {python}")

    # Emit the resolved values for the shell wrapper to consume.
    print(f"SETUP_PROJECTS_DIR={projects_dir}")
    print(f"SETUP_PYTHON={python}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AI-Coding-starter portable setup helper (M12)."
    )
    parser.add_argument(
        "--starter-dir",
        help="Starter repository root (default: script's parent directory).",
    )
    parser.add_argument(
        "--projects-dir",
        help="Projects directory (non-interactive when provided).",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Do not prompt; use --projects-dir or default.",
    )
    args = parser.parse_args()

    # Reconfigure stdout/stderr to handle Unicode paths on Windows console
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    except (AttributeError, OSError):
        pass

    starter_dir = Path(args.starter_dir) if args.starter_dir else (
        Path(__file__).resolve().parent.parent
    )

    return run(
        starter_dir=starter_dir,
        projects_dir_arg=args.projects_dir,
        non_interactive=args.non_interactive or bool(args.projects_dir),
    )


if __name__ == "__main__":
    sys.exit(main())

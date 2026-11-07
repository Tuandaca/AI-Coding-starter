"""
Centralized CLI UI module for AI-Coding-starter V2.1.1.

Provides semantic, accessible terminal styling with no mandatory third-party
dependency. All styling degrades gracefully:

  * ``NO_COLOR`` environment variable disables color.
  * Non-TTY output disables color.
  * Windows terminals are supported via ANSI escape codes (modern Windows
    Terminal / ConEmu / VT mode); legacy ``cmd.exe`` falls back to plain text.
  * A ``--no-color`` option (handled by the caller) forces plain text.

Palette (semantic, not random):

  * Primary headings: bold cyan
  * Project/stack selections: bright cyan / blue
  * Recommended option: bold green
  * Success: green
  * Warning: yellow
  * Error: red
  * User input prompt: magenta/cyan
  * Metadata / paths / IDs: dim
  * Important selected value: bold white

Backgrounds are never changed. No rainbow styling.
"""

from __future__ import annotations

import os
import sys
from typing import Optional


# ---------------------------------------------------------------------------
# Color state
# ---------------------------------------------------------------------------

_COLOR_ENABLED: bool = True


def supports_color() -> bool:
    """Whether the current terminal supports ANSI color output."""
    if not _COLOR_ENABLED:
        return False
    if os.environ.get("NO_COLOR"):
        return False
    if not sys.stdout.isatty():
        return False
    # Windows: modern terminals support ANSI; legacy console may not.
    if sys.platform == "win32":
        # Allow color; the escape codes themselves are harmless on modern
        # Windows Terminal. Older conhost may ignore them (graceful).
        return True
    return True


def set_color_enabled(enabled: bool) -> None:
    """Enable or disable color output globally."""
    global _COLOR_ENABLED
    _COLOR_ENABLED = bool(enabled)


# ---------------------------------------------------------------------------
# ANSI codes
# ---------------------------------------------------------------------------

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"

_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_BLUE = "\033[34m"
_MAGENTA = "\033[35m"
_CYAN = "\033[36m"
_WHITE = "\033[37m"

_BRIGHT_CYAN = "\033[96m"
_BRIGHT_BLUE = "\033[94m"
_BRIGHT_GREEN = "\033[92m"
_BRIGHT_YELLOW = "\033[93m"
_BRIGHT_MAGENTA = "\033[95m"
_BRIGHT_WHITE = "\033[97m"


def _code(*codes: str) -> str:
    if not supports_color():
        return ""
    return "\033[" + ";".join(codes) + "m"


def c(text: str, *codes: str) -> str:
    """Wrap ``text`` in ANSI codes (no-op when color is disabled)."""
    if not supports_color():
        return text
    return _code(*codes) + text + _RESET


# ---------------------------------------------------------------------------
# Semantic styles
# ---------------------------------------------------------------------------

def bold(text: str) -> str:
    return c(text, _BOLD)


def dim(text: str) -> str:
    return c(text, _DIM)


def red(text: str) -> str:
    return c(text, _RED)


def green(text: str) -> str:
    return c(text, _GREEN)


def yellow(text: str) -> str:
    return c(text, _YELLOW)


def blue(text: str) -> str:
    return c(text, _BLUE)


def magenta(text: str) -> str:
    return c(text, _MAGENTA)


def cyan(text: str) -> str:
    return c(text, _CYAN)


def white(text: str) -> str:
    return c(text, _WHITE)


def bright_cyan(text: str) -> str:
    return c(text, _BRIGHT_CYAN)


def bright_blue(text: str) -> str:
    return c(text, _BRIGHT_BLUE)


def bright_green(text: str) -> str:
    return c(text, _BRIGHT_GREEN)


def bright_yellow(text: str) -> str:
    return c(text, _BRIGHT_YELLOW)


def bright_magenta(text: str) -> str:
    return c(text, _BRIGHT_MAGENTA)


def bright_white(text: str) -> str:
    return c(text, _BRIGHT_WHITE)


# ---------------------------------------------------------------------------
# Reusable UI components
# ---------------------------------------------------------------------------

def rule(char: str = "─", width: int = 66, color: str = "cyan") -> str:
    line = char * width
    return c(line, _color_fn(color))


def title(text: str, version: Optional[str] = None, width: int = 66) -> str:
    """Primary heading: bold cyan rule + bold text."""
    lines = [rule("─", width, "cyan")]
    head = text
    if version:
        head = f"{text}  v{version}"
    lines.append(bright_cyan(bold(head)))
    lines.append(rule("─", width, "cyan"))
    return "\n".join(lines)


def section(text: str) -> str:
    """Section heading: bright blue."""
    return f"\n{bright_blue(text)}\n" + dim("─" * min(len(text) + 2, 66)) + "\n"


def success(text: str) -> str:
    return f"  {green('✔')}  {text}"


def warning(text: str) -> str:
    return f"  {yellow('⚠')}  {text}"


def error(text: str) -> str:
    return f"  {red('✖')}  {text}"


def info(text: str) -> str:
    return f"  {blue('ℹ')}  {text}"


def muted(text: str) -> str:
    return dim(text)


def prompt(text: str, default: Optional[str] = None) -> str:
    """User input prompt: magenta/cyan."""
    suffix = f" [{default}]" if default is not None else ""
    return f"  {magenta('?')}  {cyan(text)}{suffix} "


def selected(label: str, value: str) -> str:
    """Important selected value: bold white label + bright green value."""
    return f"  {dim(label)}: {bright_green(value)}"


def recommended(text: str) -> str:
    """Recommended option: bold green."""
    return f"  {bright_green('★')}  {text}"


def option(num: str, name: str, description: str = "", mark: str = "") -> str:
    """Menu option: number (dim) + name (bright cyan/blue) + description (dim)."""
    parts = [f"  [{dim(num)}] {bright_cyan(name)}"]
    if mark:
        parts.append(f" {green(mark)}")
    if description:
        parts.append(f"\n        {dim(description)}")
    return "".join(parts)


def metadata(label: str, value: str) -> str:
    """Metadata / path / ID line: dim label + dim value."""
    return f"  {dim(label)}: {dim(value)}"


def bullet(text: str, char: str = "•") -> str:
    return f"  {dim(char)} {text}"


def _color_fn(name: str) -> str:
    return {
        "cyan": _CYAN,
        "blue": _BLUE,
        "green": _GREEN,
        "yellow": _YELLOW,
        "red": _RED,
        "magenta": _MAGENTA,
        "white": _WHITE,
    }.get(name, _CYAN)


__all__ = [
    "set_color_enabled", "supports_color",
    "c", "bold", "dim", "red", "green", "yellow", "blue", "magenta", "cyan",
    "white", "bright_cyan", "bright_blue", "bright_green", "bright_yellow",
    "bright_magenta", "bright_white",
    "rule", "title", "section", "success", "warning", "error", "info",
    "muted", "prompt", "selected", "recommended", "option", "metadata",
    "bullet",
]
